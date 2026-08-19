"""The model2rtl compiler driver: a quantized MLP in, portable RTL out.

Given either a trained float model or an already-quantized index set, this
emits a self-contained RTL directory:

    <output>/mlp_fabric.v          weight-independent Multiply-Select-Add fabric
    <output>/mlp_params.v          portable parameter ROM (this model's weights)
    <output>/mlp_params_sel.v      build-time backend selector
    <output>/mlp_top.v             fabric + parameter memory
    <output>/compile_report.json   contract, quantization, hashes, provenance
    <output>/param_images/         canonical parameter images + manifest

The fabric never contains a trained value: it is a function of topology, K, the
activation width and the requantisation shift alone. Two models of the same
shape and shift produce a byte-identical fabric, which the compiler checks and
records.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
from dataclasses import asdict
from typing import Dict, Optional

import numpy as np

from . import contract as C
from .fabric import FabricConfig, derive_widths
from .genmodel import GeneralIntegerModel
from .param_image import ParamImage, write_images
from .param_verilog import emit_portable
from .verilog_emit import emit_fabric_verilog


class CompileError(RuntimeError):
    pass


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _sha_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build_images_general(model: GeneralIntegerModel) -> Dict[str, ParamImage]:
    """Canonical parameter images for an arbitrary two-layer topology.

    Same packing rule the frozen Stage-2 builder uses -- row[i] bits
    [j*idx_bits +: idx_bits] = weight_index[i][j], neuron 0 in the least
    significant field -- expressed for any layer width.
    """
    cfg = model.cfg
    w = derive_widths(cfg)
    ib = w["index_bits"]

    def pack(indices: np.ndarray, n_out: int) -> tuple:
        rows = []
        for i in range(indices.shape[0]):
            word = 0
            for j in range(n_out):
                word |= (int(indices[i, j]) & ((1 << ib) - 1)) << (j * ib)
            rows.append(word)
        return tuple(rows)

    def two_c(v: int, bits: int) -> int:
        return int(v) & ((1 << bits) - 1)

    return {
        "weights_l1": ParamImage(
            name="weights_l1", depth=cfg.n_in, width=cfg.n_hidden * ib,
            rows=pack(model.layer1_weight_indices, cfg.n_hidden),
            packing="row[i] bits [j*%d +: %d] = weight_index[i][j]; neuron 0 "
                    "in the least significant field" % (ib, ib),
            orientation="[in_features, out_features]", signed=False),
        "weights_l2": ParamImage(
            name="weights_l2", depth=cfg.n_hidden, width=cfg.n_out * ib,
            rows=pack(model.layer2_weight_indices, cfg.n_out),
            packing="row[i] bits [j*%d +: %d] = weight_index[i][j]; neuron 0 "
                    "in the least significant field" % (ib, ib),
            orientation="[in_features, out_features]", signed=False),
        "bias_l1": ParamImage(
            name="bias_l1", depth=cfg.n_hidden, width=w["layer1_bias_bits"],
            rows=tuple(two_c(v, w["layer1_bias_bits"])
                       for v in model.layer1_bias),
            packing="row[j] = two's-complement bias of hidden neuron j",
            orientation="[out_features]", signed=True),
        "bias_l2": ParamImage(
            name="bias_l2", depth=cfg.n_out, width=w["layer2_bias_bits"],
            rows=tuple(two_c(v, w["layer2_bias_bits"])
                       for v in model.layer2_bias),
            packing="row[j] = two's-complement bias of output neuron j",
            orientation="[out_features]", signed=True),
    }


def emit_portable_general(images: Dict[str, ParamImage], cfg: FabricConfig,
                          module_name: str) -> str:
    """Portable parameter ROM for an arbitrary topology.

    WHY THIS EXISTS.  model2rtl.param_verilog.emit_portable has a latent defect:
    it widens the layer-2 bias to the bus by calling

        bias_bus_word(images, 1, a)

    WITHOUT passing its own cfg, so the helper falls back to the default
    (MNIST) FabricConfig and sign-extends to 22 bits no matter what topology is
    being emitted.  For 784-32-10 the default IS the real config, so the bug is
    invisible and the verified Stage-2 output is correct.  For any other shape
    it produces a value too wide for the bias image and raises.

    param_verilog.py is frozen -- its SHA-256 is recorded in four stage reports
    -- so the fix cannot go there.  The MNIST path therefore still calls the
    frozen, verified emitter and reproduces its output byte for byte; every
    other topology comes through here, where cfg is threaded correctly.
    """
    w = derive_widths(cfg)
    ww, bw = w["weight_word_bits"], w["bias_data_bits"]
    waw, baw = w["weight_addr_bits"], w["bias_addr_bits"]
    wl1, wl2 = images["weights_l1"], images["weights_l2"]
    bl1, bl2 = images["bias_l1"], images["bias_l2"]

    def sign_extend(value: int, from_bits: int, to_bits: int) -> int:
        if value >> (from_bits - 1):
            value |= ((1 << (to_bits - from_bits)) - 1) << from_bits
        return value & ((1 << to_bits) - 1)

    def arms(img, addr_bits, width, extend_from=None):
        digits = (width + 3) // 4
        out = []
        for a, v in enumerate(img.rows):
            val = v if extend_from is None else sign_extend(v, extend_from,
                                                            width)
            out.append("                %d'd%d: %s <= %d'h%0*x;"
                       % (addr_bits, a, "data", width, digits, val))
        return "\n".join(out)

    def block(port, img_a, img_b, addr_bits, width, extend_b_from):
        return ("            if (%s_layer == 1'b0) begin\n"
                "                case (%s_addr)\n%s\n"
                "                    default: %s_data <= {%d{1'b0}};\n"
                "                endcase\n"
                "            end else begin\n"
                "                case (%s_addr)\n%s\n"
                "                    default: %s_data <= {%d{1'b0}};\n"
                "                endcase\n"
                "            end"
                % (port, port,
                   arms(img_a, addr_bits, width).replace("data <=",
                                                         port + "_data <="),
                   port, width, port,
                   arms(img_b, addr_bits, width,
                        extend_b_from).replace("data <=", port + "_data <="),
                   port, width))

    hdr = "\n".join(
        "//   %-11s depth %4d  width %3d  sha256 %s"
        % (i.name, i.depth, i.width, i.sha256()) for i in (wl1, wl2, bl1, bl2))

    return f"""// ===========================================================================
