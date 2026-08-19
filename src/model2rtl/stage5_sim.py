"""Stage 5 simulation: three backends compared against one canonical image.

The Stage-2 harness compares two parameter backends.  Stage 5 adds a third --
the physical-organisation wrapper over the banked and sign-padded OpenROM
macros -- and requires all three to agree with each other AND with the
canonical logical image on every cycle of the same stimulus stream.

Nothing in stage2_sim or stage3_sim is modified: their stimulus builder,
expectation model and testbench emitter are imported and reused, so there is
still exactly one definition of "what the fabric should see".
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List

import numpy as np

from .fabric import FabricConfig, derive_widths
from .param_image import ParamImage
from .sim import _run, find_tool, iverilog_compile
from .stage2_sim import Stim, build_stimulus, expected_outputs
from .stage3_sim import (_parse_hidden, _parse_out, _write_images,
                         emit_stage3_tb)

#: Build-time source list for the Stage-5 physical backend.  mnist_mlp_top.v
#: and mnist_mlp_fabric.v are the frozen files, unchanged.
PHYS_SOURCES = ["mnist_mlp_fabric.v", "mnist_mlp_params_openrom_phys.v",
                "mnist_mlp_params_sel_openrom_phys.v", "mnist_mlp_top.v"]

BACKEND_SOURCES = {
    "portable": ["mnist_mlp_fabric.v", "mnist_mlp_params_portable.v",
                 "mnist_mlp_params_sel_portable.v", "mnist_mlp_top.v"],
    "openram": ["mnist_mlp_fabric.v", "mnist_mlp_params_openram.v",
                "mnist_mlp_params_sel_openram.v", "mnist_mlp_top.v"],
    "openrom_phys": PHYS_SOURCES,
}

BACKEND_MODULES = {
    "portable": "mnist_mlp_params_portable",
    "openram": "mnist_mlp_params_openram",
    "openrom_phys": "mnist_mlp_params_openrom_phys",
}

BACKEND_FILES = {
    "portable": "mnist_mlp_params_portable.v",
    "openram": "mnist_mlp_params_openram.v",
    "openrom_phys": "mnist_mlp_params_openrom_phys.v",
}

ORDER = ("portable", "openram", "openrom_phys")


# --------------------------------------------------------------------------
# Three-way parameter-bus equivalence
# --------------------------------------------------------------------------

def emit_three_way_tb(cfg: FabricConfig = FabricConfig()) -> str:
    w = derive_widths(cfg)
    waw, baw = w["weight_addr_bits"], w["bias_addr_bits"]
    stim_bits = 2 + waw + 2 + baw
    inst = "\n".join("""
    wire [WW-1:0] wdata_{k};
    wire [BW-1:0] bdata_{k};
    {mod} u_{k} (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wdata_{k}),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bdata_{k})
    );""".format(k=k, mod=BACKEND_MODULES[k]) for k in ORDER)
    fields = ", ".join("wdata_%s, bdata_%s" % (k, k) for k in ORDER)
    fmt = " ".join(["%h"] * (2 * len(ORDER)))
    return f"""// TEST-ONLY Stage-5 testbench: drives all THREE parameter backends with one
