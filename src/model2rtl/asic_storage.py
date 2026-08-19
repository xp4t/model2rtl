"""Stage 5: map PORTABLE parameter storage to SKY130 standard cells.

Stage 4 measured the portable ROM on an FPGA (32 block RAMs) and in the Yosys
generic gate vocabulary (~20 200 gates).  Neither is comparable to a hard ROM
macro.  This module produces the fairer ASIC-oriented number: the same portable
Verilog mapped with Yosys + ABC onto the real SKY130 high-density standard-cell
liberty, reporting the library's own cell areas.

No place and route is run.  The result is a standard-cell AREA ESTIMATE -- the
sum of the liberty cell areas -- which is not the same quantity as a hard
macro's GDS bounding box.  Every caller is required to carry that caveat.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from typing import Dict, List, Optional, Sequence

from .sim import find_tool, _run

PDK_ROOT = "/home/rithwik/pdk"
LIBERTY = os.path.join(
    PDK_ROOT, "sky130A", "libs.ref", "sky130_fd_sc_hd", "lib",
    "sky130_fd_sc_hd__tt_025C_1v80.lib")
LIBERTY_CORNER = "sky130_fd_sc_hd, tt, 25 C, 1.80 V"


class AsicStorageError(RuntimeError):
    pass


def liberty_available() -> bool:
    return os.path.isfile(LIBERTY)


_SEQ_CACHE: Dict[str, frozenset] = {}


def sequential_cell_names(liberty: str = LIBERTY) -> frozenset:
    """Cells the LIBERTY ITSELF declares sequential (an ff or latch group).

    Guessing from the cell name is unreliable -- sky130 has combinational delay
    cells whose names contain "dl", and sequential cells such as edfxtp whose
    names do not start with "df".
    """
    if liberty in _SEQ_CACHE:
        return _SEQ_CACHE[liberty]
    seq, cur, depth, cell_depth = set(), None, 0, None
    cell_re = re.compile(r"^\s*cell\s*\(\s*\"?([\w$]+)\"?\s*\)")
    seq_re = re.compile(r"^\s*(ff|ff_bank|latch|latch_bank)\s*\(")
    with open(liberty) as fh:
        for line in fh:
            m = cell_re.match(line)
            if m and depth <= 1:
                cur, cell_depth = m.group(1), depth
            if cur is not None and seq_re.match(line):
                seq.add(cur)
            depth += line.count("{") - line.count("}")
            if cur is not None and depth <= cell_depth:
                cur = None
    _SEQ_CACHE[liberty] = frozenset(seq)
    return _SEQ_CACHE[liberty]


# --------------------------------------------------------------------------
# A portable case-ROM in exactly the project's storage style
# --------------------------------------------------------------------------

def emit_case_rom(module: str, depth: int, width: int,
                  rows: Sequence[int]) -> str:
    """Same construction as rtl/mnist_mlp_params_portable.v: a registered,
    enable-gated case over the address.  No $readmemh, no initial block, no
    vendor primitive -- so what is measured is the same kind of storage."""
    abits = max(1, (depth - 1).bit_length())
    digits = (width + 3) // 4
    arms = "\n".join("            %d'd%d: dout <= %d'h%0*x;"
                     % (abits, a, width, digits, v)
                     for a, v in enumerate(rows))
    return f"""// GENERATED for the Stage-5 storage sweep. Portable Verilog-2001.
