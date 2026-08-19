"""Stage 4: dual-target synthesis portability and gate-level verification.

This module never touches the production RTL.  It only

  * writes two independent Yosys synthesis scripts (FPGA-oriented and
    generic/ASIC-oriented) that *read* the frozen sources,
  * parses the resulting logs and statistics honestly,
  * emits port-only gate-level testbenches, and
  * guards, mechanically, that gate-level simulation compiles the synthesized
    netlist and never the production RTL implementation.

The Stage-0 integer golden model remains the sole arithmetic oracle; nothing
here produces expected values.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

from .fabric import FabricConfig, derive_widths
from .sim import find_tool, _run

# The exact production sources, in read order.  Stage 4 must not add, remove,
# patch or copy-and-edit any of them.
PRODUCTION_SOURCES = [
    "rtl/mnist_mlp_fabric.v",
    "rtl/mnist_mlp_params_portable.v",
    "rtl/mnist_mlp_params_sel_portable.v",
    "rtl/mnist_mlp_top.v",
]

# Files that carry a *behavioural implementation* of the design.  None of these
# may ever appear in a gate-level simulation source list.
FORBIDDEN_IN_GLS = [
    "mnist_mlp_fabric.v",
    "mnist_mlp_params_portable.v",
    "mnist_mlp_params_openram.v",
    "mnist_mlp_params_sel_portable.v",
    "mnist_mlp_params_sel_openram.v",
    "mnist_mlp_top.v",
]

TOP = "mnist_mlp_top"

# Top-level port list, frozen by Stage 1 / Stage 2.  The synthesized netlist
# must expose exactly these and nothing else: a parameter cannot be smuggled in
# through an extra port.
TOP_PORTS = ["clk", "rst", "start", "in_ready", "in_valid", "in_data",
             "busy", "done", "prediction_valid", "prediction", "logits"]

# Total bits of the four canonical Stage-2 parameter images:
#   784*128 + 32*40 + 32*22 + 10*17
PARAM_IMAGE_BITS = 784 * 128 + 32 * 40 + 32 * 22 + 10 * 17

FPGA_FAMILY = "ice40"
FPGA_FAMILY_RATIONALE = (
    "synth_ice40 is present in the installed Yosys and the matching official "
    "simulation library <datdir>/ice40/cells_sim.v exists and is complete, so "
    "the synthesized netlist can be simulated with the vendor-equivalent cell "
    "models rather than hand-written stand-ins.  ECP5 was therefore not needed."
)


class Stage4Error(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Hashing / environment
# --------------------------------------------------------------------------

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def yosys_datdir() -> str:
    yosys = find_tool("yosys")
    cfg = os.path.join(os.path.dirname(yosys), "yosys-config")
    r = _run([cfg, "--datdir"])
    if r.returncode != 0:
        raise Stage4Error("yosys-config --datdir failed: %s" % r.stderr)
    return r.stdout.strip()


def yosys_version() -> str:
    r = _run([find_tool("yosys"), "-V"])
    return r.stdout.strip().splitlines()[0]


def iverilog_version() -> str:
    r = _run([find_tool("iverilog"), "-V"])
    return r.stdout.strip().splitlines()[0]


def simlib_paths() -> Dict[str, str]:
    """Official Yosys simulation libraries for both targets.  Fails closed."""
    d = yosys_datdir()
    paths = {
        "fpga": os.path.join(d, FPGA_FAMILY, "cells_sim.v"),
        "generic": os.path.join(d, "simcells.v"),
    }
    for kind, p in paths.items():
        if not os.path.isfile(p):
            raise Stage4Error(
                "required %s simulation cell library is missing: %s -- Stage 4 "
                "cannot proceed without official cell models" % (kind, p))
    return paths


# --------------------------------------------------------------------------
# Synthesis scripts
# --------------------------------------------------------------------------

def _read_lines(root: str, defer: bool) -> List[str]:
    flag = "read_verilog -defer " if defer else "read_verilog "
    return [flag + os.path.join(root, s) for s in PRODUCTION_SOURCES]


def fpga_script(root: str, netlist: str, json_out: str) -> str:
    """FPGA-oriented flow: the stock Yosys iCE40 target, unmodified."""
    return "\n".join(
        _read_lines(root, defer=True) + [
            "synth_ice40 -top %s" % TOP,
            "check -assert",
            "stat",
            "write_json %s" % json_out,
            "write_verilog -noattr -noexpr %s" % netlist,
            "",
        ])


def generic_script(root: str, netlist: str, json_out: str) -> str:
    """Generic / ASIC-oriented flow: standard Yosys logic synthesis down to
    the Yosys generic gate vocabulary.  Independent of the FPGA flow: it shares
    no Yosys command with it beyond reading the same sources."""
    return "\n".join(
        _read_lines(root, defer=False) + [
            "hierarchy -check -top %s" % TOP,
            "proc",
            "flatten",
            "opt -full",
            "memory",
            "opt -full",
            "techmap",
            "opt -full",
            "simplemap",
            "dfflegalize -cell $_DFF_P_ 01",
            "abc -g simple",
            "setundef -zero",
            "opt_clean -purge",
            "check -assert",
            "stat",
            "write_json %s" % json_out,
            "write_verilog -noattr -noexpr %s" % netlist,
            "",
        ])


SCRIPT_BUILDERS = {"fpga": fpga_script, "generic": generic_script}


# --------------------------------------------------------------------------
# Log parsing
# --------------------------------------------------------------------------

_STAT_HDR = re.compile(r"^=== (\S+) ===")
_STAT_ROW = re.compile(r"^\s+(\d+)\s+(\S+)\s*$")
_PROBLEMS = re.compile(r"Found and reported (\d+) problems")


def parse_stat(log_text: str, top: str = TOP) -> Dict[str, int]:
    """Cell counts of the *last* per-module statistics block for the top module.

    The block is the local (non-hierarchical) count Yosys prints last, which for
    a flattened design is the whole design.
    """
    cells: Dict[str, int] = {}
    in_top = False
    for line in log_text.splitlines():
        m = _STAT_HDR.match(line)
        if m:
            in_top = (m.group(1) == top)
            if in_top:
                cells = {}
            continue
        if not in_top:
            continue
        if line.startswith("Executing") or re.match(r"^\d+\.", line):
            in_top = False
            continue
        m = _STAT_ROW.match(line)
        if m and not m.group(2).endswith(("wires", "bits", "ports", "cells",
                                          "memories", "processes",
                                          "submodules")):
            cells[m.group(2)] = int(m.group(1))
    return cells


def parse_check(log_text: str) -> Dict[str, object]:
    """Everything the Yosys log says about the health of the mapped design.

    `check -assert` alone would abort on a problem, but Stage 4 must not infer
    success from an exit code, so the specific findings are counted here too.
    """
    lines = log_text.splitlines()
    problems = [int(m) for m in _PROBLEMS.findall(log_text)]
    errors = [l for l in lines if l.startswith("ERROR")]
    warnings = sorted({l for l in lines if l.startswith("Warning:")})

    def count(pattern: str) -> int:
        return sum(1 for l in lines if re.search(pattern, l, re.I))

    return {
        "check_blocks": len(problems),
        "problems_reported": sum(problems),
        "error_lines": errors,
        "warning_lines": warnings,
        # explicit findings, not inferred from the exit status
        "latches_inferred_lines": count(r"^Inferring latch for"),
        "latches_explicitly_not_inferred_lines": count(r"^No latch inferred"),
        "multiple_driver_lines": count(
            r"multiple (conflicting )?drivers|conflicting drivers"),
        "undriven_net_lines": count(
            r"is used but has no driver|found and reported .* undriven"),
        "wire_without_driver_lines": count(r"has no driver"),
    }


def blackboxes(json_path: str) -> List[str]:
    """Module names instantiated by the netlist that the netlist does not
    define, i.e. unresolved blackboxes."""
    import json
    with open(json_path) as fh:
        doc = json.load(fh)
    mods = doc.get("modules", {})
    defined = set(mods)
    used = set()
    for m in mods.values():
        for c in m.get("cells", {}).values():
            used.add(c["type"])
    unresolved = sorted(t for t in used - defined if not t.startswith("$"))
    # A cell whose module is declared with the blackbox attribute is also
    # unresolved even if a stub is present.
    for name, m in mods.items():
        attrs = m.get("attributes", {})
        if attrs.get("blackbox") in (1, "1", True) and name in used:
            if name not in unresolved:
                unresolved.append(name)
    return sorted(unresolved)


# --------------------------------------------------------------------------
# Synthesis driver
# --------------------------------------------------------------------------

@dataclass
class SynthResult:
    kind: str
    outdir: str
    script_path: str
    script_sha256: str
    log_path: str
    netlist_path: str
    netlist_sha256: str
    json_path: str
    returncode: int
    cells: Dict[str, int]
    check: Dict[str, object]
    blackboxes: List[str]
    seconds: float

    @property
    def ok(self) -> bool:
        return (self.returncode == 0 and not self.check["error_lines"]
                and self.check["problems_reported"] == 0
                and not self.blackboxes
                and os.path.getsize(self.netlist_path) > 0)


def run_synth(root: str, kind: str, outdir: str, builder=None,
              tag: str | None = None, top: str | None = None) -> SynthResult:
    import time
    if kind not in SCRIPT_BUILDERS:
        raise Stage4Error("unknown synthesis target %r" % kind)
    tag = tag or kind
    top = top or TOP
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)           # every run starts from a clean dir
    os.makedirs(outdir)

    netlist = os.path.join(outdir, "%s_netlist.v" % tag)
    json_out = os.path.join(outdir, "%s_netlist.json" % tag)
    script = (builder(root, kind, netlist, json_out) if builder is not None
              else SCRIPT_BUILDERS[kind](root, netlist, json_out))
    script_path = os.path.join(outdir, "synth_%s.ys" % tag)
    with open(script_path, "w") as fh:
        fh.write(script)

    log_path = os.path.join(outdir, "yosys_%s.log" % tag)
    t0 = time.time()
    r = _run([find_tool("yosys"), "-l", log_path, script_path], cwd=outdir,
             timeout=7200)
    seconds = time.time() - t0
    log_text = open(log_path).read() if os.path.isfile(log_path) else r.stdout

    have_netlist = os.path.isfile(netlist)
    return SynthResult(
        kind=kind, outdir=outdir, script_path=script_path,
        script_sha256=sha256_text(script), log_path=log_path,
        netlist_path=netlist,
        netlist_sha256=sha256_file(netlist) if have_netlist else "",
        json_path=json_out, returncode=r.returncode,
        cells=parse_stat(log_text, top), check=parse_check(log_text),
        blackboxes=blackboxes(json_out) if os.path.isfile(json_out) else
                   ["<no json written>"],
        seconds=seconds)


# --------------------------------------------------------------------------
# Netlist inspection
# --------------------------------------------------------------------------

def netlist_modules(path: str) -> List[str]:
    return re.findall(r"^module\s+\\?([A-Za-z_$][\w$]*)\s*\(", open(path).read(),
                      re.M)


def netlist_top_ports(path: str, top: str = TOP) -> List[str]:
    text = open(path).read()
    m = re.search(r"^module\s+%s\s*\((.*?)\);" % top, text, re.M | re.S)
    if not m:
        raise Stage4Error("top module %s not found in %s" % (top, path))
    return [p.strip().lstrip("\\") for p in m.group(1).split(",") if p.strip()]


def netlist_evidence(path: str, kind: str,
                     top: str = TOP) -> Dict[str, object]:
    """Structural evidence that the netlist is a synthesized CELL netlist, is
    self-contained, and carries the parameter contents.

    A behavioural leftover would show up as an `always` block, a `case`
    statement, or an arithmetic operator; a netlist that got its parameters
    from outside would need $readmemh, an initial block, or an extra port.
    """
    text = open(path).read()
    body = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    body = "\n".join(l for l in body.splitlines()
                      if not l.lstrip().startswith("//"))
    ram_inits = re.findall(r"\.INIT_[0-9A-F]\(256'h([0-9a-fA-F]{64})\)", text)
    init_bits = sum(len(s) * 4 for s in ram_inits)
    nonzero_init_bits = sum(bin(int(s, 16)).count("1") for s in ram_inits)
    instances = re.findall(r"^\s+(SB_[A-Z0-9_]+|\\\$_[A-Z0-9_]+_)\s", body, re.M)
    ports = netlist_top_ports(path, top)
    return {
        "modules_defined": sorted(set(netlist_modules(path))),
        "top_ports": ports,
        "top_ports_match_frozen_interface": ports == TOP_PORTS,
        # -- no behavioural leftovers --
        "always_blocks": len(re.findall(r"\balways\b", body)),
        "case_statements": len(re.findall(r"\bcase\b", body)),
        "arithmetic_operators": len(re.findall(r"[^*/](?:\*|\+|/|%)[^/*]", body)),
        # -- self contained: parameters cannot come from outside --
        "contains_readmemh": ("$readmemh" in body) or ("$readmemb" in body),
        "contains_initial_block": bool(re.search(r"^\s*initial\b", body, re.M)),
        "contains_dollar_system_task": bool(re.search(r"\$[a-z]", body)),
        # -- cell netlist --
        "cell_instances": len(instances),
        "cell_instance_types": sorted(set(instances)),
        "assign_statements": len(re.findall(r"^\s*assign\b", body, re.M)),
        # -- parameter storage --
        "ram_init_params": len(ram_inits),
        "ram_init_bits": init_bits,
        "ram_init_one_bits": nonzero_init_bits,
        "parameter_image_bits_required": PARAM_IMAGE_BITS,
        "parameter_storage": ("block RAM initialisation data"
                              if ram_inits else "constant combinational logic"),
        "bytes": os.path.getsize(path),
    }


# --------------------------------------------------------------------------
# Port-only gate-level testbenches
# --------------------------------------------------------------------------

def emit_gls_tb(cfg: FabricConfig = FabricConfig()) -> str:
    """Gate-level testbench.  TOP-LEVEL PORTS ONLY -- no hierarchical reference
    into the DUT, because synthesis legitimately destroys internal names.  It
    therefore compiles unchanged against the behavioural RTL, the FPGA netlist
    and the generic netlist."""
    w = derive_widths(cfg)
    return f"""// TEST-ONLY Stage-4 gate-level testbench.  Never synthesized.
