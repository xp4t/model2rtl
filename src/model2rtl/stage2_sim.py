"""Stage-2 simulation: parameter readback/equivalence and top-level inference.

Two generated testbenches:

  * ``tb_params``  instantiates BOTH backends side by side, drives them with
    one identical stimulus stream and logs both data buses every cycle.
  * ``tb_top``     instantiates ``mnist_mlp_top`` (fabric + one backend chosen
    by the source list) and runs real MNIST images end to end.

Everything is checked in Python against the canonical parameter images and the
Stage-0 integer golden model.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

from .fabric import FabricConfig, derive_widths
from .param_image import ParamImage, bias_bus_word, weight_bus_word
from .sim import _run, find_tool, iverilog_compile

RTL = "rtl"

PORTABLE_SOURCES = ["mnist_mlp_fabric.v", "mnist_mlp_params_portable.v",
                    "mnist_mlp_params_sel_portable.v", "mnist_mlp_top.v"]
OPENRAM_SOURCES = ["mnist_mlp_fabric.v", "mnist_mlp_params_openram.v",
                   "mnist_mlp_params_sel_openram.v", "mnist_mlp_top.v"]


# --------------------------------------------------------------------------
# Stimulus
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Stim:
    wen: int
    wlayer: int
    waddr: int
    ben: int
    blayer: int
    baddr: int

    def packed(self, waw: int, baw: int) -> int:
        v = self.wen
        v = (v << 1) | self.wlayer
        v = (v << waw) | self.waddr
        v = (v << 1) | self.ben
        v = (v << 1) | self.blayer
        v = (v << baw) | self.baddr
        return v


def build_stimulus(images: Dict[str, ParamImage],
                   cfg: FabricConfig = FabricConfig()) -> List[Stim]:
    """Full coverage: every valid address, plus the awkward cases."""
    w = derive_widths(cfg)
    wmax = (1 << w["weight_addr_bits"]) - 1
    bmax = (1 << w["bias_addr_bits"]) - 1
    d = {n: images[n].depth for n in images}
    s: List[Stim] = []

    def add(**kw):
        base = dict(wen=0, wlayer=0, waddr=0, ben=0, blayer=0, baddr=0)
        base.update(kw)
        s.append(Stim(**base))

    # 0. prime both ports so neither data bus is still undriven
    add(wen=1, wlayer=0, waddr=0, ben=1, blayer=0, baddr=0)
    # 1. every valid layer-1 weight address, consecutively, one per cycle
    for a in range(d["weights_l1"]):
        add(wen=1, wlayer=0, waddr=a)
    # 2. every valid layer-2 weight address
    for a in range(d["weights_l2"]):
        add(wen=1, wlayer=1, waddr=a)
    # 3. every valid bias address, both layers
    for a in range(d["bias_l1"]):
        add(ben=1, blayer=0, baddr=a)
    for a in range(d["bias_l2"]):
        add(ben=1, blayer=1, baddr=a)
    # 4. both ports busy at once
    for a in range(d["bias_l1"]):
        add(wen=1, wlayer=0, waddr=a, ben=1, blayer=0, baddr=a)
    # 5. enable deasserted -- the data must HOLD
    add(wen=1, wlayer=0, waddr=5, ben=1, blayer=0, baddr=5)
    for _ in range(4):
        add()
    # 6. layer switching on consecutive cycles
    for a in range(8):
        add(wen=1, wlayer=0, waddr=a, ben=1, blayer=0, baddr=a)
        add(wen=1, wlayer=1, waddr=a, ben=1, blayer=1, baddr=a % d["bias_l2"])
    # 7. first and last valid addresses of every space
    for layer, depth in ((0, d["weights_l1"]), (1, d["weights_l2"])):
        add(wen=1, wlayer=layer, waddr=0)
        add(wen=1, wlayer=layer, waddr=depth - 1)
    for layer, depth in ((0, d["bias_l1"]), (1, d["bias_l2"])):
        add(ben=1, blayer=layer, baddr=0)
        add(ben=1, blayer=layer, baddr=depth - 1)
    # 8. invalid addresses: just past the end, and the maximum encodable
    for layer, depth in ((0, d["weights_l1"]), (1, d["weights_l2"])):
        for a in (depth, depth + 1, wmax):
            if a <= wmax:
                add(wen=1, wlayer=layer, waddr=a)
    for layer, depth in ((0, d["bias_l1"]), (1, d["bias_l2"])):
        for a in (depth, depth + 1, bmax):
            if a <= bmax:
                add(ben=1, blayer=layer, baddr=a)
    # 9. an invalid address immediately after a valid one must not alias it
    for layer, depth in ((0, d["weights_l1"]), (1, d["weights_l2"])):
        add(wen=1, wlayer=layer, waddr=0)
        add(wen=1, wlayer=layer, waddr=wmax)
    # 10. address changing every cycle, alternating high/low
    for a in range(16):
        add(wen=1, wlayer=0, waddr=a, ben=1, blayer=0, baddr=a)
        add(wen=1, wlayer=0, waddr=d["weights_l1"] - 1 - a,
            ben=1, blayer=0, baddr=d["bias_l1"] - 1 - a)
    add()  # settle
    return s


def expected_outputs(stim: Sequence[Stim], images: Dict[str, ParamImage],
                     cfg: FabricConfig = FabricConfig()
                     ) -> Tuple[List[int], List[int]]:
    """Golden wmem_data / bmem_data for each stimulus, with hold semantics."""
    wd, bd = [], []
    cur_w, cur_b = None, None
    for st in stim:
        if st.wen:
            cur_w = weight_bus_word(images, st.wlayer, st.waddr, cfg)
        if st.ben:
            cur_b = bias_bus_word(images, st.blayer, st.baddr, cfg)
        wd.append(cur_w)
        bd.append(cur_b)
    return wd, bd


# --------------------------------------------------------------------------
# Testbench emitters
# --------------------------------------------------------------------------

def emit_param_tb(cfg: FabricConfig = FabricConfig()) -> str:
    w = derive_widths(cfg)
    waw, baw = w["weight_addr_bits"], w["bias_addr_bits"]
    stim_bits = 2 + waw + 2 + baw
    return f"""// TEST-ONLY: drives BOTH Stage-2 parameter backends with one identical