// {module_name}.v -- GENERATED by model2rtl. Do not edit by hand.
//
// Portable parameter memory for a {cfg.n_in} -> {cfg.n_hidden} -> {cfg.n_out} network.
// Pure synthesizable Verilog-2001: no vendor primitive, no memory IP, no
// attribute, no synthesis pragma, no $readmemh and no initial block.
//
// TIMING CONTRACT
//   Synchronous read, one cycle of latency, enable gated with hold. An address
//   driven during cycle T is captured on the posedge ending T and its data is
//   presented throughout T+1. While en is low the previous data is held.
//
// WEIGHT WORD PACKING
//   weight_index[i][j] = wmem_data[j*{w['index_bits']} +: {w['index_bits']}], neuron 0 in the least
//   significant field, orientation [in_features, out_features].
//   Layer 2 uses bits [{cfg.n_out * w['index_bits'] - 1}:0]; the unused high bits are driven to zero.
//
// BIAS
//   Layer-1 biases occupy the whole {bw}-bit bus. Layer-2 biases are {bl2.width}-bit
//   and are SIGN extended to {bw} bits, never zero extended.
//
// INVALID ADDRESSES
//   Any address outside a layer's depth returns zero. No invalid address
//   aliases onto a valid parameter row.
//
// SOURCE IMAGES (canonical, model2rtl-param-image-v1)
{hdr}
// ===========================================================================

`default_nettype none

module {module_name} (
    input  wire          clk,
    input  wire          wmem_en,
    input  wire          wmem_layer,
    input  wire [{waw - 1}:0]{' ' * max(0, 5 - len(str(waw - 1)))}wmem_addr,
    output reg  [{ww - 1}:0]{' ' * max(0, 5 - len(str(ww - 1)))}wmem_data,
    input  wire          bmem_en,
    input  wire          bmem_layer,
    input  wire [{baw - 1}:0]{' ' * max(0, 5 - len(str(baw - 1)))}bmem_addr,
    output reg  [{bw - 1}:0]{' ' * max(0, 5 - len(str(bw - 1)))}bmem_data
);

    always @(posedge clk) begin
        if (wmem_en) begin
{block("wmem", wl1, wl2, waw, ww, None)}
        end
    end

    always @(posedge clk) begin
        if (bmem_en) begin
{block("bmem", bl1, bl2, baw, bw, bl2.width)}
        end
    end

endmodule

`default_nettype wire
"""


def emit_selector_general(cfg: FabricConfig, backend_module: str,
                          module_name: str) -> str:
    """Build-time selector for an arbitrary design name.

    model2rtl.param_verilog.emit_selector hardcodes the MNIST module names and
    is frozen, so the general compiler emits its own. The structure is
    identical: one module that binds the abstract parameter-memory name to one
    concrete backend, chosen by which file you compile.
    """
    w = derive_widths(cfg)
    return f"""// ===========================================================================
