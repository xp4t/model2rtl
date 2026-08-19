"""Stage-3 behavioural verification infrastructure.

Everything here drives the FROZEN production RTL (fabric + a real parameter
backend + mnist_mlp_top) through Icarus and compares against the Stage-0 NumPy
integer golden model.  Nothing in this module is synthesized and nothing here
is allowed to change the design.

Three testbenches are generated:

  * ``tb_stage3``  -- back-to-back inference over N images under a chosen input
    stall pattern, with an optional cycle-by-cycle internal trace.
  * ``tb_reset``   -- synchronous reset injected at a chosen point of an
    inference, followed by a fresh inference that must still be exact.
  * the Stage-2 ``tb_top`` is reused where a plain run is enough.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

from . import contract as C
from .fabric import FabricConfig, derive_widths
from .param_image import ParamImage
from .param_verilog import emit_portable
from .sim import _run, find_tool, iverilog_compile
from .stage2_sim import OPENRAM_SOURCES, PORTABLE_SOURCES

#: neurons whose internal state is captured in the cycle trace
TRACE_L1_NEURONS = (0, 1, 31)
TRACE_L2_NEURONS = (0, 9)

#: stall patterns exercised at the top level
STALL_NONE, STALL_PERIODIC, STALL_PSEUDORANDOM = 0, 1, 2
STALL_NAMES = {0: "no stalls", 1: "periodic (every Nth input)",
               2: "deterministic pseudo-random (LFSR)"}


# --------------------------------------------------------------------------
# Testbench emitters
# --------------------------------------------------------------------------

def emit_stage3_tb(cfg: FabricConfig = FabricConfig()) -> str:
    w = derive_widths(cfg)
    l1 = " ".join('$fwrite(fh_tr, " %%0d", dut.u_fabric.acc1[%d]);' % j
                  for j in TRACE_L1_NEURONS)
    s1 = " ".join('$fwrite(fh_tr, " %%0d", dut.u_fabric.l1_sel_ext[%d]);' % j
                  for j in TRACE_L1_NEURONS)
    l2 = " ".join('$fwrite(fh_tr, " %%0d", dut.u_fabric.acc2[%d]);' % j
                  for j in TRACE_L2_NEURONS)
    s2 = " ".join('$fwrite(fh_tr, " %%0d", dut.u_fabric.l2_sel_ext[%d]);' % j
                  for j in TRACE_L2_NEURONS)
    return f"""// TEST-ONLY Stage-3 testbench. Never synthesized.