// Observes ONLY the frozen top-level ports of mnist_mlp_top.
`timescale 1ns/1ps

module tb;
    parameter NIMG       = 4;
    parameter STALL_MODE = 0;   // 0 = none, 1 = periodic bubble every STALL_N
    parameter STALL_N    = 7;

    localparam N_IN     = {cfg.n_in};
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

    integer fh_out, im, q, errors, done_pulses;

    task run_image;
        input integer index;
        integer base, pix, t0, t1, guard, bubble;
        begin
            base = index * N_IN;
            @(negedge clk); start = 1'b1; t0 = cyc;
            @(negedge clk); start = 1'b0;

            pix = 0; bubble = 0;
            while (pix < N_IN) begin
                if (in_ready && (bubble == 0)) begin
                    in_valid = 1'b1;
                    in_data  = img[base + pix];
                    pix      = pix + 1;
                    if (STALL_MODE == 1)
                        bubble = ((pix % STALL_N) == 0) ? 1 : 0;
                    else
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
                @(negedge clk); guard = guard + 1;
            end
            if (!done) begin
                $display("TIMEOUT on image %0d", index);
                errors = errors + 1;
            end else begin
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
            end
            @(negedge clk);
            if (done !== 1'b0) begin
                $display("done still high one cycle later, image %0d", index);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        cyc = 32'd0; errors = 0; done_pulses = 0;
        rst = 1'b1; start = 1'b0; in_valid = 1'b0;
        in_data = {{ACT_BITS{{1'b0}}}};
        $readmemh("img.hex", img);
        fh_out = $fopen("out.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        // Back to back: NIMG inferences in ONE simulation, no reset between.
        for (im = 0; im < NIMG; im = im + 1)
            run_image(im);

        if (done_pulses != NIMG) begin
            $display("expected %0d done pulses, saw %0d", NIMG, done_pulses);
            errors = errors + 1;
        end
        $fclose(fh_out);
        if (errors != 0) $display("TB ERRORS: %0d", errors);
        else             $display("TB OK");
        $finish;
    end
endmodule
"""


def emit_gls_reset_tb(cfg: FabricConfig = FabricConfig()) -> str:
    """Reset testbench, top-level ports only.

    RESET_AT == 0 : clean reset, then one inference.
    RESET_AT  > 0 : start an inference, drive RESET_AT activations, assert reset
                    mid-inference, check the observable outputs go idle, then
                    run a full fresh inference of the SAME image.  The result
                    must equal the golden model, i.e. no stale state survived.
    """
    w = derive_widths(cfg)
    return f"""// TEST-ONLY Stage-4 gate-level reset testbench.  Never synthesized.
`timescale 1ns/1ps