`default_nettype none

module {module} (
    input  wire                 clk,
    input  wire                 en,
    input  wire [{abits - 1}:0]{' ' * max(0, 12 - len(str(abits - 1)))}addr,
    output reg  [{width - 1}:0]{' ' * max(0, 12 - len(str(width - 1)))}dout
);
    always @(posedge clk) begin
        if (en) begin
            case (addr)
{arms}
                default: dout <= {{{width}{{1'b0}}}};
            endcase
        end
    end
endmodule

`default_nettype wire
"""


def deterministic_rows(depth: int, width: int, seed: int = 1234) -> List[int]:
    """Reproducible pseudo-random contents for a sweep point.

    A ROM's mapped area depends on its contents, so the sweep must not use
    all-zero or all-one data.  This is a fixed 64-bit LCG: the same depth,
    width and seed always give the same image, on any machine.
    """
    mask = (1 << width) - 1
    state = (seed * 2862933555777941757 + 3037000493) & ((1 << 64) - 1)
    out = []
    for _ in range(depth):
        v = 0
        got = 0
        while got < width:
            state = (state * 6364136223846793005 + 1442695040888963407) \
                & ((1 << 64) - 1)
            v = (v << 32) | ((state >> 16) & 0xFFFFFFFF)
            got += 32
        out.append(v & mask)
    return out


# --------------------------------------------------------------------------
# Yosys + ABC against the real liberty
# --------------------------------------------------------------------------

_AREA = re.compile(r"Chip area for (?:top )?module '?\\?(\S+?)'?:\s+([\d.]+)")
#: Yosys prints the exact sequential share right under the chip area.  The
#: per-cell-type areas in the stat table are display values -- some are printed
#: in 3-significant-digit scientific notation -- so they must NEVER be summed
#: to produce a reported number.
_SEQ_AREA = re.compile(
    r"of which used for sequential elements:\s+([\d.]+)")
#: `stat -liberty` prints "count area cellname"; without a liberty it prints
#: "count cellname".  Accept both.
_STAT_ROW = re.compile(r"^\s+(\d+)\s+([\d.E+-]+)?\s*(\S+)\s*$")


def synth_script(sources: Sequence[str], top: str, netlist: str,
                 liberty: str = LIBERTY) -> str:
    # read_liberty -lib first: without the cell interfaces Yosys's `check`
    # cannot see that a mapped flip-flop drives an output port and reports
    # false "no driver" problems, and blackbox detection is meaningless.
    return "\n".join(
        ["read_liberty -lib %s" % liberty]
        + ["read_verilog " + s for s in sources] + [
            "hierarchy -check -top %s" % top,
            "proc",
            "flatten",
            "opt -full",
            "memory",
            "opt -full",
            "techmap",
            "opt -full",
            # lower anything techmap/opt left coarse (wide $mux in particular)
            # so nothing survives ABC unmapped
            "simplemap",
            "dfflibmap -liberty %s" % liberty,
            "abc -liberty %s" % liberty,
            "setundef -zero",
            "opt_clean -purge",
            "check -assert",
            "stat -liberty %s" % liberty,
            "write_verilog -noattr -noexpr %s" % netlist,
            "",
        ])


def _parse(log_text: str, top: str) -> Dict[str, object]:
    """Cell counts AND per-cell liberty areas from the `stat -liberty` block."""
    cells: Dict[str, int] = {}
    areas: Dict[str, float] = {}
    in_top = False
    for line in log_text.splitlines():
        m = re.match(r"^=== (\S+) ===", line)
        if m:
            in_top = (m.group(1).lstrip("\\") == top)
            if in_top:
                cells, areas = {}, {}
            continue
        if not in_top:
            continue
        m = _STAT_ROW.match(line)
        if not m:
            continue
        name = m.group(3)
        if name in ("wires", "wire", "bits", "ports", "cells", "memories",
                    "processes", "submodules"):
            continue
        if not (name.startswith("sky130_") or name.startswith("$")):
            continue
        cells[name] = int(m.group(1))
        if m.group(2):
            try:
                areas[name] = float(m.group(2))
            except ValueError:
                pass
    area = seq_area = None
    m = _AREA.search(log_text)
    if m:
        area = float(m.group(2))
    m = _SEQ_AREA.search(log_text)
    if m:
        seq_area = float(m.group(1))
    return {"cells": cells, "cell_areas_display_only": areas,
            "chip_area_um2": area, "sequential_area_um2": seq_area}


def map_to_sky130(sources: Sequence[str], top: str, outdir: str,
                  liberty: str = LIBERTY, timeout: int = 7200
                  ) -> Dict[str, object]:
    """Map a design onto SKY130 standard cells and report measured cell area."""
    if not os.path.isfile(liberty):
        raise AsicStorageError("SKY130 liberty not found: %s" % liberty)
    os.makedirs(outdir, exist_ok=True)
    netlist = os.path.join(outdir, "%s_sky130.v" % top)
    script = synth_script(sources, top, netlist, liberty)
    script_path = os.path.join(outdir, "%s_sky130.ys" % top)
    with open(script_path, "w") as fh:
        fh.write(script)
    log_path = os.path.join(outdir, "%s_sky130.log" % top)
    t0 = time.time()
    r = _run([find_tool("yosys"), "-l", log_path, script_path], cwd=outdir,
             timeout=timeout)
    elapsed = time.time() - t0
    log_text = open(log_path).read() if os.path.isfile(log_path) else r.stdout

    parsed = _parse(log_text, top)
    cells = parsed["cells"]
    areas = parsed["cell_areas_display_only"]
    total_area = parsed["chip_area_um2"]
    seq_area = parsed["sequential_area_um2"]
    comb_area = (None if (total_area is None or seq_area is None)
                 else round(total_area - seq_area, 6))
    unmapped = {k: v for k, v in cells.items() if not k.startswith("sky130_")}
    seq_names = sequential_cell_names(liberty)
    seq = {k: v for k, v in cells.items()
           if k.startswith("sky130_") and k in seq_names}
    comb = {k: v for k, v in cells.items()
            if k.startswith("sky130_") and k not in seq}
    errors = [l for l in log_text.splitlines() if l.startswith("ERROR")]
    return {
        "top": top,
        "sources": [os.path.basename(s) for s in sources],
        "liberty": liberty,
        "liberty_corner": LIBERTY_CORNER,
        "script": script,
        "script_path": script_path,
        "log": log_path,
        "netlist": netlist,
        "exit_status": r.returncode,
        "seconds": round(elapsed, 1),
        "cells": cells,
        "total_cells": sum(cells.values()),
        "sequential_cells": sum(seq.values()),
        "combinational_cells": sum(comb.values()),
        "sequential_area_um2": seq_area,
        "combinational_area_um2": comb_area,
        "cell_areas_display_only_um2": areas,
        "cell_area_note": "Per-cell-type areas in the Yosys stat table are "
                          "DISPLAY values (some printed in 3-significant-digit "
                          "scientific notation) and are not summed. The "
                          "reported total and sequential areas are the exact "
                          "figures Yosys prints, and the combinational area is "
                          "their difference.",
        "unmapped_cells": unmapped,
        "blackboxes": sorted(unmapped),
        "chip_area_um2": total_area,
        "area_source": ("Yosys `stat -liberty`: the sum of the liberty cell "
                        "areas of the mapped cells. This is a standard-cell "
                        "AREA ESTIMATE and excludes placement utilisation and "
                        "routing overhead; it is NOT a placed block area and "
                        "not directly comparable to a hard macro's GDS "
                        "bounding box."),
        "errors": errors,
        "ok": (r.returncode == 0 and not errors and not unmapped
               and total_area is not None and seq_area is not None),
    }