// stimulus stream and logs both data buses every cycle. Never synthesized.
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

    reg             wmem_en, wmem_layer, bmem_en, bmem_layer;
    reg [WAW-1:0]   wmem_addr;
    reg [BAW-1:0]   bmem_addr;

    wire [WW-1:0]   wdata_p, wdata_o;
    wire [BW-1:0]   bdata_p, bdata_o;

    mnist_mlp_params_portable u_p (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wdata_p),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bdata_p)
    );

    mnist_mlp_params_openram u_o (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wdata_o),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bdata_o)
    );

    integer fh, i;
    reg [SB-1:0] s;

    initial begin
        wmem_en = 1'b0; wmem_layer = 1'b0; wmem_addr = {{WAW{{1'b0}}}};
        bmem_en = 1'b0; bmem_layer = 1'b0; bmem_addr = {{BAW{{1'b0}}}};
        $readmemh("stim.hex", stim);
        fh = $fopen("params_out.txt", "w");

        @(negedge clk);
        for (i = 0; i < NSTIM; i = i + 1) begin
            @(negedge clk);
            if (i > 0)
                $fdisplay(fh, "%0d %h %h %h %h", i - 1,
                          wdata_p, wdata_o, bdata_p, bdata_o);
            s = stim[i];
            bmem_addr  = s[BAW-1:0];
            bmem_layer = s[BAW];
            bmem_en    = s[BAW+1];
            wmem_addr  = s[BAW+2+WAW-1:BAW+2];
            wmem_layer = s[BAW+2+WAW];
            wmem_en    = s[BAW+2+WAW+1];
        end
        @(negedge clk);
        $fdisplay(fh, "%0d %h %h %h %h", NSTIM - 1,
                  wdata_p, wdata_o, bdata_p, bdata_o);
        $fclose(fh);
        $display("TB OK");
        $finish;
    end
endmodule
"""


def emit_top_tb(cfg: FabricConfig = FabricConfig()) -> str:
    """Top-level inference testbench: no external memory model at all."""
    w = derive_widths(cfg)
    return f"""// TEST-ONLY: runs MNIST images through mnist_mlp_top, which already
// contains the selected parameter backend. Never synthesized.
`timescale 1ns/1ps

module tb;
    parameter NIMG = 4;

    localparam N_IN     = {cfg.n_in};
    localparam N_HID    = {cfg.n_hidden};
    localparam N_OUT    = {cfg.n_out};
    localparam ACT_BITS = {w['act_bits']};
    localparam ACC2     = {w['layer2_acc_bits']};
    localparam PREDW    = {w['prediction_bits']};
    localparam LOGW     = {w['logits_bits']};
    localparam TIMEOUT  = 20000;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg                rst, start, in_valid;
    reg [ACT_BITS-1:0] in_data;
    wire               in_ready, busy, done, prediction_valid;
    wire [PREDW-1:0]   prediction;
    wire [LOGW-1:0]    logits;

    mnist_mlp_top dut (
        .clk(clk), .rst(rst), .start(start),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),
        .busy(busy), .done(done), .prediction_valid(prediction_valid),
        .prediction(prediction), .logits(logits)
    );

    reg [ACT_BITS-1:0] img [0:NIMG*N_IN-1];
    reg [31:0] cyc;
    always @(posedge clk) cyc <= cyc + 32'd1;

    integer fh_out, fh_hid, im, q, errors;

    task run_image;
        input integer index;
        integer base, pix, t0, t1, guard;
        begin
            base = index * N_IN;
            @(negedge clk); start = 1'b1; t0 = cyc;
            @(negedge clk); start = 1'b0;

            pix = 0;
            while (pix < N_IN) begin
                if (in_ready) begin
                    in_valid = 1'b1;
                    in_data  = img[base + pix];
                    pix      = pix + 1;
                end else begin
                    in_valid = 1'b0;
                end
                @(negedge clk);
            end
            in_valid = 1'b0;

            guard = 0;
            while (!done && (guard < TIMEOUT)) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) begin
                $display("TIMEOUT on image %0d", index);
                errors = errors + 1;
            end else begin
                t1 = cyc;
                if (prediction_valid !== 1'b1) begin
                    $display("prediction_valid low with done, image %0d", index);
                    errors = errors + 1;
                end
                $fwrite(fh_out, "%0d %0d %0d", index, t1 - t0 + 1, prediction);
                for (q = 0; q < N_OUT; q = q + 1)
                    $fwrite(fh_out, " %0d", $signed(logits[q*ACC2 +: ACC2]));
                $fdisplay(fh_out, "");

                $fwrite(fh_hid, "%0d", index);
                for (q = 0; q < N_HID; q = q + 1)
                    $fwrite(fh_hid, " %0d", dut.u_fabric.hidden[q]);
                $fdisplay(fh_hid, "");
            end
            @(negedge clk);
        end
    endtask

    initial begin
        cyc = 32'd0; errors = 0;
        rst = 1'b1; start = 1'b0; in_valid = 1'b0;
        in_data = {{ACT_BITS{{1'b0}}}};
        $readmemh("img.hex", img);
        fh_out = $fopen("out.txt", "w");
        fh_hid = $fopen("hidden.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        for (im = 0; im < NIMG; im = im + 1)
            run_image(im);

        $fclose(fh_out);
        $fclose(fh_hid);
        if (errors != 0) $display("TB ERRORS: %0d", errors);
        else             $display("TB OK");
        $finish;
    end
endmodule
"""


# --------------------------------------------------------------------------
# Runners
# --------------------------------------------------------------------------

def _copy_sources(root: str, workdir: str, sources: Sequence[str]) -> List[str]:
    out = []
    for s in sources:
        src = os.path.join(root, RTL, s)
        dst = os.path.join(workdir, s)
        shutil.copyfile(src, dst)
        out.append(dst)
    return out


def run_param_equivalence(root: str, workdir: str,
                          images: Dict[str, ParamImage],
                          cfg: FabricConfig = FabricConfig()) -> dict:
    """Drive both backends with one stimulus stream and compare everything."""
    os.makedirs(workdir, exist_ok=True)
    w = derive_widths(cfg)
    stim = build_stimulus(images, cfg)
    packed = [s.packed(w["weight_addr_bits"], w["bias_addr_bits"]) for s in stim]
    bits = 2 + w["weight_addr_bits"] + 2 + w["bias_addr_bits"]
    with open(os.path.join(workdir, "stim.hex"), "w") as fh:
        fh.write("\n".join("%0*x" % ((bits + 3) // 4, v) for v in packed) + "\n")

    srcs = _copy_sources(root, workdir,
                         ["mnist_mlp_params_portable.v",
                          "mnist_mlp_params_openram.v"])
    tb = os.path.join(workdir, "tb_params.v")
    with open(tb, "w") as fh:
        fh.write(emit_param_tb(cfg))

    exe = os.path.join(workdir, "params.vvp")
    c = iverilog_compile(srcs + [tb], exe, workdir, std="2001",
                         top_params={"tb.NSTIM": len(stim)})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)
    r = _run([find_tool("vvp"), exe], cwd=workdir)
    if r.returncode != 0 or "TB OK" not in r.output:
        raise RuntimeError("simulation failed:\n" + r.output)

    exp_w, exp_b = expected_outputs(stim, images, cfg)
    def parse(field):
        """X means 'never driven yet'. It is only legal before the first
        enabled read on that port; that is checked below."""
        return None if "x" in field.lower() else int(field, 16)

    rows = []
    with open(os.path.join(workdir, "params_out.txt")) as fh:
        for line in fh:
            f = line.split()
            rows.append((int(f[0]), parse(f[1]), parse(f[2]),
                         parse(f[3]), parse(f[4])))

    cmp_w = cmp_b = 0
    mism_backend, mism_golden = [], []
    for idx, wp, wo, bp, bo in rows:
        if wp != wo:
            mism_backend.append(("weight", idx, hex(wp) if wp is not None else "x",
                                 hex(wo) if wo is not None else "x"))
        if bp != bo:
            mism_backend.append(("bias", idx, hex(bp) if bp is not None else "x",
                                 hex(bo) if bo is not None else "x"))
        if exp_w[idx] is not None:
            cmp_w += 1
            for tag, got in (("weight-portable", wp), ("weight-openram", wo)):
                if got != exp_w[idx]:
                    mism_golden.append((tag, idx,
                                        hex(got) if got is not None else "x",
                                        hex(exp_w[idx])))
        if exp_b[idx] is not None:
            cmp_b += 1
            for tag, got in (("bias-portable", bp), ("bias-openram", bo)):
                if got != exp_b[idx]:
                    mism_golden.append((tag, idx,
                                        hex(got) if got is not None else "x",
                                        hex(exp_b[idx])))

    return {
        "stimulus_cycles": len(stim),
        "logged_cycles": len(rows),
        "weight_comparisons": cmp_w,
        "bias_comparisons": cmp_b,
        "backend_mismatches": len(mism_backend),
        "golden_mismatches": len(mism_golden),
        "backend_mismatch_detail": mism_backend[:10],
        "golden_mismatch_detail": mism_golden[:10],
        "undriven_cycles_before_first_read": sum(
            1 for idx, wp, wo, bp, bo in rows
            if (wp is None) or (bp is None)),
    }


def run_top_inference(root: str, workdir: str, backend: str,
                      images_x: np.ndarray,
                      cfg: FabricConfig = FabricConfig()) -> dict:
    """Run MNIST images through mnist_mlp_top with the chosen backend."""
    os.makedirs(workdir, exist_ok=True)
    sources = PORTABLE_SOURCES if backend == "portable" else OPENRAM_SOURCES
    srcs = _copy_sources(root, workdir, sources)
    tb = os.path.join(workdir, "tb_top.v")
    with open(tb, "w") as fh:
        fh.write(emit_top_tb(cfg))

    x = np.asarray(images_x, dtype=np.int64)
    if x.ndim == 1:
        x = x[None, :]
    with open(os.path.join(workdir, "img.hex"), "w") as fh:
        fh.write("\n".join("%02x" % v for v in x.ravel()) + "\n")

    exe = os.path.join(workdir, "top.vvp")
    c = iverilog_compile(srcs + [tb], exe, workdir, std="2001",
                         top_params={"tb.NIMG": x.shape[0]})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)
    r = _run([find_tool("vvp"), exe], cwd=workdir, timeout=3600)
    if r.returncode != 0 or "TB OK" not in r.output:
        raise RuntimeError("simulation failed:\n" + r.output[-4000:])

    cycles, preds, logits = [], [], []
    with open(os.path.join(workdir, "out.txt")) as fh:
        for line in fh:
            f = line.split()
            cycles.append(int(f[1]))
            preds.append(int(f[2]))
            logits.append([int(v) for v in f[3:3 + cfg.n_out]])
    hidden = []
    with open(os.path.join(workdir, "hidden.txt")) as fh:
        for line in fh:
            f = line.split()
            hidden.append([int(v) for v in f[1:1 + cfg.n_hidden]])

    return {
        "backend": backend,
        "sources": [os.path.basename(s) for s in srcs],
        "cycles": cycles,
        "predictions": np.array(preds, dtype=np.int64),
        "logits": np.array(logits, dtype=np.int64),
        "hidden": np.array(hidden, dtype=np.int64),
        "log": r.output,
    }