// {module_name}.v -- GENERATED by model2rtl. Do not edit by hand.
//
// Build-time backend selector: `{module_name}` -> {backend_module}
// Compile exactly ONE selector file per build.
// ===========================================================================

`default_nettype none

module {module_name} (
    input  wire          clk,
    input  wire          wmem_en,
    input  wire          wmem_layer,
    input  wire [{w['weight_addr_bits'] - 1}:0]{' ' * max(0, 5 - len(str(w['weight_addr_bits'] - 1)))}wmem_addr,
    output wire [{w['weight_word_bits'] - 1}:0]{' ' * max(0, 5 - len(str(w['weight_word_bits'] - 1)))}wmem_data,
    input  wire          bmem_en,
    input  wire          bmem_layer,
    input  wire [{w['bias_addr_bits'] - 1}:0]{' ' * max(0, 5 - len(str(w['bias_addr_bits'] - 1)))}bmem_addr,
    output wire [{w['bias_data_bits'] - 1}:0]{' ' * max(0, 5 - len(str(w['bias_data_bits'] - 1)))}bmem_data
);

    {backend_module} u_backend (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data)
    );

endmodule

`default_nettype wire
"""


def emit_top_general(cfg: FabricConfig, top_name: str, fabric_module: str,
                     params_module: str) -> str:
    """Top level for an arbitrary design name.

    model2rtl.param_verilog.emit_top instantiates the literal module name
    `mnist_mlp_fabric` and is frozen, so a generally-named design needs its own
    top. Same structure, same ports, names taken from the config.
    """
    w = derive_widths(cfg)
    return f"""// ===========================================================================
// {top_name}.v -- GENERATED by model2rtl. Do not edit by hand.
//
// {fabric_module} (weight independent) + one parameter backend.
//
// BACKEND SELECTION IS BUILD TIME. Compile exactly one selector file, which
// defines `{params_module}` and binds it to a concrete backend. There is no
// runtime mux and no parameter.
//
// Topology {cfg.n_in} -> {cfg.n_hidden} -> ReLU -> {cfg.n_out}, K = {cfg.k},
// activation {cfg.act_bits}-bit unsigned, requantisation shift {cfg.requant_shift}.
// ===========================================================================

