#!/usr/bin/env python3
"""Stage 5: the storage-size crossover sweep.

At each measured point the SAME deterministic contents are stored two ways and
both are measured, never estimated:

  A. an OpenROM hard macro          -> GDS bounding box, measured with KLayout
  B. the portable case ROM          -> SKY130 standard cells, liberty cell area

The two numbers are different KINDS of area and the report says so; the sweep's
purpose is to locate the interval in which their ORDER changes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import asic_storage as A                         # noqa: E402
from model2rtl import openrom as O                              # noqa: E402

BUILD = os.path.join(ROOT, "build", "stage5", "sweep")
RECORD = os.path.join(ROOT, "build", "stage5", "stage5_sweep.json")

#: Byte-aligned widths only, so the sweep introduces no further physical
#: transformation.  32 bits is the layer-1 bank width, so the deepest point is
#: the real bank shape.
DEFAULT_POINTS = ((32, 32), (64, 32), (128, 32), (256, 32), (512, 32),
                  (784, 32))
WPR_LADDER = (4, 8, 2)


def sweep_point(depth: int, width: int, timeout: int) -> dict:
    rows = A.deterministic_rows(depth, width)
    name = "sweep_%dx%d" % (depth, width)
    outdir = os.path.join(BUILD, name)
    os.makedirs(outdir, exist_ok=True)
    hex_stream = "".join("%0*x" % (width // 4, v) for v in rows)

    point = {
        "depth": depth,
        "width_bits": width,
        "bits": depth * width,
        "contents": "deterministic 64-bit LCG, seed 1234; identical for both "
                    "implementations at this point",
        "contents_sha256": O.hashlib.sha256(hex_stream.encode()).hexdigest(),
    }

    # ---- A: OpenROM hard macro ----------------------------------------
    t0 = time.time()
    b = O.build_rom(name, depth, width, hex_stream, outdir, ROOT,
                    wpr_candidates=WPR_LADDER, timeout=timeout)
    openrom = {
        "generated": b.generated,
        "words_per_row": b.words_per_row,
        "attempts": [{k: a[k] for k in ("words_per_row", "returncode",
                                        "elapsed_seconds", "generated")}
                     for a in b.attempts],
        "seconds": round(time.time() - t0, 1),
    }
    if b.generated:
        gds = os.path.join(ROOT, b.views["gds"]["path"])
        openrom["bbox"] = O.gds_bbox(gds, os.path.join(BUILD, "_scratch"))
        openrom["area_um2"] = openrom["bbox"]["area_um2"]
        openrom["lef_size"] = O.lef_size(os.path.join(ROOT,
                                                      b.views["lef"]["path"]))
        openrom["content_verification"] = O.verify_spice_content(
            os.path.join(ROOT, b.views["sp"]["path"]), name, rows, width,
            b.words_per_row)
    else:
        openrom["area_um2"] = None
        openrom["error_signature"] = b.error
    point["openrom"] = openrom

    # ---- B: portable case ROM mapped to SKY130 -------------------------
    src = os.path.join(outdir, name + "_portable.v")
    with open(src, "w") as fh:
        fh.write(A.emit_case_rom(name + "_portable", depth, width, rows))
    m = A.map_to_sky130([src], name + "_portable", outdir)
    point["portable"] = {
        "ok": m["ok"],
        "total_cells": m["total_cells"],
        "sequential_cells": m["sequential_cells"],
        "combinational_cells": m["combinational_cells"],
        "sequential_area_um2": m["sequential_area_um2"],
        "combinational_area_um2": m["combinational_area_um2"],
        "area_um2": m["chip_area_um2"],
        "blackboxes": m["blackboxes"],
        "seconds": m["seconds"],
        "netlist": os.path.relpath(m["netlist"], ROOT),
    }

    a, p = openrom["area_um2"], point["portable"]["area_um2"]
    point["ratio_openrom_over_portable"] = (round(a / p, 4)
                                            if a and p else None)
    point["smaller"] = (None if not (a and p)
                        else ("openrom" if a < p else "portable"))
    return point


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=int, default=10800)
    ap.add_argument("--points", type=int, nargs="*", default=None,
                    help="depths to sweep (width is fixed at 32 bits)")
    args = ap.parse_args()

    if not A.liberty_available():
        print("FATAL: SKY130 liberty not found at %s" % A.LIBERTY,
              file=sys.stderr)
        return 1

    points = (tuple((d, 32) for d in args.points) if args.points
              else DEFAULT_POINTS)
    os.makedirs(BUILD, exist_ok=True)
    record = (json.load(open(RECORD)) if os.path.exists(RECORD)
              else {"points": {}})
    record["liberty"] = A.LIBERTY
    record["liberty_corner"] = A.LIBERTY_CORNER
    record["toolchain"] = O.toolchain_versions()
    record["method"] = {
        "openrom_area": "GDS bounding box, measured with KLayout, hierarchy "
                        "resolved",
        "portable_area": "Yosys `stat -liberty` cell-area sum after ABC "
                         "mapping to sky130_fd_sc_hd",
        "caveat": "These are different kinds of area. The hard-macro bounding "
                  "box already contains its own decoders, precharge and supply "
                  "ring; the standard-cell number is a cell-area sum with no "
                  "placement utilisation or routing overhead. The sweep "
                  "locates where their ORDER changes; it is not an exact "
                  "final-chip area ratio.",
    }

    for depth, width in points:
        key = "%dx%d" % (depth, width)
        print("== sweep point %s (%d bits) ==" % (key, depth * width),
              flush=True)
        pt = sweep_point(depth, width, args.timeout)
        record["points"][key] = pt
        print("   openrom %s um^2   portable %s um^2   smaller=%s"
              % (pt["openrom"]["area_um2"], pt["portable"]["area_um2"],
                 pt["smaller"]), flush=True)
        _save(record)

    _save(record)
    print("\nwrote %s" % os.path.relpath(RECORD, ROOT))
    return 0


def _save(record: dict) -> None:
    tmp = RECORD + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, RECORD)


if __name__ == "__main__":
    raise SystemExit(main())
