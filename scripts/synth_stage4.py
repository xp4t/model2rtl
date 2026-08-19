#!/usr/bin/env python3
"""Stage 4 synthesis driver.

Runs BOTH synthesis flows -- FPGA-oriented (synth_ice40) and generic /
ASIC-oriented (standard Yosys logic synthesis) -- from the *same* frozen
production RTL, into build/stage4/.  Each flow runs twice from a clean output
directory so the determinism of the emitted netlist can be reported honestly.

The script never writes into rtl/ and never copies or patches a source file.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import stage4_synth as S     # noqa: E402


def freeze() -> dict:
    return {os.path.relpath(p, ROOT): S.sha256_file(os.path.join(ROOT, p))
            for p in S.PRODUCTION_SOURCES}


def describe(r: S.SynthResult, top: str = S.TOP) -> dict:
    table = S.FPGA_CATEGORIES if r.kind == "fpga" else S.GENERIC_CATEGORIES
    d = {
        "target": r.kind,
        "script_path": os.path.relpath(r.script_path, ROOT),
        "script_sha256": r.script_sha256,
        "script": open(r.script_path).read(),
        "log_path": os.path.relpath(r.log_path, ROOT),
        "netlist_path": os.path.relpath(r.netlist_path, ROOT),
        "netlist_sha256": r.netlist_sha256,
        "json_path": os.path.relpath(r.json_path, ROOT),
        "exit_status": r.returncode,
        "seconds": round(r.seconds, 2),
        "cells": r.cells,
        "resources": S.categorise(r.cells, table),
        "check": r.check,
        "unresolved_blackboxes": r.blackboxes,
        "netlist_evidence": S.netlist_evidence(r.netlist_path, r.kind, top),
        "status": "PASS" if r.ok else "FAIL",
    }
    if r.kind == "fpga":
        d["family"] = S.FPGA_FAMILY
        d["family_rationale"] = S.FPGA_FAMILY_RATIONALE
    return d


def main() -> int:
    before = freeze()
    build = os.path.join(ROOT, "build", "stage4")
    os.makedirs(build, exist_ok=True)

    record = {
        "tooling": {
            "python": sys.version.split()[0],
            "yosys": S.yosys_version(),
            "iverilog": S.iverilog_version(),
            "yosys_datdir": S.yosys_datdir(),
        },
        "source_freeze_before": before,
        "targets": {},
        "repeat": {},
    }
    libs = S.simlib_paths()
    record["tooling"]["simulation_libraries"] = {
        k: {"path": v, "sha256": S.sha256_file(v)} for k, v in libs.items()}

    for kind in ("fpga", "generic"):
        print("[synth] %s ..." % kind, flush=True)
        r = S.run_synth(ROOT, kind, os.path.join(build, kind))
        record["targets"][kind] = describe(r)
        print("  status=%s cells=%d %.1fs"
              % (record["targets"][kind]["status"],
                 record["targets"][kind]["resources"]["total_cells"],
                 r.seconds), flush=True)

        print("[synth] %s (repeat, clean dir) ..." % kind, flush=True)
        r2 = S.run_synth(ROOT, kind, os.path.join(build, "repeat_" + kind))
        record["repeat"][kind] = {
            "netlist_sha256": r2.netlist_sha256,
            "identical_to_first_run": r2.netlist_sha256 == r.netlist_sha256,
            "cells": r2.cells,
            "same_cell_counts": r2.cells == r.cells,
            "exit_status": r2.returncode,
            "seconds": round(r2.seconds, 2),
        }
        print("  repeat identical=%s"
              % record["repeat"][kind]["identical_to_first_run"], flush=True)

    # ---- diagnostic: the compute fabric on its own ------------------------
    # Read-only extra synthesis of rtl/mnist_mlp_fabric.v with no parameter
    # backend attached, so the MSA datapath cost can be separated from the
    # parameter-ROM cost.  Never simulated, not part of the portability claim.
    record["fabric_only_diagnostic"] = {}
    for kind in ("fpga", "generic"):
        print("[diag] fabric-only %s ..." % kind, flush=True)
        r = S.run_synth(ROOT, kind, os.path.join(build, "diag_fabric_" + kind),
                        builder=S.fabric_only_script, tag="fabric_only",
                        top="mnist_mlp_fabric")
        d = describe(r, top="mnist_mlp_fabric")
        d["constant_multiply"] = S.analyze_product_bank(
            r.json_path, r.netlist_path, top="mnist_mlp_fabric")
        record["fabric_only_diagnostic"][kind] = d
        print("  cells=%d" % d["resources"]["total_cells"], flush=True)

    # ---- what synthesis did to the 16 constant multiplications ------------
    for kind in ("fpga", "generic"):
        t = record["targets"][kind]
        t["constant_multiply"] = S.analyze_product_bank(
            os.path.join(ROOT, t["json_path"]),
            os.path.join(ROOT, t["netlist_path"]))

    after = freeze()
    record["source_freeze_after"] = after
    record["source_unchanged"] = (before == after)
    if not record["source_unchanged"]:
        print("FATAL: production RTL changed during synthesis", file=sys.stderr)

    out = os.path.join(build, "stage4_synth.json")
    tmp = out + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
    os.replace(tmp, out)
    print("wrote", os.path.relpath(out, ROOT))
    ok = (record["source_unchanged"]
          and all(t["status"] == "PASS" for t in record["targets"].values()))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