`default_nettype none

module {top_name} (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    output wire         in_ready,
    input  wire         in_valid,
    input  wire [{cfg.act_bits - 1}:0]   in_data,
    output wire         busy,
    output wire         done,
    output wire         prediction_valid,
    output wire [{w['prediction_bits'] - 1}:0]   prediction,
    output wire [{w['logits_bits'] - 1}:0] logits
);

    wire         wmem_en, wmem_layer;
    wire [{w['weight_addr_bits'] - 1}:0]  wmem_addr;
    wire [{w['weight_word_bits'] - 1}:0] wmem_data;
    wire         bmem_en, bmem_layer;
    wire [{w['bias_addr_bits'] - 1}:0]   bmem_addr;
    wire [{w['bias_data_bits'] - 1}:0]  bmem_data;

    {fabric_module} u_fabric (
        .clk(clk), .rst(rst), .start(start),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data),
        .busy(busy), .done(done), .prediction_valid(prediction_valid),
        .prediction(prediction), .logits(logits)
    );

    {params_module} u_params (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data)
    );

endmodule

`default_nettype wire
"""


def _prove_weight_independence(cfg: FabricConfig, fabric_src: str,
                               seed: int = 4242) -> dict:
    """Regenerate the fabric from a different random model of the same shape.

    The fabric must come out byte-identical. This is the compiler asserting its
    own central property on every run, not a claim inherited from Stage 1.
    """
    rng = np.random.default_rng(seed)
    other = GeneralIntegerModel.from_arrays(
        rng.integers(0, cfg.k, (cfg.n_in, cfg.n_hidden)),
        rng.integers(0, cfg.k, (cfg.n_hidden, cfg.n_out)),
        np.zeros(cfg.n_hidden, dtype=np.int64),
        np.zeros(cfg.n_out, dtype=np.int64),
        k=cfg.k, act_bits=cfg.act_bits, requant_shift=cfg.requant_shift,
        module_name=cfg.module_name)
    again = emit_fabric_verilog(other.cfg)
    return {
        "fabric_sha256": _sha_text(fabric_src),
        "fabric_sha256_with_random_parameters": _sha_text(again),
        "identical": _sha_text(fabric_src) == _sha_text(again),
        "method": "regenerate the fabric from a random model of the same "
                  "topology and compare SHA-256",
    }


def compile_model(model: GeneralIntegerModel, outdir: str,
                  prefix: str = "mlp",
                  extra_report: Optional[dict] = None,
                  write_param_images: bool = True) -> dict:
    """Emit the RTL and the compile report. Returns the report."""
    cfg = model.cfg
    if cfg.k != C.K:
        raise CompileError(
            "this fabric emitter implements K = %d only; K = %d would change "
            "the product-bank width and the selector fan-in, which is a "
            "different architecture." % (C.K, cfg.k))
    os.makedirs(outdir, exist_ok=True)
    w = derive_widths(cfg)

    backend_module = "%s_params_portable" % prefix
    params_module = "%s_params" % prefix
    fabric_src = emit_fabric_verilog(cfg)
    images = build_images_general(model)
    # The frozen emitter is correct for -- and only for -- the MNIST config it
    # was verified against; see emit_portable_general for why.
    mnist_cfg = FabricConfig(module_name=cfg.module_name)
    if (cfg.n_in, cfg.n_hidden, cfg.n_out, cfg.k, cfg.act_bits,
            cfg.requant_shift) == (mnist_cfg.n_in, mnist_cfg.n_hidden,
                                   mnist_cfg.n_out, mnist_cfg.k,
                                   mnist_cfg.act_bits,
                                   mnist_cfg.requant_shift):
        params_src = emit_portable(images, cfg, module_name=backend_module)
        params_emitter = "model2rtl.param_verilog.emit_portable (frozen, "\
                         "Stage-2 verified)"
    else:
        params_src = emit_portable_general(images, cfg, backend_module)
        params_emitter = "model2rtl.compile.emit_portable_general"
    sel_src = emit_selector_general(cfg, backend_module, params_module)
    top_src = emit_top_general(cfg, "%s_top" % prefix, cfg.module_name,
                               params_module)

    files = {
        "%s_fabric.v" % prefix: fabric_src,
        "%s_params.v" % prefix: params_src,
        "%s_params_sel.v" % prefix: sel_src,
        "%s_top.v" % prefix: top_src,
    }
    written = {}
    for name, text in files.items():
        path = os.path.join(outdir, name)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            fh.write(text)
        os.replace(tmp, path)
        written[name] = _sha_file(path)

    if write_param_images:
        write_images(os.path.join(outdir, "param_images"), images)

    report = {
        "tool": "model2rtl",
        "topology": "%d -> %d -> ReLU -> %d" % (cfg.n_in, cfg.n_hidden,
                                                cfg.n_out),
        "config": asdict(cfg),
        "widths": w,
        "model": model.to_dict(),
        "canonical_images": {n: i.to_dict() for n, i in images.items()},
        "emitted": written,
        "parameter_rom_emitter": params_emitter,
        "weight_independence": _prove_weight_independence(cfg, fabric_src),
        "build_command": (
            "compile exactly one selector file:\n"
            "  {p}_top.v {p}_fabric.v {p}_params.v {p}_params_sel.v"
        ).format(p=prefix),
        "latency": {
            "cycles_per_inference": cfg.n_in + 2 * cfg.n_hidden + cfg.n_out + 6,
            "formula": "n_in + 2*n_hidden + n_out + 6",
            "note": "architectural cycle count only; no timing analysis is "
                    "performed and no clock frequency is implied",
        },
        "environment": {"python": platform.python_version(),
                        "numpy": np.__version__},
        "not_claimed": [
            "no synthesis, place-and-route or timing analysis is run by this "
            "command",
            "no ASIC or FPGA implementation is produced",
            "accuracy of the emitted design equals the integer model it was "
            "given, and no more",
        ],
    }
    if extra_report:
        report.update(extra_report)
    if not report["weight_independence"]["identical"]:
        raise CompileError("the emitted fabric depends on the trained "
                           "parameters; this must never happen")

    path = os.path.join(outdir, "compile_report.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return report