// Drives mnist_mlp_top back to back under a selectable input stall pattern and
// optionally captures a cycle-by-cycle internal trace of the fabric.
`timescale 1ns/1ps

module tb;
    parameter NIMG        = 4;
    parameter STALL_MODE  = 0;   // 0 none, 1 periodic, 2 pseudo-random
    parameter STALL_N     = 7;   // period for mode 1
    parameter TRACE_IMAGES = 0;  // capture the internal trace for the first M

    localparam N_IN     = {cfg.n_in};
    localparam N_HID    = {cfg.n_hidden};
    localparam N_OUT    = {cfg.n_out};
    localparam ACT_BITS = {w['act_bits']};
    localparam ACC2     = {w['layer2_acc_bits']};
    localparam PREDW    = {w['prediction_bits']};
    localparam LOGW     = {w['logits_bits']};
    localparam TIMEOUT  = 40000;

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

    integer fh_out, fh_hid, fh_tr, im, q, errors, done_pulses;
    reg [15:0] lfsr;

    // ---- cycle-by-cycle internal trace -----------------------------------
    integer trace_img;
    task capture;
        begin
            $fwrite(fh_tr, "%0d %0d %0d %0d %0d %0d %0d %0d %h %h",
                    trace_img, cyc,
                    dut.u_fabric.state, dut.u_fabric.mac_valid,
                    dut.u_fabric.layer_r, dut.u_fabric.fin_valid,
                    dut.u_fabric.fin_idx, dut.u_fabric.act_pipe,
                    dut.wmem_data, dut.bmem_data);
            {l1}
            {s1}
            $fwrite(fh_tr, " %0d %0d", dut.u_fabric.l1_accb,
                    dut.u_fabric.hid_next);
            {l2}
            {s2}
            $fwrite(fh_tr, " %0d", dut.u_fabric.logit_next);
            $fwrite(fh_tr, " %0d %0d %0d", dut.u_fabric.prod_00,
                    dut.u_fabric.prod_09, dut.u_fabric.prod_15);
            $fdisplay(fh_tr, "");
        end
    endtask

    // ---- one image --------------------------------------------------------
    task run_image;
        input integer index;
        integer base, pix, t0, t1, guard, bubble;
        begin
            base = index * N_IN;
            trace_img = index;

            @(negedge clk); start = 1'b1; t0 = cyc;
            if (index < TRACE_IMAGES) capture;
            @(negedge clk); start = 1'b0;

            pix    = 0;
            bubble = 0;
            while (pix < N_IN) begin
                if (index < TRACE_IMAGES) capture;
                if (in_ready && (bubble == 0)) begin
                    in_valid = 1'b1;
                    in_data  = img[base + pix];
                    pix      = pix + 1;
                    if (STALL_MODE == 1)
                        bubble = ((pix % STALL_N) == 0) ? 1 : 0;
                    else if (STALL_MODE == 2) begin
                        lfsr   = {{lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]}};
                        bubble = lfsr[0];
                    end else
                        bubble = 0;
                end else begin
                    in_valid = 1'b0;
                    bubble   = 0;
                end
                @(negedge clk);
            end
            in_valid = 1'b0;

            guard = 0;
            while (!done && (guard < TIMEOUT)) begin
                if (index < TRACE_IMAGES) capture;
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) begin
                $display("TIMEOUT on image %0d", index);
                errors = errors + 1;
            end else begin
                if (index < TRACE_IMAGES) capture;
                t1 = cyc;
                done_pulses = done_pulses + 1;
                if (prediction_valid !== 1'b1) begin
                    $display("prediction_valid low with done, image %0d", index);
                    errors = errors + 1;
                end
                if (busy !== 1'b1) begin
                    $display("busy low while done asserted, image %0d", index);
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
            // done must be a single-cycle pulse
            if (done !== 1'b0) begin
                $display("done still high one cycle later, image %0d", index);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        cyc = 32'd0; errors = 0; done_pulses = 0; lfsr = 16'hACE1;
        rst = 1'b1; start = 1'b0; in_valid = 1'b0;
        in_data = {{ACT_BITS{{1'b0}}}};
        $readmemh("img.hex", img);
        fh_out = $fopen("out.txt", "w");
        fh_hid = $fopen("hidden.txt", "w");
        fh_tr  = $fopen("trace.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        for (im = 0; im < NIMG; im = im + 1)
            run_image(im);

        if (done_pulses != NIMG) begin
            $display("expected %0d done pulses, saw %0d", NIMG, done_pulses);
            errors = errors + 1;
        end
        $fclose(fh_out); $fclose(fh_hid); $fclose(fh_tr);
        if (errors != 0) $display("TB ERRORS: %0d", errors);
        else             $display("TB OK");
        $finish;
    end
endmodule
"""


def emit_reset_tb(cfg: FabricConfig = FabricConfig()) -> str:
    w = derive_widths(cfg)
    return f"""// TEST-ONLY Stage-3 reset testbench. Never synthesized.
// Injects a synchronous reset RESET_AT cycles into an inference, checks that no
// state survives, then runs a fresh inference that must still be exact.
`timescale 1ns/1ps