// identical stimulus stream and logs every data bus every cycle.
// Never synthesized.
`timescale 1ns/1ps

module tb;
    parameter NSTIM = 16;

    localparam WAW = {waw};
    localparam BAW = {baw};
    localparam WW  = {w['weight_word_bits']};
    localparam BW  = {w['bias_data_bits']};
    localparam SB  = {stim_bits};

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg [SB-1:0] stim [0:NSTIM-1];

    reg           wmem_en, wmem_layer, bmem_en, bmem_layer;
    reg [WAW-1:0] wmem_addr;
    reg [BAW-1:0] bmem_addr;
{inst}

    integer fh, i;
    reg [SB-1:0] s;

    initial begin
        wmem_en = 1'b0; wmem_layer = 1'b0; wmem_addr = {{WAW{{1'b0}}}};
        bmem_en = 1'b0; bmem_layer = 1'b0; bmem_addr = {{BAW{{1'b0}}}};
        $readmemh("stim.hex", stim);
        fh = $fopen("params3_out.txt", "w");

        @(negedge clk);
        for (i = 0; i < NSTIM; i = i + 1) begin
            @(negedge clk);
            if (i > 0)
                $fdisplay(fh, "%0d {fmt}", i - 1, {fields});
            s = stim[i];
            bmem_addr  = s[BAW-1:0];
            bmem_layer = s[BAW];
            bmem_en    = s[BAW+1];
            wmem_addr  = s[BAW+2+WAW-1:BAW+2];
            wmem_layer = s[BAW+2+WAW];
            wmem_en    = s[BAW+2+WAW+1];
        end
        @(negedge clk);
        $fdisplay(fh, "%0d {fmt}", NSTIM - 1, {fields});
        $fclose(fh);
        $display("TB OK");
        $finish;
    end
endmodule
"""


def _parse_hex(field: str):
    """X means 'never driven yet'.  Legal only before the first enabled read on
    that port, which the caller checks."""
    return None if "x" in field.lower() else int(field, 16)


def run_three_way(root: str, workdir: str, images: Dict[str, ParamImage],
                  cfg: FabricConfig = FabricConfig()) -> dict:
    """Drive all three backends with one stimulus stream and compare
    everything: backend to backend, and every backend to the canonical image."""
    os.makedirs(workdir, exist_ok=True)
    w = derive_widths(cfg)
    stim = build_stimulus(images, cfg)
    packed = [s.packed(w["weight_addr_bits"], w["bias_addr_bits"])
              for s in stim]
    bits = 2 + w["weight_addr_bits"] + 2 + w["bias_addr_bits"]
    with open(os.path.join(workdir, "stim.hex"), "w") as fh:
        fh.write("\n".join("%0*x" % ((bits + 3) // 4, v) for v in packed)
                 + "\n")

    srcs = []
    for k in ORDER:
        p = os.path.join(root, "rtl", BACKEND_FILES[k])
        dst = os.path.join(workdir, BACKEND_FILES[k])
        if os.path.abspath(p) != os.path.abspath(dst):
            shutil.copyfile(p, dst)
        srcs.append(dst)
    tb = os.path.join(workdir, "tb_params3.v")
    with open(tb, "w") as fh:
        fh.write(emit_three_way_tb(cfg))

    exe = os.path.join(workdir, "params3.vvp")
    c = iverilog_compile(srcs + [tb], exe, workdir, std="2001",
                         top_params={"tb.NSTIM": len(stim)})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)
    r = _run([find_tool("vvp"), exe], cwd=workdir, timeout=7200)
    if r.returncode != 0 or "TB OK" not in r.output:
        raise RuntimeError("simulation failed:\n" + r.output[-4000:])

    exp_w, exp_b = expected_outputs(stim, images, cfg)

    rows = []
    with open(os.path.join(workdir, "params3_out.txt")) as fh:
        for line in fh:
            f = line.split()
            rows.append((int(f[0]),
                         [_parse_hex(f[1 + 2 * i]) for i in range(len(ORDER))],
                         [_parse_hex(f[2 + 2 * i]) for i in range(len(ORDER))]))

    per_backend = {k: {"weight_vs_image": 0, "bias_vs_image": 0} for k in ORDER}
    backend_pairs = {}
    for i, a in enumerate(ORDER):
        for b in ORDER[i + 1:]:
            backend_pairs["%s_vs_%s" % (a, b)] = {"weight": 0, "bias": 0}
    undriven_before_first = 0
    seen_w = seen_b = False
    weight_cmp = bias_cmp = 0
    examples: List[dict] = []

    for idx, wvals, bvals in rows:
        ew, eb = exp_w[idx], exp_b[idx]
        if ew is not None:
            seen_w = True
            for k, v in zip(ORDER, wvals):
                weight_cmp += 1
                if v is None:
                    undriven_before_first += 1
                elif v != ew:
                    per_backend[k]["weight_vs_image"] += 1
                    if len(examples) < 8:
                        examples.append({"cycle": idx, "port": "weight",
                                         "backend": k, "expected": hex(ew),
                                         "found": hex(v)})
        elif any(v is None for v in wvals) and seen_w:
            undriven_before_first += 1
        if eb is not None:
            seen_b = True
            for k, v in zip(ORDER, bvals):
                bias_cmp += 1
                if v is None:
                    undriven_before_first += 1
                elif v != eb:
                    per_backend[k]["bias_vs_image"] += 1
                    if len(examples) < 8:
                        examples.append({"cycle": idx, "port": "bias",
                                         "backend": k, "expected": hex(eb),
                                         "found": hex(v)})
        for i, a in enumerate(ORDER):
            for j, b in enumerate(ORDER[i + 1:], start=i + 1):
                key = "%s_vs_%s" % (a, b)
                if wvals[i] != wvals[j]:
                    backend_pairs[key]["weight"] += 1
                if bvals[i] != bvals[j]:
                    backend_pairs[key]["bias"] += 1

    total = (sum(v["weight_vs_image"] + v["bias_vs_image"]
                 for v in per_backend.values())
             + sum(v["weight"] + v["bias"] for v in backend_pairs.values()))
    return {
        "backends": list(ORDER),
        "stimulus_cycles": len(stim),
        "stimulus_coverage": "every valid address of every logical memory, "
                             "plus holds, layer switches, invalid addresses, "
                             "first/last address and a new address every cycle",
        "weight_comparisons": weight_cmp,
        "bias_comparisons": bias_cmp,
        "vs_canonical_image": per_backend,
        "backend_to_backend": backend_pairs,
        "undriven_cycles_before_first_read": undriven_before_first,
        "mismatches": total,
        "examples": examples,
    }


# --------------------------------------------------------------------------
# Full-model inference with an arbitrary backend source list
# --------------------------------------------------------------------------

def run_images_backend(root: str, workdir: str, backend: str, x: np.ndarray,
                       stall_mode: int = 0, stall_n: int = 7,
                       cfg: FabricConfig = FabricConfig()) -> dict:
    """Same testbench Stage 3 used, driven with any of the three backends."""
    os.makedirs(workdir, exist_ok=True)
    x = np.asarray(x, dtype=np.int64)
    if x.ndim == 1:
        x = x[None, :]

    srcs = []
    for n in BACKEND_SOURCES[backend]:
        p = os.path.join(root, "rtl", n)
        dst = os.path.join(workdir, n)
        if os.path.abspath(p) != os.path.abspath(dst):
            shutil.copyfile(p, dst)
        srcs.append(dst)

    tb = os.path.join(workdir, "tb_stage3.v")
    with open(tb, "w") as fh:
        fh.write(emit_stage3_tb(cfg))
    _write_images(workdir, x)

    exe = os.path.join(workdir, "stage5.vvp")
    c = iverilog_compile(srcs + [tb], exe, workdir, std="2001",
                         top_params={"tb.NIMG": x.shape[0],
                                     "tb.STALL_MODE": stall_mode,
                                     "tb.STALL_N": stall_n,
                                     "tb.TRACE_IMAGES": 0})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)
    r = _run([find_tool("vvp"), exe], cwd=workdir, timeout=14400)
    if r.returncode != 0 or "TB OK" not in r.output:
        raise RuntimeError("simulation failed:\n" + r.output[-4000:])

    cycles, preds, logits = _parse_out(os.path.join(workdir, "out.txt"),
                                       cfg.n_out)
    return {
        "backend": backend,
        "cycles": cycles,
        "predictions": preds,
        "logits": logits,
        "hidden": _parse_hidden(os.path.join(workdir, "hidden.txt"),
                                cfg.n_hidden),
    }