module tb_reset;
    parameter RESET_AT = 0;

    localparam N_IN     = {cfg.n_in};
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

    reg [ACT_BITS-1:0] img [0:N_IN-1];
    reg [31:0] cyc;
    always @(posedge clk) cyc <= cyc + 32'd1;
    integer fh_out, q, pix, guard, t0, t1, errors;

    initial begin
        cyc = 32'd0; errors = 0;
        rst = 1'b1; start = 1'b0; in_valid = 1'b0;
        in_data = {{ACT_BITS{{1'b0}}}};
        $readmemh("img.hex", img);
        fh_out = $fopen("reset_out.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        if (RESET_AT > 0) begin
            // ---- partial inference, then reset mid-flight ------------------
            @(negedge clk); start = 1'b1;
            @(negedge clk); start = 1'b0;
            pix = 0;
            while (pix < RESET_AT) begin
                if (in_ready) begin
                    in_valid = 1'b1; in_data = img[pix]; pix = pix + 1;
                end else in_valid = 1'b0;
                @(negedge clk);
            end
            in_valid = 1'b0;
            rst = 1'b1;
            @(negedge clk);
            @(negedge clk);
            // observable state must be idle while reset is held
            if (busy !== 1'b0)             begin $display("RESET: busy high"); errors = errors + 1; end
            if (done !== 1'b0)             begin $display("RESET: done high"); errors = errors + 1; end
            if (prediction_valid !== 1'b0) begin $display("RESET: prediction_valid high"); errors = errors + 1; end
            rst = 1'b0;
            @(negedge clk);
            if (busy !== 1'b0)             begin $display("POST-RESET: busy high"); errors = errors + 1; end
            if (done !== 1'b0)             begin $display("POST-RESET: done high"); errors = errors + 1; end
            if (prediction_valid !== 1'b0) begin $display("POST-RESET: prediction_valid high"); errors = errors + 1; end
        end else begin
            if (busy !== 1'b0)             begin $display("CLEAN: busy high"); errors = errors + 1; end
            if (done !== 1'b0)             begin $display("CLEAN: done high"); errors = errors + 1; end
            if (prediction_valid !== 1'b0) begin $display("CLEAN: prediction_valid high"); errors = errors + 1; end
        end

        // ---- one full inference after the reset ---------------------------
        @(negedge clk); start = 1'b1; t0 = cyc;
        @(negedge clk); start = 1'b0;
        pix = 0;
        while (pix < N_IN) begin
            if (in_ready) begin
                in_valid = 1'b1; in_data = img[pix]; pix = pix + 1;
            end else in_valid = 1'b0;
            @(negedge clk);
        end
        in_valid = 1'b0;
        guard = 0;
        while (!done && (guard < TIMEOUT)) begin
            @(negedge clk); guard = guard + 1;
        end
        if (!done) begin
            $display("RESET TB TIMEOUT"); errors = errors + 1;
        end else begin
            t1 = cyc;
            $fwrite(fh_out, "0 %0d %0d", t1 - t0 + 1, prediction);
            for (q = 0; q < N_OUT; q = q + 1)
                $fwrite(fh_out, " %0d", $signed(logits[q*ACC2 +: ACC2]));
            $fdisplay(fh_out, "");
        end
        $fclose(fh_out);
        if (errors != 0) $display("TB ERRORS: %0d", errors);
        else             $display("TB OK");
        $finish;
    end
endmodule
"""


# --------------------------------------------------------------------------
# The GLS source-list guard
# --------------------------------------------------------------------------

def check_gls_sources(sources: Sequence[str], netlist: str,
                      simlib: str, root: str) -> Dict[str, object]:
    """Prove the simulation compiles the SYNTHESIZED netlist and nothing that
    contains a behavioural implementation of the design.  Raises on violation.
    """
    abs_sources = [os.path.abspath(s) for s in sources]
    abs_root_rtl = os.path.abspath(os.path.join(root, "rtl"))
    stage4_dir = os.path.abspath(os.path.join(root, "build", "stage4"))

    if os.path.abspath(netlist) not in abs_sources:
        raise Stage4Error("synthesized netlist %s is not in the source list"
                          % netlist)
    if not os.path.abspath(netlist).startswith(stage4_dir):
        raise Stage4Error("netlist %s is not under build/stage4" % netlist)
    if os.path.abspath(simlib) not in abs_sources:
        raise Stage4Error("cell simulation library %s is not in the source list"
                          % simlib)

    for s in abs_sources:
        if os.path.dirname(s) == abs_root_rtl:
            raise Stage4Error(
                "gate-level simulation source list contains production RTL: %s"
                % s)
        if os.path.basename(s) in FORBIDDEN_IN_GLS:
            raise Stage4Error(
                "gate-level simulation source list contains a behavioural "
                "implementation file: %s" % s)

    # Every module the simulation defines must come from the netlist, the
    # testbench, or the official cell library -- nothing else.
    defined: Dict[str, str] = {}
    for s in abs_sources:
        for m in netlist_modules(s):
            if m in defined:
                raise Stage4Error("module %s defined twice: %s and %s"
                                  % (m, defined[m], s))
            defined[m] = s
    if TOP not in defined:
        raise Stage4Error("%s is not defined by any simulation source" % TOP)
    if defined[TOP] != os.path.abspath(netlist):
        raise Stage4Error("%s comes from %s, not from the synthesized netlist"
                          % (TOP, defined[TOP]))

    return {
        "sources": [os.path.relpath(s, root) if s.startswith(os.path.abspath(root))
                    else s for s in abs_sources],
        "top_defined_by": os.path.relpath(os.path.abspath(netlist), root),
        "production_rtl_in_source_list": False,
        "behavioural_implementation_in_source_list": False,
        "duplicate_module_definitions": 0,
    }


# --------------------------------------------------------------------------
# Gate-level simulation driver
# --------------------------------------------------------------------------

def _write_images(workdir: str, x: np.ndarray) -> None:
    with open(os.path.join(workdir, "img.hex"), "w") as fh:
        fh.write("\n".join("%02x" % v for v in np.asarray(x).ravel()) + "\n")


def _parse_out(path: str, n_out: int):
    cycles, preds, logits = [], [], []
    with open(path) as fh:
        for line in fh:
            f = line.split()
            if not f:
                continue
            cycles.append(int(f[1]))
            preds.append(int(f[2]))
            logits.append([int(v) for v in f[3:3 + n_out]])
    return cycles, np.array(preds, dtype=np.int64), np.array(logits,
                                                             dtype=np.int64)


@dataclass
class GlsRun:
    kind: str
    workdir: str
    guard: Dict[str, object]
    compile_seconds: float
    sim_seconds: float
    tb_ok: bool
    stdout: str
    cycles: List[int]
    predictions: np.ndarray
    logits: np.ndarray


def run_gls(root: str, workdir: str, kind: str, netlist: str, simlib: str,
            x: np.ndarray, stall_mode: int = 0, stall_n: int = 7,
            cfg: FabricConfig = FabricConfig(),
            sim_timeout: int = 21600) -> GlsRun:
    import time
    os.makedirs(workdir, exist_ok=True)
    tb_path = os.path.join(workdir, "tb_gls.v")
    with open(tb_path, "w") as fh:
        fh.write(emit_gls_tb(cfg))
    _write_images(workdir, x)

    sources = [tb_path, netlist, simlib]
    guard = check_gls_sources(sources, netlist, simlib, root)

    n = int(np.asarray(x).shape[0])
    out = os.path.join(workdir, "sim.vvp")
    cmd = [find_tool("iverilog"), "-g2012", "-o", out,
           "-Ptb.NIMG=%d" % n, "-Ptb.STALL_MODE=%d" % stall_mode,
           "-Ptb.STALL_N=%d" % stall_n, "-s", "tb"] + sources
    t0 = time.time()
    r = _run(cmd, cwd=workdir)
    ct = time.time() - t0
    if r.returncode != 0:
        raise Stage4Error("gate-level compile failed (%s):\n%s"
                          % (kind, r.stdout + r.stderr))
    t0 = time.time()
    r = _run([find_tool("vvp"), out], cwd=workdir, timeout=sim_timeout)
    st = time.time() - t0
    if r.returncode != 0:
        raise Stage4Error("gate-level simulation failed (%s):\n%s"
                          % (kind, r.stdout + r.stderr))
    cycles, preds, logits = _parse_out(os.path.join(workdir, "out.txt"),
                                       cfg.n_out)
    return GlsRun(kind=kind, workdir=workdir, guard=guard, compile_seconds=ct,
                  sim_seconds=st, tb_ok=("TB OK" in r.stdout), stdout=r.stdout,
                  cycles=cycles, predictions=preds, logits=logits)


def run_gls_reset(root: str, workdir: str, kind: str, netlist: str, simlib: str,
                  x_one: np.ndarray, reset_at: int,
                  cfg: FabricConfig = FabricConfig()) -> GlsRun:
    import time
    os.makedirs(workdir, exist_ok=True)
    tb_path = os.path.join(workdir, "tb_gls_reset.v")
    with open(tb_path, "w") as fh:
        fh.write(emit_gls_reset_tb(cfg))
    _write_images(workdir, x_one)

    sources = [tb_path, netlist, simlib]
    guard = check_gls_sources(sources, netlist, simlib, root)

    out = os.path.join(workdir, "sim_reset.vvp")
    cmd = [find_tool("iverilog"), "-g2012", "-o", out,
           "-Ptb_reset.RESET_AT=%d" % reset_at, "-s", "tb_reset"] + sources
    t0 = time.time()
    r = _run(cmd, cwd=workdir)
    ct = time.time() - t0
    if r.returncode != 0:
        raise Stage4Error("reset compile failed (%s):\n%s"
                          % (kind, r.stdout + r.stderr))
    t0 = time.time()
    r = _run([find_tool("vvp"), out], cwd=workdir)
    st = time.time() - t0
    if r.returncode != 0:
        raise Stage4Error("reset simulation failed (%s):\n%s"
                          % (kind, r.stdout + r.stderr))
    cycles, preds, logits = _parse_out(os.path.join(workdir, "reset_out.txt"),
                                       cfg.n_out)
    return GlsRun(kind=kind, workdir=workdir, guard=guard, compile_seconds=ct,
                  sim_seconds=st, tb_ok=("TB OK" in r.stdout), stdout=r.stdout,
                  cycles=cycles, predictions=preds, logits=logits)


# --------------------------------------------------------------------------
# Resource categorisation
# --------------------------------------------------------------------------

FPGA_CATEGORIES = {
    "lut": ("SB_LUT4",),
    "ff": ("SB_DFF", "SB_DFFE", "SB_DFFESR", "SB_DFFSR", "SB_DFFR", "SB_DFFS",
           "SB_DFFSS", "SB_DFFN", "SB_DFFNE", "SB_DFFNESR", "SB_DFFNSR",
           "SB_DFFES", "SB_DFFER", "SB_DFFSE"),
    "carry": ("SB_CARRY",),
    "ram": ("SB_RAM40_4K", "SB_RAM40_4KNR", "SB_RAM40_4KNW", "SB_RAM40_4KNRNW",
            "SB_SPRAM256KA"),
    "dsp": ("SB_MAC16",),
}

GENERIC_CATEGORIES = {
    "sequential": ("$_DFF_P_", "$_DFF_N_", "$_DFFE_PP_", "$_SDFF_PP0_",
                   "$_DLATCH_P_", "$_DLATCH_N_"),
    "mux": ("$_MUX_", "$_NMUX_", "$_MUX4_", "$_MUX8_", "$_MUX16_"),
    "and": ("$_AND_", "$_NAND_", "$_ANDNOT_"),
    "or": ("$_OR_", "$_NOR_", "$_ORNOT_"),
    "xor": ("$_XOR_", "$_XNOR_"),
    "not": ("$_NOT_", "$_BUF_"),
    "aoi_oai": ("$_AOI3_", "$_OAI3_", "$_AOI4_", "$_OAI4_"),
}

LATCH_TYPES = ("$_DLATCH_P_", "$_DLATCH_N_", "$_DLATCHSR_PPP_", "SB_LATCH")
ARITH_TYPES = ("$mul", "$add", "$sub", "$alu", "$macc", "$div", "$mod",
               "SB_MAC16")


def categorise(cells: Dict[str, int], table: Dict[str, Tuple[str, ...]]
               ) -> Dict[str, object]:
    real = {k: v for k, v in cells.items() if k != "$scopeinfo"}
    out: Dict[str, object] = {}
    claimed = set()
    for cat, types in table.items():
        n = sum(real.get(t, 0) for t in types)
        out[cat] = n
        claimed.update(t for t in types if t in real)
    out["other"] = sum(v for k, v in real.items() if k not in claimed)
    out["other_types"] = sorted(k for k in real if k not in claimed)
    out["total_cells"] = sum(real.values())
    out["latches"] = sum(real.get(t, 0) for t in LATCH_TYPES)
    out["arithmetic_or_multiplier_cells"] = sum(real.get(t, 0)
                                                for t in ARITH_TYPES)
    return out


# --------------------------------------------------------------------------
# Constant-multiply analysis
#
# The Stage-1 source contains exactly 16 `*` operators:
#     prod_k = $signed({4'b0000, act_pipe}) * ALPHA_k,   ALPHA_k = k - 8
# One operand is always a fixed alphabet level, so synthesis is free to replace
# every one of them.  This walks the synthesized netlists and reports what it
# actually did, instead of assuming.
# --------------------------------------------------------------------------

BANK_NET = "u_fabric.L1_SELECT[0].u_sel.bank"
ACT_NET = "u_fabric.act_pipe"
FABRIC_BANK_NET = "L1_SELECT[0].u_sel.bank"
FABRIC_ACT_NET = "act_pipe"
_SEQ_MARKERS = ("DFF", "SDFF", "ADFF", "DLATCH", "RAM", "LATCH")


def _load_module(json_path: str, top: str = TOP) -> Dict[str, object]:
    import json
    with open(json_path) as fh:
        return json.load(fh)["modules"][top]


def _is_seq(cell_type: str) -> bool:
    t = cell_type.upper()
    return any(m in t for m in _SEQ_MARKERS)


def analyze_product_bank(json_path: str, netlist_v: str,
                         cfg: FabricConfig = FabricConfig(),
                         top: str = TOP) -> Dict[str, object]:
    """What did synthesis actually do to the 16 constant multiplications?

    Answered from the netlists, not assumed.  Two independent views:

    1.  Bit-level classification of the 192-bit product bank.  A bit that is a
        literal constant or a plain alias of the activation register costs zero
        logic; a bit with no driver left in the netlist means the product was
        never materialised as a signal at all -- synthesis fused constant
        multiplication into the downstream 16:1 selection.
    2.  For the FPGA netlist, where the `prod_NN` names survive, the actual
        right-hand side each product wire was reduced to.
    """
    mod = _load_module(json_path, top)
    nets, cells = mod["netnames"], mod["cells"]
    bank_net = BANK_NET if BANK_NET in nets else FABRIC_BANK_NET
    act_net = ACT_NET if BANK_NET in nets else FABRIC_ACT_NET
    if bank_net not in nets:
        raise Stage4Error("product-bank net not present in %s" % json_path)
    bank = nets[bank_net]["bits"]
    prod_bits = derive_widths(cfg)["product_bits"]

    driver: Dict[int, str] = {}
    for name, c in cells.items():
        for port, bits in c["connections"].items():
            if c.get("port_directions", {}).get(port) == "output":
                for b in bits:
                    if isinstance(b, int):
                        driver[b] = c["type"]

    # The activation register: named in the FPGA netlist, anonymous after the
    # generic flow's flatten+abc, so fall back to "driven by a flip-flop".
    act = {b for b in nets.get(act_net, {"bits": []})["bits"]
           if isinstance(b, int)}

    def classify(b) -> str:
        if not isinstance(b, int):
            return "constant"
        if b in act:
            return "activation_register_alias"
        t = driver.get(b)
        if t is None:
            return "no_driver_fused_downstream"
        if _is_seq(t):
            return "activation_register_alias"
        return "combinational_cell:" + t

    per_product = []
    totals: Dict[str, int] = {}
    for k in range(cfg.k):
        bits = bank[k * prod_bits:(k + 1) * prod_bits]
        kinds: Dict[str, int] = {}
        for b in bits:
            c = classify(b)
            kinds[c] = kinds.get(c, 0) + 1
            totals[c] = totals.get(c, 0) + 1
        zero_cost = (kinds.get("constant", 0)
                     + kinds.get("activation_register_alias", 0))
        per_product.append({
            "k": k,
            "alphabet_level": int(cfg.alphabet[k]),
            "bit_classes": kinds,
            "zero_logic_bits": zero_cost,
            "of_bits": prod_bits,
        })

    rhs = {}
    if os.path.isfile(netlist_v):
        text = open(netlist_v).read()
        for m in re.finditer(r"assign \\u_fabric\.prod_(\d\d)\s*=\s*(.+?);",
                             text):
            rhs["prod_%s" % m.group(1)] = re.sub(r"\s+", " ",
                                                m.group(2)).strip()

    return {
        "bank_net": bank_net,
        "bank_width_bits": len(bank),
        "product_width_bits": prod_bits,
        "source_multiply_operators": cfg.k,
        "bit_class_totals": totals,
        "zero_logic_bits": (totals.get("constant", 0)
                            + totals.get("activation_register_alias", 0)),
        "multiplier_or_dsp_cells_in_netlist": sum(
            n for t, n in _cell_counts(mod).items()
            if t in ARITH_TYPES or "MAC" in t.upper()),
        "product_wire_drivers": rhs,
        "per_product": per_product,
    }


def _cell_counts(mod) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for c in mod["cells"].values():
        out[c["type"]] = out.get(c["type"], 0) + 1
    return out


def fabric_only_script(root: str, kind: str, netlist: str,
                       json_out: str) -> str:
    """DIAGNOSTIC ONLY.  Synthesizes rtl/mnist_mlp_fabric.v by itself so the
    cost of the MSA compute datapath can be separated from the cost of the
    parameter ROM.  Not part of the portability claim and never simulated."""
    src = os.path.join(root, "rtl/mnist_mlp_fabric.v")
    if kind == "fpga":
        body = ["read_verilog -defer " + src,
                "synth_ice40 -top mnist_mlp_fabric",
                "check -assert", "stat",
                "write_json %s" % json_out,
                "write_verilog -noattr -noexpr %s" % netlist, ""]
    else:
        body = ["read_verilog " + src,
                "hierarchy -check -top mnist_mlp_fabric",
                "proc", "flatten", "opt -full", "memory", "opt -full",
                "techmap", "opt -full", "simplemap",
                "dfflegalize -cell $_DFF_P_ 01", "abc -g simple",
                "setundef -zero", "opt_clean -purge", "check -assert", "stat",
                "write_json %s" % json_out,
                "write_verilog -noattr -noexpr %s" % netlist, ""]
    return "\n".join(body)
