"""Simulation and lint drivers for the Stage-1 fabric.

Everything here is verification infrastructure.  It writes the model
parameters into hex files that a TEST-ONLY testbench loads, so the fabric is
exercised long before a real ROM backend exists (Stage 2).

Tool discovery is explicit and fails closed: if Icarus or Yosys is missing the
caller is told, never silently skipped into a weaker check.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np

from .fabric import (FabricConfig, derive_widths, pack_weight_words,
                     to_twos_complement)
from .verilog_emit import emit_fabric_verilog, emit_testbench_verilog

#: Extra locations searched for the EDA tools, on top of PATH.
_EXTRA_TOOL_DIRS = [
    os.path.expanduser("~/klayout_cf/iverilog/bin"),
    os.path.expanduser("~/klayout_cf/yosys/bin"),
]


class ToolMissing(RuntimeError):
    pass


def find_tool(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    for d in _EXTRA_TOOL_DIRS:
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    raise ToolMissing("%s not found on PATH or in %s" % (name, _EXTRA_TOOL_DIRS))


def have_tool(name: str) -> bool:
    try:
        find_tool(name)
        return True
    except ToolMissing:
        return False


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def _run(cmd: Sequence[str], cwd: str | None = None,
         timeout: int = 1800) -> RunResult:
    p = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True,
                       timeout=timeout)
    return RunResult(p.returncode, p.stdout, p.stderr)


# --------------------------------------------------------------------------
# Yosys
# --------------------------------------------------------------------------

def yosys_check(verilog_path: str, top: str) -> Dict[str, object]:
    """read_verilog / hierarchy -check / proc / check -assert / stat.

    Returns the parsed cell counts and the raw log.  A clean exit code is not
    trusted on its own: the log is scanned for the failure strings Yosys emits
    for undriven signals, multiple drivers and inferred latches.
    """
    yosys = find_tool("yosys")
    script = ("read_verilog -defer %s; "
              "hierarchy -check -top %s; "
              "proc; "
              "check -assert; "
              "stat" % (verilog_path, top))
    r = _run([yosys, "-p", script])
    log = r.output

    # Yosys prints one stat section per module and a final
    # "=== design hierarchy ===" section with the counts including submodules.
    # Reset on every section header so the final (whole-design) counts win.
    cells: Dict[str, int] = {}
    in_counts = False
    for line in log.splitlines():
        if line.startswith("==="):
            cells = {}
            in_counts = False
            continue
        s = line.strip()
        m = re.match(r"^(\d+)\s+(cells|submodules)$", s)
        if m:
            in_counts = True
            continue
        if in_counts:
            m2 = re.match(r"^(\d+)\s+(\$?[A-Za-z_][A-Za-z0-9_$]*)$", s)
            if m2:
                cells[m2.group(2)] = int(m2.group(1))
            elif s:
                in_counts = False

    problems = []
    m = re.search(r"Found and reported (\d+) problems", log)
    if m and int(m.group(1)) > 0:
        problems.append(m.group(0))
    for marker in ("multiple conflicting drivers", "is used but has no driver",
                   "ERROR:"):
        if marker in log:
            problems.append(marker)
    latch_lines = [l for l in log.splitlines()
                   if "latch" in l.lower() and "No latch inferred" not in l
                   and "PROC_DLATCH" not in l]
    return {
        "returncode": r.returncode,
        "log": log,
        "cells": cells,
        "problem_markers": problems,
        "latch_lines": latch_lines,
        "ok": (r.returncode == 0 and not problems and not latch_lines),
    }


# --------------------------------------------------------------------------
# Icarus
# --------------------------------------------------------------------------

def iverilog_compile(sources: List[str], out: str, cwd: str,
                     std: str = "2001", defines: Dict[str, str] | None = None,
                     top_params: Dict[str, int] | None = None) -> RunResult:
    iverilog = find_tool("iverilog")
    cmd = [iverilog, "-g%s" % std, "-Wall", "-o", out]
    for k, v in (top_params or {}).items():
        cmd += ["-P%s" % k if v is None else "-P%s=%d" % (k, v)]
    cmd += sources
    return _run(cmd, cwd=cwd)


# --------------------------------------------------------------------------
# Model-parameter hex files (TEST-ONLY stimulus, not a ROM backend)
# --------------------------------------------------------------------------

def write_hex_words(path: str, words: Sequence[int], bits: int) -> None:
    digits = (bits + 3) // 4
    with open(path, "w") as fh:
        for wd in words:
            if wd >> bits:
                raise ValueError("value does not fit %d bits" % bits)
            fh.write("%0*x\n" % (digits, wd))


def write_parameter_files(d: str, cfg: FabricConfig, i1: np.ndarray,
                          b1: np.ndarray, i2: np.ndarray, b2: np.ndarray,
                          images: np.ndarray) -> None:
    w = derive_widths(cfg)
    write_hex_words(os.path.join(d, "w1.hex"),
                    pack_weight_words(i1, cfg), w["weight_word_bits"])
    write_hex_words(os.path.join(d, "w2.hex"),
                    pack_weight_words(i2, cfg), w["weight_word_bits"])
    bdw = w["bias_data_bits"]

    def encode(values, layer_bits):
        out = []
        for v in values:
            # fail closed if the trained bias does not fit its architectural
            # width, then sign extend onto the shared bias bus
            to_twos_complement(int(v), layer_bits)
            out.append(to_twos_complement(int(v), bdw))
        return out

    write_hex_words(os.path.join(d, "b1.hex"),
                    encode(b1, w["layer1_bias_bits"]), bdw)
    write_hex_words(os.path.join(d, "b2.hex"),
                    encode(b2, w["layer2_bias_bits"]), bdw)
    imgs = np.asarray(images, dtype=np.int64)
    if imgs.ndim == 1:
        imgs = imgs[None, :]
    write_hex_words(os.path.join(d, "img.hex"),
                    [int(v) for v in imgs.ravel()], cfg.act_bits)


# --------------------------------------------------------------------------
# Full simulation
# --------------------------------------------------------------------------

@dataclass
class SimOutput:
    cycles: List[int]
    predictions: List[int]
    logits: np.ndarray          # (n_images, n_out)
    hidden: np.ndarray          # (n_images, n_hidden)
    acc1: np.ndarray            # (n_images, n_hidden) layer-1 dot products
    log: str
    compile_log: str


def simulate(workdir: str, cfg: FabricConfig, i1: np.ndarray, b1: np.ndarray,
             i2: np.ndarray, b2: np.ndarray, images: np.ndarray,
             fabric_path: str | None = None, stall: int = 0) -> SimOutput:
    """Run the fabric on `images` through Icarus and return everything it saw."""
    os.makedirs(workdir, exist_ok=True)
    imgs = np.asarray(images, dtype=np.int64)
    if imgs.ndim == 1:
        imgs = imgs[None, :]
    n_img = imgs.shape[0]

    fab = os.path.join(workdir, cfg.module_name + ".v")
    if fabric_path is None:
        with open(fab, "w") as fh:
            fh.write(emit_fabric_verilog(cfg))
    elif os.path.abspath(fabric_path) != os.path.abspath(fab):
        shutil.copyfile(fabric_path, fab)
    tb = os.path.join(workdir, "tb.v")
    with open(tb, "w") as fh:
        fh.write(emit_testbench_verilog(cfg))

    write_parameter_files(workdir, cfg, i1, b1, i2, b2, imgs)

    exe = os.path.join(workdir, "sim.vvp")
    # the production fabric is compiled in strict Verilog-2001 mode
    c = iverilog_compile([fab, tb], exe, workdir, std="2001",
                         top_params={"tb.NIMG": n_img, "tb.STALL": stall})
    if c.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + c.output)

    vvp = find_tool("vvp")
    r = _run([vvp, exe], cwd=workdir)
    if r.returncode != 0 or "TB ERRORS" in r.output:
        raise RuntimeError("simulation failed:\n" + r.output)

    cycles, preds, logits = [], [], []
    with open(os.path.join(workdir, "out.txt")) as fh:
        for line in fh:
            f = line.split()
            if len(f) < 3 + cfg.n_out:
                raise RuntimeError("bad simulator output line: %r" % line)
            cycles.append(int(f[1]))
            preds.append(int(f[2]))
            logits.append([int(v) for v in f[3:3 + cfg.n_out]])

    def _load(name: str, n_col: int) -> np.ndarray:
        rows = []
        with open(os.path.join(workdir, name)) as fh:
            for line in fh:
                f = line.split()
                rows.append([int(v) for v in f[1:1 + n_col]])
        return np.array(rows, dtype=np.int64)

    return SimOutput(
        cycles=cycles,
        predictions=preds,
        logits=np.array(logits, dtype=np.int64),
        hidden=_load("hidden.txt", cfg.n_hidden),
        acc1=_load("acc1.txt", cfg.n_hidden),
        log=r.output,
        compile_log=c.output,
    )
