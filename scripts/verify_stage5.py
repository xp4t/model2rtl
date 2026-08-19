#!/usr/bin/env python3
"""Stage 5 verification + report.

Consumes the artefacts the Stage-5 build scripts produced -- it does not
re-generate macros -- re-verifies every one of them against the frozen
canonical images, and writes

    reports/stage5_openrom_physical.json

A non-zero exit status means Stage 5 is NOT complete.  Physical GENERATION and
physical SIGNOFF are reported as two separate verdicts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import openrom as O                              # noqa: E402
from model2rtl import phys_image as P                           # noqa: E402
from model2rtl import stage3_sim as S3                          # noqa: E402
from model2rtl import stage5_sim as S5                          # noqa: E402
from model2rtl import storage as ST                             # noqa: E402
from model2rtl import asic_storage as A                         # noqa: E402
from model2rtl.fabric import FabricConfig, unpack_weight_word    # noqa: E402
from model2rtl.golden import (alphabet_lookup,                   # noqa: E402
                              requantize_relu_u8)
from model2rtl.param_image import (IMAGE_ORDER, build_images,    # noqa: E402
                                   bias_bus_word, weight_bus_word)

REPORT = os.path.join(ROOT, "reports", "stage5_openrom_physical.json")
BUILD = os.path.join(ROOT, "build", "stage5")
MACRO_RECORD = os.path.join(BUILD, "stage5_openrom_build.json")
SWEEP_RECORD = os.path.join(BUILD, "stage5_sweep.json")
DRCLVS_RECORD = os.path.join(BUILD, "stage5_drclvs.json")
FULLMODEL = os.path.join(BUILD, "fullmodel", "fullmodel.json")
PORTABLE_ASIC = os.path.join(BUILD, "portable_asic", "result.json")

FROZEN = [
    "rtl/mnist_mlp_fabric.v",
    "rtl/mnist_mlp_params_portable.v",
    "rtl/mnist_mlp_params_openram.v",
    "rtl/mnist_mlp_top.v",
    "rtl/mnist_mlp_params_sel_portable.v",
    "rtl/mnist_mlp_params_sel_openram.v",
    "model/mnist_weights_indices.npz",
    "model/quant_params.json",
    "src/model2rtl/contract.py",
    "src/model2rtl/golden.py",
    "src/model2rtl/fabric.py",
    "src/model2rtl/param_image.py",
    "src/model2rtl/storage.py",
    "reports/stage0_quantization.json",
    "reports/stage1_compute_fabric.json",
    "reports/stage2_parameter_backends.json",
    "reports/stage3_behavioral_verification.json",
    "reports/stage4_dual_target_portability.json",
]

STAGE5_NEW_RTL = ["rtl/mnist_mlp_params_openrom_phys.v",
                  "rtl/mnist_mlp_params_sel_openrom_phys.v"]


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def freeze():
    return {p: sha(os.path.join(ROOT, p)) for p in FROZEN}


def _need(path, what):
    if not os.path.exists(path):
        print("FATAL: %s missing -- %s" % (os.path.relpath(path, ROOT), what),
              file=sys.stderr)
        raise SystemExit(1)
    return json.load(open(path))


# --------------------------------------------------------------------------
# Complete physical -> logical readback
# --------------------------------------------------------------------------

def readback(phys, logical, cfg) -> dict:
    """Rebuild every logical row, every weight index and every bias from the
    PHYSICAL images alone, and compare with the frozen Stage-0 model."""
    model = ST.load_indices(ST.default_paths(ROOT)["npz"])
    decoded = P.decode_physical(phys, logical)

    rows_checked = rows_bad = 0
    per_memory = {}
    for name in IMAGE_ORDER:
        want, got = list(logical[name].rows), decoded[name]
        bad = [i for i, (a, b) in enumerate(zip(want, got)) if a != b]
        per_memory[name] = {
            "logical_shape": "%d x %d" % (logical[name].depth,
                                          logical[name].width),
            "physical_macros": list(P.macros_of(name)),
            "rows_checked": len(want),
            "row_mismatches": len(bad),
        }
        rows_checked += len(want)
        rows_bad += len(bad)

    # weight indices, unpacked from the reconstructed rows
    idx_checked = idx_bad = 0
    for name, indices, n_out in (
            ("weights_l1", model.layer1_weight_indices, cfg.n_hidden),
            ("weights_l2", model.layer2_weight_indices, cfg.n_out)):
        got = np.array([unpack_weight_word(v, n_out, cfg)
                        for v in decoded[name]], dtype=np.int64)
        idx_checked += int(indices.size)
        idx_bad += int((got != indices).sum())
        per_memory[name]["weight_indices_checked"] = int(indices.size)
        per_memory[name]["weight_index_mismatches"] = int((got != indices).sum())

    # biases, all the way through the interface
    bias_checked = bias_bad = 0
    edge = {}
    for layer, name, arr in ((0, "bias_l1", model.layer1_bias),
                             (1, "bias_l2", model.layer2_bias)):
        for a, v in enumerate(arr):
            want = bias_bus_word(logical, layer, a)
            got = P.bias_bus_word_from_physical(phys, layer, a)
            bias_checked += 1
            if want != got:
                bias_bad += 1
        per_memory[name]["bias_values_checked"] = int(len(arr))
        vals = [int(v) for v in arr]
        edge[name] = {
            "min_present": min(vals), "max_present": max(vals),
            "contains_zero": 0 in vals,
            "contains_plus_one": 1 in vals,
            "contains_minus_one": -1 in vals,
        }

    # explicit encode/decode round trip on the required special values
    special = {}
    for name, bits in (("bias_l1", logical["bias_l1"].width),
                       ("bias_l2", logical["bias_l2"].width)):
        cases = [0, 1, -1, (1 << (bits - 1)) - 1, -(1 << (bits - 1))]
        vals = [int(v) for v in (model.layer1_bias if name == "bias_l1"
                                 else model.layer2_bias)]
        cases += [max(vals), min(vals)]
        rows = []
        for v in cases:
            two = v & ((1 << bits) - 1)
            physv = P._sign_extend(two, bits, P.BIAS_PHYS_BITS)
            back = P._truncate(physv, bits)
            signed_back = back - (1 << bits) if back >> (bits - 1) else back
            rows.append({"logical": v, "physical_24bit": "0x%06x" % physv,
                         "recovered": signed_back, "exact": signed_back == v})
        special[name] = rows

    bad_special = sum(1 for n in special for r in special[n]
                      if not r["exact"])
    return {
        "per_memory": per_memory,
        "logical_rows_checked": rows_checked,
        "logical_row_mismatches": rows_bad,
        "weight_indices_checked": idx_checked,
        "weight_index_mismatches": idx_bad,
        "bias_values_checked": bias_checked,
        "bias_mismatches": bias_bad,
        "bias_edge_values_present": edge,
        "bias_special_value_roundtrip": special,
        "bias_special_value_failures": bad_special,
        "mismatches": rows_bad + idx_bad + bias_bad + bad_special,
    }


# --------------------------------------------------------------------------
# Crossover
# --------------------------------------------------------------------------

def crossover(sweep: dict) -> dict:
    pts = sorted(sweep["points"].values(), key=lambda p: p["bits"])
    table = [{
        "point": "%dx%d" % (p["depth"], p["width_bits"]),
        "bits": p["bits"],
        "openrom_bbox_um2": p["openrom"]["area_um2"],
        "openrom_words_per_row": p["openrom"]["words_per_row"],
        "portable_cell_area_um2": p["portable"]["area_um2"],
        "portable_cells": p["portable"]["total_cells"],
        "ratio_openrom_over_portable": p["ratio_openrom_over_portable"],
        "smaller": p["smaller"],
    } for p in pts]
    winners = [t for t in table if t["smaller"] == "openrom"]
    smallest = min(winners, key=lambda t: t["bits"]) if winners else None
    ratios = [t["ratio_openrom_over_portable"] for t in table
              if t["ratio_openrom_over_portable"]]
    out = {
        "measured_points": table,
        "smallest_openrom_winning_point": smallest,
        "measured_crossover_interval": None,
        "conclusion": None,
        "break_even_utilisation": None,
    }
    if smallest is None:
        deepest = table[-1]
        out["measured_crossover_interval"] = (
            "none: the portable standard-cell mapping is smaller at every "
            "measured point from %d to %d bits" % (table[0]["bits"],
                                                   deepest["bits"]))
        out["conclusion"] = (
            "No crossover was measured. The OpenROM bounding box exceeds the "
            "portable mapped cell area at all %d points, and the ratio is "
            "%.2f at the smallest point and %.2f at the largest, so it "
            "flattens rather than converging towards 1. Any statement about "
            "sizes beyond %d bits would be extrapolation and is not made."
            % (len(table), ratios[0], ratios[-1], deepest["bits"]))
        if deepest["ratio_openrom_over_portable"]:
            out["break_even_utilisation"] = {
                "value": round(1.0 / deepest["ratio_openrom_over_portable"], 4),
                "meaning": "A placed portable block occupies cell_area / "
                           "utilisation. At the deepest measured point the two "
                           "areas would be equal only if the portable block "
                           "were placed at this utilisation or worse. This is "
                           "a derived sensitivity, not a measurement.",
            }
    else:
        below = [t for t in table if t["bits"] < smallest["bits"]]
        out["measured_crossover_interval"] = (
            "portable smaller at %d bits, OpenROM smaller at %d bits, so the "
            "crossover lies between them"
            % (below[-1]["bits"], smallest["bits"]) if below else
            "OpenROM already smaller at the smallest measured point (%d bits)"
            % smallest["bits"])
        out["conclusion"] = "measured crossover interval reported above"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=int, default=500)
    args = ap.parse_args()

    cfg = FabricConfig()
    failures = []
    before = freeze()

    macro_rec = _need(MACRO_RECORD, "run scripts/gen_openrom_stage5.py")
    sweep_rec = _need(SWEEP_RECORD, "run scripts/sweep_stage5.py")
    drclvs_rec = _need(DRCLVS_RECORD, "run scripts/verify_physical_stage5.py")
    fullmodel = _need(FULLMODEL, "run the Stage-5 full-model inference")
    portable_asic = _need(PORTABLE_ASIC, "run the portable SKY130 mapping")

    model = ST.load_indices(ST.default_paths(ROOT)["npz"])
    logical = build_images(model, cfg)
    phys = P.build_physical_images(logical)

    print("== physical representation ==")
    roundtrip = P.verify_roundtrip(phys, logical)
    print("   round trip %d rows, %d mismatches"
          % (roundtrip["rows_checked"], roundtrip["mismatches"]))
    if roundtrip["mismatches"]:
        failures.append("physical-roundtrip")

    # ---- macros -----------------------------------------------------------
    print("== macros ==")
    macros = {}
    total_area = 0.0
    for name in P.PHYS_ORDER:
        m = macro_rec["macros"].get(name)
        if not m:
            failures.append("macro-missing-" + name)
            continue
        img = phys[name]
        if m["physical_image_sha256"] != img.sha256():
            failures.append("macro-image-sha-" + name)
        views_ok = True
        for ext, v in m["views"].items():
            p = os.path.join(ROOT, v["path"])
            if not os.path.exists(p) or O.sha256_file(p) != v["sha256"]:
                views_ok = False
        if not views_ok:
            failures.append("macro-view-changed-" + name)
        if not m["generated"] or m["status"] != "PASS":
            failures.append("macro-not-generated-" + name)
        cv = m["content_verification"]
        if not cv["exact"]:
            failures.append("macro-content-" + name)
        d = drclvs_rec["macros"].get(name, {})
        entry = {
            "macro": name,
            "logical_memory": img.logical_memory,
            "requested_shape": "%d x %d" % (img.depth, img.width),
            "words_per_row": m["words_per_row"],
            "array_rows": m["array_rows"],
            "array_cols": m["array_cols"],
            "words_per_row_attempts": [
                {k: a[k] for k in ("words_per_row", "returncode",
                                   "elapsed_seconds", "generated")}
                for a in m["attempts"]],
            "generated": m["generated"],
            "runtime_seconds": m["elapsed_seconds"],
            "views": m["views"],
            "views_generated": m["views_generated"],
            "data_image": m["data_image"],
            "physical_image": m["physical_image"],
            "content_verification": cv,
            "bbox": m["bbox"],
            "lef_size": m["lef_size"],
            "generated_verilog_properties": m["generated_verilog"],
            "drc_errors": d.get("drc_errors"),
            "drc_status": d.get("drc_status", "not run"),
            "lvs_status": d.get("lvs_status", "not run"),
            "status": m["status"],
        }
        macros[name] = entry
        total_area += m["bbox"]["area_um2"]
        print("   %-14s %s  %d/%d bits exact  bbox %.1f um^2  DRC=%s LVS=%s"
              % (name, m["status"],
                 cv["bits_checked"] - cv["bit_mismatches"], cv["bits_checked"],
                 m["bbox"]["area_um2"], entry["drc_status"],
                 entry["lvs_status"]))

    # ---- readback ---------------------------------------------------------
    print("== complete readback from the physical images ==")
    rb = readback(phys, logical, cfg)
    print("   %d logical rows, %d weight indices, %d biases, %d mismatches"
          % (rb["logical_rows_checked"], rb["weight_indices_checked"],
             rb["bias_values_checked"], rb["mismatches"]))
    if rb["mismatches"]:
        failures.append("readback")

    # ---- three-way logical equivalence ------------------------------------
    print("== three-way backend equivalence ==")
    tmp = tempfile.mkdtemp(prefix="model2rtl_stage5_")
    eq = S5.run_three_way(ROOT, os.path.join(tmp, "params3"), logical, cfg)
    print("   %d weight + %d bias comparisons, %d mismatches"
          % (eq["weight_comparisons"], eq["bias_comparisons"],
             eq["mismatches"]))
    if eq["mismatches"]:
        failures.append("backend-equivalence")

    # ---- full model -------------------------------------------------------
    print("== full model ==")
    fm = fullmodel
    for k in ("openrom_phys", "portable"):
        v = fm[k]
        if any(v[f] for f in ("hidden_mismatches", "logit_mismatches",
                              "prediction_mismatches")):
            failures.append("fullmodel-" + k)
        print("   %-13s %d images  hidden=%d logit=%d prediction=%d  acc %.4f"
              % (k, v["images"], v["hidden_mismatches"], v["logit_mismatches"],
                 v["prediction_mismatches"], v["label_accuracy"]))
    if any(fm["backend_to_backend"].values()):
        failures.append("fullmodel-backend-to-backend")
    if fm["openrom_phys"]["images"] < args.images:
        failures.append("fullmodel-too-few-images")

    # ---- portable ASIC storage -------------------------------------------
    print("== portable storage mapped to SKY130 ==")
    if not portable_asic["ok"]:
        failures.append("portable-asic-mapping")
    print("   %d cells, %s um^2, blackboxes %s"
          % (portable_asic["total_cells"], portable_asic["chip_area_um2"],
             portable_asic["blackboxes"]))

    # ---- area comparison --------------------------------------------------
    p_area = portable_asic["chip_area_um2"]
    area = {
        "openrom_total_macro_bbox_um2": round(total_area, 3),
        "openrom_per_macro_um2": {k: v["bbox"]["area_um2"]
                                  for k, v in macros.items()},
        "openrom_weights_l1_bank_sum_um2": round(
            sum(macros["weights_l1_b%d" % b]["bbox"]["area_um2"]
                for b in range(P.L1_BANKS)), 3),
        "portable_mapped_cell_area_um2": p_area,
        "ratio_openrom_over_portable": (round(total_area / p_area, 4)
                                        if p_area else None),
        "measurement_kinds": {
            "openrom": "hard-macro GDS bounding box, measured with KLayout "
                       "(hierarchy resolved). It already contains the decoders, "
                       "column mux, precharge and the supply ring.",
            "portable": "synthesized standard-cell area: the sum of the "
                        "sky130_fd_sc_hd liberty cell areas after ABC mapping. "
                        "It excludes placement utilisation and routing "
                        "overhead.",
        },
        "caveat": "These two numbers are NOT the same kind of area and their "
                  "ratio is NOT a finished-chip area ratio. A placed portable "
                  "block would occupy cell area divided by its utilisation, "
                  "which is not measured here because Stage 5 runs no "
                  "place-and-route. There is also no floorplan: the macro "
                  "figure is a raw sum of bounding boxes, not a floorplanned "
                  "area, and no placement density is claimed.",
        "floorplanned_area": "not available: no floorplan was produced",
    }
    print("   OpenROM total %.1f um^2 vs portable %.1f um^2 (ratio %.2f)"
          % (total_area, p_area, area["ratio_openrom_over_portable"]))

    # ---- crossover --------------------------------------------------------
    print("== crossover ==")
    cross = crossover(sweep_rec)
    print("   %s" % cross["measured_crossover_interval"])

    # ---- physical signoff -------------------------------------------------
    print("== physical signoff ==")
    signoff = {
        "control": drclvs_rec["control"],
        "control_description": drclvs_rec["control_description"],
        "control_is_clean": drclvs_rec["control_is_clean"],
        "macro_results": {k: {"drc_errors": v.get("drc_errors"),
                              "drc_status": v.get("drc_status"),
                              "lvs_status": v.get("lvs_status"),
                              "log": v.get("log")}
                          for k, v in drclvs_rec["macros"].items()},
        "status": drclvs_rec["signoff_status"],
        "reasoning": drclvs_rec["signoff_reasoning"],
        "physical_generation": ("PASS" if not [f for f in failures
                                               if f.startswith("macro-")]
                                else "FAIL"),
    }
    print("   control clean=%s -> signoff %s"
          % (signoff["control_is_clean"], signoff["status"]))

    after = freeze()
    unchanged = (before == after)
    if not unchanged:
        failures.append("frozen-artifact-changed")
        for p in FROZEN:
            if before[p] != after[p]:
                print("CHANGED: %s" % p, file=sys.stderr)

    report = {
        "stage": 5,
        "title": "complete ASIC OpenROM backend + physical storage analysis",
        "status": "PASS" if not failures else "FAIL",
        "failures": sorted(set(failures)),
        "source_freeze": {"before": before, "after": after,
                          "unchanged": unchanged},
        "stage5_new_rtl": {p: sha(os.path.join(ROOT, p))
                           for p in STAGE5_NEW_RTL},
        "stage5_new_rtl_note":
            "rtl/mnist_mlp_params_openram.v is frozen, so the physical "
            "organisation lives in a NEW backend file plus its own build-time "
            "selector. Nothing frozen was edited; mnist_mlp_top.v instantiates "
            "the abstract module `mnist_mlp_params` and is unchanged.",
        "toolchain": macro_rec["toolchain"],
        "python": platform.python_version(),
        "physical_representation": {
            "logical_images": macro_rec["logical_images"],
            "physical_images": macro_rec["physical_images"],
            "roundtrip": roundtrip,
            "transformations": {
                "weights_l1": "banked into %d parallel macros of %d x %d; all "
                              "banks share one address and are read together, "
                              "so the external latency stays one cycle"
                              % (P.L1_BANKS, logical["weights_l1"].depth,
                                 P.L1_BANK_BITS),
                "weights_l2": "identity: already byte granular",
                "bias_l1": "sign extended 22 -> 24 bits",
                "bias_l2": "sign extended 17 -> 24 bits, then recovered and "
                           "sign extended 17 -> 22 on the bus",
            },
            "bit_order_transform": P.OPENROM_DOUT_CONVENTION,
        },
        "macros": macros,
        "logical_equivalence": {"readback": rb, "backend_bus": eq},
        "full_model": fm,
        "portable_asic_storage": {
            "liberty": portable_asic["liberty"],
            "liberty_corner": portable_asic["liberty_corner"],
            "top": portable_asic["top"],
            "total_cells": portable_asic["total_cells"],
            "sequential_cells": portable_asic["sequential_cells"],
            "combinational_cells": portable_asic["combinational_cells"],
            "sequential_area_um2": portable_asic["sequential_area_um2"],
            "combinational_area_um2": portable_asic["combinational_area_um2"],
            "chip_area_um2": portable_asic["chip_area_um2"],
            "blackboxes": portable_asic["blackboxes"],
            "area_source": portable_asic["area_source"],
            "qualifications": [
                "No place and route was run, so this is a cell-area sum and "
                "not a placed block area.",
                "No timing constraint was applied; ABC mapped for area with "
                "the default script.",
                "The number covers the whole parameter backend (all four "
                "logical memories, %d bits) as ONE synthesized block, which "
                "lets the mapper share logic across memories."
                % sum(i.depth * i.width for i in logical.values()),
            ],
        },
        "area": area,
        "crossover": cross,
        "physical_signoff": signoff,
        "not_claimed": [
            "No macro is DRC-clean or LVS-clean: the environment's control "
            "fails, so no physical-verification result here is evidence.",
            "No full-chip GDS, no floorplan, no placement, no routing.",
            "No timing analysis and no maximum clock frequency.",
            "The area comparison is between two different kinds of area and "
            "is not a finished-chip ratio.",
            "No crossover point is claimed beyond the measured data.",
        ],
        "full_chip_gds": "NOT ATTEMPTED",
        "rtl2gdsagi_used": False,
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
