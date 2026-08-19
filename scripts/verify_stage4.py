#!/usr/bin/env python3
"""Stage 4 verification + report.

Proves that the SAME frozen production RTL synthesizes through an
FPGA-oriented Yosys flow and a generic/ASIC-oriented Yosys flow with no source
change, and that BOTH synthesized gate-level netlists still perform bit-exact
inference against the Stage-0 integer golden model.

Writes reports/stage4_dual_target_portability.json.  A non-zero exit status
means Stage 4 is NOT complete.

Nothing here writes to rtl/ or model/.  Synthesis itself is done by
scripts/synth_stage4.py; this script re-verifies the netlist hashes it recorded
before using them.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import sys
import tempfile
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import stage3_sim as S3                            # noqa: E402
from model2rtl import stage4_synth as S4                          # noqa: E402
from model2rtl import storage as ST                               # noqa: E402
from model2rtl.fabric import FabricConfig                         # noqa: E402
from model2rtl.golden import IntegerModel                         # noqa: E402

REPORT = os.path.join(ROOT, "reports", "stage4_dual_target_portability.json")
SYNTH_RECORD = os.path.join(ROOT, "build", "stage4", "stage4_synth.json")

# Everything Stage 4 must leave untouched.
FROZEN = S4.PRODUCTION_SOURCES + [
    "rtl/mnist_mlp_params_openram.v",
    "rtl/mnist_mlp_params_sel_openram.v",
    "model/mnist_weights_indices.npz",
    "model/quant_params.json",
    "reports/stage0_quantization.json",
    "reports/stage1_compute_fabric.json",
    "reports/stage2_parameter_backends.json",
    "reports/stage3_behavioral_verification.json",
    "src/model2rtl/contract.py",
    "src/model2rtl/golden.py",
    "src/model2rtl/fabric.py",
    "src/model2rtl/param_image.py",
    "src/model2rtl/storage.py",
]

RESET_MID_POINT = 391      # mid layer-1 input streaming


def freeze() -> dict:
    return {p: S4.sha256_file(os.path.join(ROOT, p)) for p in FROZEN}


def golden(model: IntegerModel, x: np.ndarray):
    logits = model.forward(x)
    return logits, np.argmax(logits, axis=1)


def compare(run, logits, pred, label, expect_cycles=None) -> dict:
    d = {
        "images": int(logits.shape[0]),
        "logits_compared": int(logits.size),
        "prediction_comparisons": int(pred.size),
        "logit_mismatches": int((run.logits != logits).sum()),
        "prediction_mismatches": int((run.predictions != pred).sum()),
        "cycles_per_inference": sorted(set(run.cycles)),
        "gate_level_label_accuracy": float((run.predictions == label).mean()),
        "testbench_self_checks_passed": bool(run.tb_ok),
        "sim_seconds": round(run.sim_seconds, 1),
        "compile_seconds": round(run.compile_seconds, 1),
    }
    if expect_cycles is not None:
        d["latency_contract_cycles"] = expect_cycles
        d["latency_contract_held"] = (d["cycles_per_inference"]
                                      == [expect_cycles])
    d["ok"] = (d["logit_mismatches"] == 0 and d["prediction_mismatches"] == 0
               and d["testbench_self_checks_passed"]
               and d.get("latency_contract_held", True))
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=int, default=500,
                    help="gate-level images per target (>= 200 required)")
    ap.add_argument("--stall-images", type=int, default=12)
    ap.add_argument("--b2b-images", type=int, default=12)
    args = ap.parse_args()

    cfg = FabricConfig()
    expect_cycles = cfg.n_in + 2 * cfg.n_hidden + cfg.n_out + 6
    failures = []
    tmp = tempfile.mkdtemp(prefix="model2rtl_stage4_")

    before = freeze()

    # ---- synthesis record ------------------------------------------------
    if not os.path.isfile(SYNTH_RECORD):
        print("FATAL: %s missing -- run scripts/synth_stage4.py first"
              % os.path.relpath(SYNTH_RECORD, ROOT), file=sys.stderr)
        return 1
    with open(SYNTH_RECORD) as fh:
        synth = json.load(fh)

    print("== source freeze ==")
    same_as_synth = all(before[p] == synth["source_freeze_before"].get(p, "")
                        for p in S4.PRODUCTION_SOURCES)
    print("   production RTL identical to what synthesis read: %s"
          % same_as_synth)
    if not same_as_synth:
        failures.append("source-changed-since-synthesis")

    # ---- portability invariant -------------------------------------------
    # Both synthesis scripts must literally read the SAME absolute source
    # paths.  A copy-and-patch flow would name a different file.
    per_target_sources = {}
    for kind, t in synth["targets"].items():
        read = [l.split()[-1] for l in t["script"].splitlines()
                if l.startswith("read_verilog")]
        per_target_sources[kind] = {
            os.path.relpath(p, ROOT): S4.sha256_file(p) for p in read}
    portability = {
        "fpga_source_hashes": per_target_sources["fpga"],
        "generic_source_hashes": per_target_sources["generic"],
        "same_source_rtl": (per_target_sources["fpga"]
                            == per_target_sources["generic"]),
        "matches_working_tree": all(
            per_target_sources["fpga"].get(p) == before[p]
            for p in S4.PRODUCTION_SOURCES),
        "source_patches_applied": False,
        "sources_read_from": sorted(per_target_sources["fpga"]),
    }
    print("== portability invariant ==")
    print("   same source RTL on both targets: %s"
          % portability["same_source_rtl"])
    if not (portability["same_source_rtl"]
            and portability["matches_working_tree"]):
        failures.append("portability-source-identity")
    for p in portability["sources_read_from"]:
        if not p.startswith("rtl/"):
            failures.append("source-not-read-from-rtl")

    # ---- netlists still as synthesized ------------------------------------
    libs = S4.simlib_paths()
    netlists = {}
    for kind, t in synth["targets"].items():
        path = os.path.join(ROOT, t["netlist_path"])
        if not os.path.isfile(path):
            print("FATAL: missing netlist %s" % path, file=sys.stderr)
            return 1
        now = S4.sha256_file(path)
        if now != t["netlist_sha256"]:
            failures.append("netlist-changed-" + kind)
        netlists[kind] = path
        if t["status"] != "PASS":
            failures.append("synthesis-" + kind)
        if t["unresolved_blackboxes"]:
            failures.append("blackbox-" + kind)
        ev = t["netlist_evidence"]
        if not ev["top_ports_match_frozen_interface"]:
            failures.append("port-interface-" + kind)
        if ev["always_blocks"] or ev["case_statements"] \
                or ev["arithmetic_operators"] or ev["contains_readmemh"] \
                or ev["contains_initial_block"]:
            failures.append("netlist-not-structural-" + kind)
        if t["resources"]["latches"] or t["check"]["latches_inferred_lines"]:
            failures.append("latch-" + kind)
        if t["check"]["multiple_driver_lines"] \
                or t["check"]["undriven_net_lines"] \
                or t["check"]["wire_without_driver_lines"]:
            failures.append("driver-" + kind)

    # ---- per-target metadata the report must carry ------------------------
    targets = {}
    for kind, t in synth["targets"].items():
        d = dict(t)
        d["yosys_version"] = synth["tooling"]["yosys"]
        d["yosys_datdir"] = synth["tooling"]["yosys_datdir"]
        d["simulation_library"] = libs[kind]
        d["simulation_library_sha256"] = S4.sha256_file(libs[kind])
        r = t["resources"]
        if kind == "fpga":
            d["parameter_rom_mapping"] = (
                "inferred as %d SB_RAM40_4K block RAMs holding %d bits of INIT "
                "data; the ROM did not become LUT or mux logic"
                % (r["ram"], t["netlist_evidence"]["ram_init_bits"])
                if r["ram"] else
                "no block RAM was inferred: the ROM became LUT / mux logic")
            d["inferred_memories"] = r["ram"]
            d["multiplier_related_cells"] = r["dsp"]
            d["mux_lut_related_cells"] = r["lut"]
            d["registers"] = r["ff"]
        else:
            d["parameter_rom_mapping"] = (
                "the generic gate vocabulary has no memory primitive, so the "
                "ROM was synthesized into constant combinational logic")
            d["inferred_memories"] = 0
            d["multiplier_related_cells"] = r["arithmetic_or_multiplier_cells"]
            d["mux_lut_related_cells"] = r["mux"]
            d["registers"] = r["sequential"]
        targets[kind] = d

    # ---- oracle + image set ----------------------------------------------
    model = ST.load_indices(ST.default_paths(ROOT)["npz"])
    if args.images < 200:
        print("FATAL: Stage 4 requires >= 200 images", file=sys.stderr)
        return 1
    x, y, set_meta = S3.test_set(args.images)
    logits_g, pred_g = golden(model, x)
    set_meta["oracle"] = ("Stage-0 pure NumPy integer golden model "
                          "(model2rtl.golden.IntegerModel)")
    set_meta["integer_golden_accuracy"] = float((pred_g == y).mean())
    set_meta["reused_from_stage3"] = True
    print("== image set: %d images, %s ==" % (args.images,
                                              set_meta["selection_policy"]))
    print("   integer golden accuracy: %.4f"
          % set_meta["integer_golden_accuracy"])

    # ---- gate-level verification -----------------------------------------
    # The two targets are independent, and each spends its time inside a
    # single-threaded simulator subprocess, so they run concurrently.
    def verify_target(kind):
        local = []
        print("== gate-level simulation: %s ==" % kind, flush=True)
        wd = os.path.join(tmp, kind)
        r = S4.run_gls(ROOT, wd, kind, netlists[kind], libs[kind], x, cfg=cfg)
        main_cmp = compare(r, logits_g, pred_g, y, expect_cycles)
        print("   [%s] %d images: logit=%d prediction=%d mismatches, "
              "accuracy %.4f, cycles %s (%.0fs)"
              % (kind, main_cmp["images"], main_cmp["logit_mismatches"],
                 main_cmp["prediction_mismatches"],
                 main_cmp["gate_level_label_accuracy"],
                 main_cmp["cycles_per_inference"], r.sim_seconds), flush=True)
        if not main_cmp["ok"]:
            local.append("gls-" + kind)

        n_b = min(args.b2b_images, args.images)
        rb = S4.run_gls(ROOT, os.path.join(wd, "b2b"), kind, netlists[kind],
                        libs[kind], x[:n_b], cfg=cfg)
        b2b = compare(rb, logits_g[:n_b], pred_g[:n_b], y[:n_b], expect_cycles)
        b2b["note"] = ("%d inferences issued back to back inside ONE "
                       "simulation, no reset and no restart between them"
                       % n_b)
        print("   [%s] back-to-back %d: logit=%d prediction=%d mismatches"
              % (kind, n_b, b2b["logit_mismatches"],
                 b2b["prediction_mismatches"]), flush=True)
        if not b2b["ok"]:
            local.append("gls-b2b-" + kind)

        n_s = min(args.stall_images, args.images)
        rs = S4.run_gls(ROOT, os.path.join(wd, "stall"), kind, netlists[kind],
                        libs[kind], x[:n_s], stall_mode=1, stall_n=7, cfg=cfg)
        stall = compare(rs, logits_g[:n_s], pred_g[:n_s], y[:n_s])
        stall["pattern"] = "in_valid bubble after every 7th accepted activation"
        stall["cycles_exceed_nominal"] = all(c > expect_cycles
                                             for c in rs.cycles)
        print("   [%s] stalls: logit=%d prediction=%d mismatches, cycles %s"
              % (kind, stall["logit_mismatches"],
                 stall["prediction_mismatches"],
                 stall["cycles_per_inference"]), flush=True)
        if not stall["ok"]:
            local.append("gls-stall-" + kind)

        resets = {}
        for label, at in (("clean_reset_before_inference", 0),
                          ("reset_mid_inference", RESET_MID_POINT)):
            rr = S4.run_gls_reset(ROOT, os.path.join(wd, "reset_%d" % at), kind,
                                  netlists[kind], libs[kind], x[:1], at,
                                  cfg=cfg)
            c = compare(rr, logits_g[:1], pred_g[:1], y[:1], expect_cycles)
            c["reset_asserted_after_activations"] = at
            c["stale_state_observed"] = not rr.tb_ok
            resets[label] = c
            print("   [%s] reset %-32s logit=%d prediction=%d mismatches, "
                  "stale=%s" % (kind, label, c["logit_mismatches"],
                                c["prediction_mismatches"],
                                c["stale_state_observed"]), flush=True)
            if not c["ok"]:
                local.append("gls-reset-%s-%s" % (kind, label))

        entry = {
            "netlist_path": os.path.relpath(netlists[kind], ROOT),
            "netlist_sha256": synth["targets"][kind]["netlist_sha256"],
            "simulation_library": libs[kind],
            "simulation_library_sha256": S4.sha256_file(libs[kind]),
            "icarus_language_level": "-g2012 (required by the official Yosys "
                                     "cell library; the production RTL itself "
                                     "remains Verilog-2001)",
            "source_list_guard": r.guard,
            "observable_handshake_checks": [
                "done asserted exactly once per inference (pulse counted)",
                "prediction_valid high on the cycle done is high",
                "busy high on the cycle done is high",
                "done low again one cycle later (single-cycle pulse)",
                "in_ready respected: no activation issued while it is low",
            ],
            "handshake_checks_passed": bool(r.tb_ok),
            "no_stall": main_cmp,
            "back_to_back": b2b,
            "stalls": stall,
            "reset": resets,
        }
        return kind, entry, r, local

    gls = {}
    runs = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for kind, entry, r, local in pool.map(verify_target,
                                              ("fpga", "generic")):
            gls[kind] = entry
            runs[kind] = r
            failures.extend(local)

    # ---- cross target ------------------------------------------------------
    cross = {
        "logit_mismatches": int((runs["fpga"].logits
                                 != runs["generic"].logits).sum()),
        "prediction_mismatches": int((runs["fpga"].predictions
                                      != runs["generic"].predictions).sum()),
        "cycle_mismatches": int(sum(a != b for a, b in
                                    zip(runs["fpga"].cycles,
                                        runs["generic"].cycles))),
    }
    cross["identical"] = not any(cross.values())
    print("== fpga vs generic: %s ==" % ("identical" if cross["identical"]
                                         else "DIFFER"))
    if not cross["identical"]:
        failures.append("cross-target")

    # ---- resource analysis -------------------------------------------------
    resources = {
        "source_level_baselines": {
            "naive_fully_spatial_synapse_multiplications": 25408,
            "fully_spatial_msa_product_generators": 13056,
            "stage1_time_multiplexed_msa_product_expressions": 16,
            "caveat": ("These are SOURCE-LEVEL operation counts from the "
                       "Stage-1 analysis, not synthesized areas.  No ratio "
                       "between them is an area ratio, and none of them may be "
                       "divided by a synthesized cell count.  Only the two "
                       "synthesized numbers below are measured."),
        },
        "fpga": {
            "family": S4.FPGA_FAMILY,
            "cells": targets["fpga"]["cells"],
            "categories": targets["fpga"]["resources"],
            "parameter_rom_mapping": targets["fpga"]["parameter_rom_mapping"],
            "fabric_only_diagnostic":
                synth["fabric_only_diagnostic"]["fpga"]["resources"],
        },
        "generic": {
            "cells": targets["generic"]["cells"],
            "categories": targets["generic"]["resources"],
            "parameter_rom_mapping": targets["generic"]["parameter_rom_mapping"],
            "fabric_only_diagnostic":
                synth["fabric_only_diagnostic"]["generic"]["resources"],
        },
        "physical_area": ("not available at this stage: no characterized "
                          "standard-cell library was used, so cell counts "
                          "cannot be converted to area"),
        "constant_multiplication": {
            kind: targets[kind]["constant_multiply"]
            for kind in ("fpga", "generic")},
    }

    after = freeze()
    unchanged = (before == after)
    if not unchanged:
        failures.append("frozen-artifact-changed")
        for p in FROZEN:
            if before[p] != after[p]:
                print("CHANGED: %s" % p, file=sys.stderr)

    report = {
        "stage": 4,
        "title": "dual-target synthesis portability + gate-level verification",
        "status": "PASS" if not failures else "FAIL",
        "failures": sorted(set(failures)),
        "source_freeze": {
            "before": before,
            "after": after,
            "unchanged": unchanged,
        },
        "reproducibility": {
            "python": platform.python_version(),
            "yosys": synth["tooling"]["yosys"],
            "iverilog": synth["tooling"]["iverilog"],
            "yosys_datdir": synth["tooling"]["yosys_datdir"],
            "simulation_libraries": synth["tooling"]["simulation_libraries"],
            "fpga_family": S4.FPGA_FAMILY,
            "repeat_synthesis": synth["repeat"],
        },
        "fpga_target": targets["fpga"],
        "generic_target": targets["generic"],
        "fabric_only_diagnostic": synth["fabric_only_diagnostic"],
        "gate_level_verification": {
            "image_selection": set_meta,
            "oracle": ("Stage-0 pure NumPy integer golden model; pre-synthesis "
                       "RTL was NOT used as the oracle"),
            "fpga": gls["fpga"],
            "generic": gls["generic"],
            "cross_target": cross,
        },
        "portability": dict(portability, **{
            "fpga_gls": "PASS" if gls["fpga"]["no_stall"]["ok"] else "FAIL",
            "generic_gls": ("PASS" if gls["generic"]["no_stall"]["ok"]
                            else "FAIL"),
        }),
        "resource_analysis": resources,
        "formal_equivalence_check": {
            "performed": False,
            "reason": ("optional supplemental evidence only; gate-level "
                       "simulation against the Stage-0 integer oracle was run "
                       "instead and is the mandatory check"),
        },
        "limitations": [
            "No FPGA place-and-route was run: synth_ice40 output was not "
            "passed to nextpnr and no bitstream exists.",
            "No FPGA timing analysis and no Fmax was measured. The Stage-1 "
            "50/100 MHz figures remain architectural latency examples only.",
            "No ASIC physical implementation: the generic flow maps to the "
            "Yosys generic gate vocabulary, not to a SKY130 standard-cell "
            "library, and no floorplan, placement, routing or extraction was "
            "performed.",
            "No ASIC timing analysis and no characterized-library area.",
            "Stage-2 physical OpenROM backend remains PARTIAL and was not "
            "touched in Stage 4; the OpenRAM behavioural backend was "
            "deliberately excluded from Stage 4, which uses the portable "
            "backend only.",
        ],
        "openrom_physical_backend": "PARTIAL (unchanged from Stage 2)",
        "stage5_implemented": False,
        "rtl2gdsagi_modified": False,
    }

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    t = REPORT + ".tmp"
    with open(t, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    os.replace(t, REPORT)
    print("\nwrote %s -- %s" % (os.path.relpath(REPORT, ROOT),
                                report["status"]))
    if failures:
        print("FAILURES: %s" % ", ".join(sorted(set(failures))),
              file=sys.stderr)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