module tb;
    parameter RESET_AT = 100;   // cycles after start; -1 = reset while idle
    parameter NIMG     = 2;

    localparam N_IN     = {cfg.n_in};
    localparam N_HID    = {cfg.n_hidden};
    localparam N_OUT    = {cfg.n_out};
    localparam ACT_BITS = {w['act_bits']};
    localparam ACC2     = {w['layer2_acc_bits']};
    localparam PREDW    = {w['prediction_bits']};
    localparam LOGW     = {w['logits_bits']};
    localparam TIMEOUT  = 40000;

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
    integer fh, fh_hid, q, k, guard, pix, errors, stale;

    task stream_and_finish;
        input integer index;
        integer base;
        begin
            base = index * N_IN;
            pix  = 0;
            while (pix < N_IN) begin
                if (in_ready) begin
                    in_valid = 1'b1;
                    in_data  = img[base + pix];
                    pix      = pix + 1;
                end else
                    in_valid = 1'b0;
                @(negedge clk);
            end
            in_valid = 1'b0;
            guard = 0;
            while (!done && (guard < TIMEOUT)) begin
                @(negedge clk);
                guard = guard + 1;
            end
        end
    endtask

    initial begin
        errors = 0; stale = 0;
        rst = 1'b1; start = 1'b0; in_valid = 1'b0;
        in_data = {{ACT_BITS{{1'b0}}}};
        $readmemh("img.hex", img);
        fh     = $fopen("out.txt", "w");
        fh_hid = $fopen("hidden.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        // ---- an inference that gets reset part way through ----------------
        if (RESET_AT >= 0) begin
            @(negedge clk); start = 1'b1;
            @(negedge clk); start = 1'b0;
            pix = 0;
            for (k = 0; k < RESET_AT; k = k + 1) begin
                if (in_ready && (pix < N_IN)) begin
                    in_valid = 1'b1;
                    in_data  = img[pix];
                    pix      = pix + 1;
                end else
                    in_valid = 1'b0;
                @(negedge clk);
            end
        end

        // ---- assert reset --------------------------------------------------
        in_valid = 1'b0;
        rst = 1'b1;
        @(negedge clk);
        @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        // no inference state may survive
        if (busy !== 1'b0)             begin stale = stale + 1;
            $display("busy high after reset"); end
        if (done !== 1'b0)             begin stale = stale + 1;
            $display("done high after reset"); end
        if (prediction_valid !== 1'b0) begin stale = stale + 1;
            $display("prediction_valid high after reset"); end
        if (in_ready !== 1'b0)         begin stale = stale + 1;
            $display("in_ready high after reset"); end
        for (q = 0; q < N_HID; q = q + 1)
            if (dut.u_fabric.hidden[q] !== {{ACT_BITS{{1'b0}}}}) begin
                stale = stale + 1;
                $display("hidden[%0d] not cleared by reset", q);
            end
        for (q = 0; q < N_HID; q = q + 1)
            if (dut.u_fabric.acc1[q] !== 0) begin
                stale = stale + 1;
                $display("acc1[%0d] not cleared by reset", q);
            end
        for (q = 0; q < N_OUT; q = q + 1)
            if (dut.u_fabric.acc2[q] !== 0) begin
                stale = stale + 1;
                $display("acc2[%0d] not cleared by reset", q);
            end
        for (q = 0; q < N_OUT; q = q + 1)
            if (dut.u_fabric.logit_reg[q] !== 0) begin
                stale = stale + 1;
                $display("logit_reg[%0d] not cleared by reset", q);
            end

        // ---- a fresh inference, which must still be exact ------------------
        @(negedge clk); start = 1'b1;
        @(negedge clk); start = 1'b0;
        stream_and_finish(1);
        if (!done) begin
            $display("TIMEOUT after reset");
            errors = errors + 1;
        end else begin
            $fwrite(fh, "1 0 %0d", prediction);
            for (q = 0; q < N_OUT; q = q + 1)
                $fwrite(fh, " %0d", $signed(logits[q*ACC2 +: ACC2]));
            $fdisplay(fh, "");
            $fwrite(fh_hid, "1");
            for (q = 0; q < N_HID; q = q + 1)
                $fwrite(fh_hid, " %0d", dut.u_fabric.hidden[q]);
            $fdisplay(fh_hid, "");
        end

        $fclose(fh); $fclose(fh_hid);
        $display("STALE %0d", stale);
        if (errors != 0) $display("TB ERRORS: %0d", errors);
        else             $display("TB OK");
        $finish;
    end
endmodule
"""


# --------------------------------------------------------------------------
# Runners
# --------------------------------------------------------------------------

def _sources(root: str, backend: str) -> List[str]:
    names = PORTABLE_SOURCES if backend == "portable" else OPENRAM_SOURCES
    return [os.path.join(root, "rtl", n) for n in names]


def _write_images(workdir: str, x: np.ndarray) -> None:
    with open(os.path.join(workdir, "img.hex"), "w") as fh:
        fh.write("\n".join("%02x" % v for v in np.asarray(x).ravel()) + "\n")


def _parse_out(path: str, n_out: int):
    cycles, preds, logits = [], [], []
    with open(path) as fh:
        for line in fh:
            f = line.split()
            cycles.append(int(f[1]))
            preds.append(int(f[2]))
            logits.append([int(v) for v in f[3:3 + n_out]])
    return cycles, np.array(preds, dtype=np.int64), np.array(logits, dtype=np.int64)


def _parse_hidden(path: str, n_hid: int) -> np.ndarray:
    rows = []
    with open(path) as fh:
        for line in fh:
            f = line.split()
            rows.append([int(v) for v in f[1:1 + n_hid]])
    return np.array(rows, dtype=np.int64)


def run_images(root: str, workdir: str, backend: str, x: np.ndarray,
               stall_mode: int = STALL_NONE, stall_n: int = 7,
               trace_images: int = 0, params_file: str | None = None,
               cfg: FabricConfig = FabricConfig()) -> dict:
    """Run x through mnist_mlp_top with the chosen backend and stall pattern."""
    os.makedirs(workdir, exist_ok=True)
    x = np.asarray(x, dtype=np.int64)
    if x.ndim == 1:
        x = x[None, :]

    srcs = []
    for p in _sources(root, backend):
        dst = os.path.join(workdir, os.path.basename(p))
        if params_file and os.path.basename(p) == "mnist_mlp_params_portable.v":
            if os.path.abspath(params_file) != os.path.abspath(dst):
                shutil.copyfile(params_file, dst)
        elif os.path.abspath(p) != os.path.abspath(dst):
            shutil.copyfile(p, dst)
        srcs.append(dst)

    tb = os.path.join(workdir, "tb_stage3.v")
    with open(tb, "w") as fh:
        fh.write(emit_stage3_tb(cfg))
    _write_images(workdir, x)

    exe = os.path.join(workdir, "stage3.vvp")
    c = iverilog_compile(srcs + [tb], exe, workdir, std="2001",
                         top_params={"tb.NIMG": x.shape[0],
                                     "tb.STALL_MODE": stall_mode,
                                     "tb.STALL_N": stall_n,
                                     "tb.TRACE_IMAGES": trace_images})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)
    r = _run([find_tool("vvp"), exe], cwd=workdir, timeout=7200)
    if r.returncode != 0 or "TB OK" not in r.output:
        raise RuntimeError("simulation failed:\n" + r.output[-4000:])

    cycles, preds, logits = _parse_out(os.path.join(workdir, "out.txt"),
                                       cfg.n_out)
    return {
        "backend": backend,
        "stall_mode": stall_mode,
        "cycles": cycles,
        "predictions": preds,
        "logits": logits,
        "hidden": _parse_hidden(os.path.join(workdir, "hidden.txt"),
                                cfg.n_hidden),
        "trace_path": os.path.join(workdir, "trace.txt"),
        "log": r.output,
    }


def run_reset(root: str, workdir: str, backend: str, x: np.ndarray,
              reset_at: int, cfg: FabricConfig = FabricConfig()) -> dict:
    """Inject a synchronous reset reset_at cycles into an inference."""
    os.makedirs(workdir, exist_ok=True)
    x = np.asarray(x, dtype=np.int64)
    srcs = []
    for p in _sources(root, backend):
        dst = os.path.join(workdir, os.path.basename(p))
        if os.path.abspath(p) != os.path.abspath(dst):
            shutil.copyfile(p, dst)
        srcs.append(dst)
    tb = os.path.join(workdir, "tb_reset.v")
    with open(tb, "w") as fh:
        fh.write(emit_reset_tb(cfg))
    _write_images(workdir, x)

    exe = os.path.join(workdir, "reset.vvp")
    c = iverilog_compile(srcs + [tb], exe, workdir, std="2001",
                         top_params={"tb.RESET_AT": reset_at,
                                     "tb.NIMG": x.shape[0]})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)
    r = _run([find_tool("vvp"), exe], cwd=workdir, timeout=3600)
    if r.returncode != 0 or "TB OK" not in r.output:
        raise RuntimeError("simulation failed:\n" + r.output[-4000:])
    stale = int([l for l in r.output.splitlines()
                 if l.startswith("STALE")][0].split()[1])
    _, preds, logits = _parse_out(os.path.join(workdir, "out.txt"), cfg.n_out)
    return {
        "reset_at": reset_at,
        "stale_state_failures": stale,
        "predictions": preds,
        "logits": logits,
        "hidden": _parse_hidden(os.path.join(workdir, "hidden.txt"),
                                cfg.n_hidden),
        "log": r.output,
    }


def run_with_params(root: str, workdir: str, images: Dict[str, ParamImage],
                    x: np.ndarray, cfg: FabricConfig = FabricConfig(),
                    **kwargs) -> Tuple[dict, str]:
    """Generate a portable backend from arbitrary parameter images and run it.

    Used for the argmax, arithmetic-edge and alternate-model tests: the whole
    production flow is exercised, only the parameter data differs.
    """
    os.makedirs(workdir, exist_ok=True)
    params = os.path.join(workdir, "mnist_mlp_params_portable.v")
    with open(params, "w") as fh:
        fh.write(emit_portable(images, cfg))
    out = run_images(root, workdir, "portable", x, params_file=params,
                     cfg=cfg, **kwargs)
    return out, params


# --------------------------------------------------------------------------
# Cycle-aware trace checking
# --------------------------------------------------------------------------

TRACE_FIELDS = (["img", "cyc", "state", "mac_valid", "layer_r", "fin_valid",
                 "fin_idx", "act_pipe", "wmem_data", "bmem_data"]
                + ["acc1_%d" % j for j in TRACE_L1_NEURONS]
                + ["sel1_%d" % j for j in TRACE_L1_NEURONS]
                + ["l1_accb", "hid_next"]
                + ["acc2_%d" % j for j in TRACE_L2_NEURONS]
                + ["sel2_%d" % j for j in TRACE_L2_NEURONS]
                + ["logit_next", "prod_00", "prod_09", "prod_15"])


def _twos(value: int, bits: int) -> int:
    return int(value) & ((1 << bits) - 1)


def check_trace(trace_path: str, x: np.ndarray, model, images,
                cfg: FabricConfig = FabricConfig()) -> dict:
    """Replay the internal trace against the golden model, cycle by cycle.

    Every check below is anchored to a specific (image, cycle, signal) so the
    FIRST causal divergence is localised rather than only the top-level result.
    """
    from .golden import alphabet_lookup, requantize_relu_u8

    w = derive_widths(cfg)
    alpha = cfg.alphabet
    i1 = model.layer1_weight_indices
    i2 = model.layer2_weight_indices
    b1 = model.layer1_bias
    b2 = model.layer2_bias
    w1 = alphabet_lookup(i1)
    w2 = alphabet_lookup(i2)
    pack1 = images["weights_l1"].rows
    pack2 = images["weights_l2"].rows

    x = np.asarray(x, dtype=np.int64)
    dot1 = x @ w1
    hidden = requantize_relu_u8(dot1 + b1)
    dot2 = hidden @ w2
    logits = dot2 + b2

    failures: List[str] = []
    counts = {k: 0 for k in ("mac_l1", "mac_l2", "fin_l1", "fin_l2",
                             "weight_word", "bias_word", "product",
                             "accumulator", "requant", "logit")}

    def fail(img, cyc, what, got, want):
        failures.append("image %d cycle %s: %s = %s, expected %s"
                        % (img, cyc, what, got, want))

    state = {}
    with open(trace_path) as fh:
        for line in fh:
            f = line.split()
            if len(f) != len(TRACE_FIELDS):
                raise RuntimeError("trace line has %d fields, expected %d"
                                   % (len(f), len(TRACE_FIELDS)))
            r = dict(zip(TRACE_FIELDS, f))
            img = int(r["img"])
            cyc = r["cyc"]
            st = state.setdefault(img, {"mac1": 0, "mac2": 0,
                                        "run1": {j: 0 for j in TRACE_L1_NEURONS},
                                        "run2": {j: 0 for j in TRACE_L2_NEURONS}})
            mac = int(r["mac_valid"])
            fin = int(r["fin_valid"])
            layer = int(r["layer_r"])
            act = int(r["act_pipe"])

            if mac and layer == 0:
                i = st["mac1"]
                if i >= cfg.n_in:
                    fail(img, cyc, "layer-1 MAC count", i + 1, cfg.n_in)
                    continue
                counts["mac_l1"] += 1
                if act != int(x[img, i]):
                    fail(img, cyc, "act_pipe (input %d)" % i, act, int(x[img, i]))
                counts["weight_word"] += 1
                if int(r["wmem_data"], 16) != pack1[i]:
                    fail(img, cyc, "wmem_data for input %d (off-by-one?)" % i,
                         r["wmem_data"], "%032x" % pack1[i])
                for tag, k in (("prod_00", 0), ("prod_09", 9), ("prod_15", 15)):
                    counts["product"] += 1
                    if int(r[tag]) != act * int(alpha[k]):
                        fail(img, cyc, "%s (shared product bank)" % tag,
                             r[tag], act * int(alpha[k]))
                for j in TRACE_L1_NEURONS:
                    counts["accumulator"] += 1
                    if int(r["acc1_%d" % j]) != st["run1"][j]:
                        fail(img, cyc, "acc1[%d] before update" % j,
                             r["acc1_%d" % j], st["run1"][j])
                    want = int(x[img, i]) * int(alpha[int(i1[i, j])])
                    counts["product"] += 1
                    if int(r["sel1_%d" % j]) != want:
                        fail(img, cyc, "selected product for neuron %d, input %d"
                             % (j, i), r["sel1_%d" % j], want)
                    st["run1"][j] += want
                st["mac1"] += 1

            elif mac and layer == 1:
                i = st["mac2"]
                if i >= cfg.n_hidden:
                    fail(img, cyc, "layer-2 MAC count", i + 1, cfg.n_hidden)
                    continue
                counts["mac_l2"] += 1
                if act != int(hidden[img, i]):
                    fail(img, cyc, "act_pipe (hidden %d)" % i, act,
                         int(hidden[img, i]))
                counts["weight_word"] += 1
                if int(r["wmem_data"], 16) != pack2[i]:
                    fail(img, cyc, "wmem_data for hidden %d (off-by-one?)" % i,
                         r["wmem_data"], "%032x" % pack2[i])
                for j in TRACE_L2_NEURONS:
                    counts["accumulator"] += 1
                    if int(r["acc2_%d" % j]) != st["run2"][j]:
                        fail(img, cyc, "acc2[%d] before update" % j,
                             r["acc2_%d" % j], st["run2"][j])
                    want = int(hidden[img, i]) * int(alpha[int(i2[i, j])])
                    counts["product"] += 1
                    if int(r["sel2_%d" % j]) != want:
                        fail(img, cyc, "selected product for logit %d, hidden %d"
                             % (j, i), r["sel2_%d" % j], want)
                    st["run2"][j] += want
                st["mac2"] += 1

            if fin and layer == 0:
                j = int(r["fin_idx"])
                counts["fin_l1"] += 1
                counts["bias_word"] += 1
                want_b = _twos(int(b1[j]), w["bias_data_bits"])
                if int(r["bmem_data"], 16) != want_b:
                    fail(img, cyc, "bmem_data for hidden neuron %d (off-by-one?)"
                         % j, r["bmem_data"], "%06x" % want_b)
                counts["requant"] += 1
                if int(r["l1_accb"]) != int(dot1[img, j] + b1[j]):
                    fail(img, cyc, "biased accumulator for neuron %d" % j,
                         r["l1_accb"], int(dot1[img, j] + b1[j]))
                if int(r["hid_next"]) != int(hidden[img, j]):
                    fail(img, cyc, "requantised hidden %d" % j,
                         r["hid_next"], int(hidden[img, j]))

            if fin and layer == 1:
                j = int(r["fin_idx"])
                counts["fin_l2"] += 1
                counts["bias_word"] += 1
                want_b = _twos(int(b2[j]), w["bias_data_bits"])
                if int(r["bmem_data"], 16) != want_b:
                    fail(img, cyc, "bmem_data for logit %d (off-by-one?)" % j,
                         r["bmem_data"], "%06x" % want_b)
                counts["logit"] += 1
                if int(r["logit_next"]) != int(logits[img, j]):
                    fail(img, cyc, "logit %d" % j, r["logit_next"],
                         int(logits[img, j]))

    for img, st in state.items():
        if st["mac1"] != cfg.n_in:
            failures.append("image %d: %d layer-1 MACs, expected %d"
                            % (img, st["mac1"], cfg.n_in))
        if st["mac2"] != cfg.n_hidden:
            failures.append("image %d: %d layer-2 MACs, expected %d"
                            % (img, st["mac2"], cfg.n_hidden))

    return {
        "images_traced": len(state),
        "checks": counts,
        "total_checks": sum(counts.values()),
        "failures": len(failures),
        "first_failures": failures[:10],
    }


# --------------------------------------------------------------------------
# Crafted parameter sets (argmax, arithmetic edges, alternate model)
# --------------------------------------------------------------------------

def images_from_arrays(i1, b1, i2, b2, cfg: FabricConfig = FabricConfig()):
    from .golden import IntegerModel
    from .param_image import build_images
    m = IntegerModel(layer1_weight_indices=np.asarray(i1, dtype=np.int64),
                     layer2_weight_indices=np.asarray(i2, dtype=np.int64),
                     layer1_bias=np.asarray(b1, dtype=np.int64),
                     layer2_bias=np.asarray(b2, dtype=np.int64))
    m.validate()
    return m, build_images(m, cfg)


def zero_weight_model(b2, cfg: FabricConfig = FabricConfig()):
    """All weights at alphabet level 0, so the logits are exactly b2."""
    zero = cfg.k // 2
    return images_from_arrays(
        np.full((cfg.n_in, cfg.n_hidden), zero),
        np.zeros(cfg.n_hidden, dtype=np.int64),
        np.full((cfg.n_hidden, cfg.n_out), zero),
        np.asarray(b2, dtype=np.int64), cfg)


def alternate_model(seed: int, cfg: FabricConfig = FabricConfig()):
    """A deterministic second valid parameter set. No training involved."""
    rng = np.random.default_rng(seed)
    w = derive_widths(cfg)
    lim1 = 1 << (w["layer1_bias_bits"] - 3)
    lim2 = 1 << (w["layer2_bias_bits"] - 3)
    return images_from_arrays(
        rng.integers(0, cfg.k, (cfg.n_in, cfg.n_hidden)),
        rng.integers(-lim1, lim1, cfg.n_hidden),
        rng.integers(0, cfg.k, (cfg.n_hidden, cfg.n_out)),
        rng.integers(-lim2, lim2, cfg.n_out), cfg)


def test_set(n: int, policy: str = "first") -> Tuple[np.ndarray, np.ndarray, dict]:
    """Deterministic MNIST subset. Records exactly which indices were used."""
    cache = os.path.expanduser("~/.keras/datasets/mnist.npz")
    with np.load(cache) as z:
        x_all = z["x_test"].reshape(-1, C.INPUT_DIM).astype(np.int64)
        y_all = z["y_test"].astype(np.int64)
    if policy == "first":
        idx = np.arange(n)
    else:
        raise ValueError("unknown selection policy %r" % policy)
    x, y = x_all[idx], y_all[idx]
    meta = {
        "selection_policy": "first %d images of the official MNIST test set, "
                            "in order; no filtering of any kind" % n,
        "count": int(n),
        "indices_first": [int(v) for v in idx[:10]],
        "indices_last": [int(v) for v in idx[-10:]],
        "indices_sha256": hashlib.sha256(idx.astype(np.int64).tobytes()).hexdigest(),
        "images_sha256": hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(np.ascontiguousarray(y).tobytes()).hexdigest(),
        "label_histogram": [int(v) for v in np.bincount(y, minlength=10)],
    }
    return x, y, meta
