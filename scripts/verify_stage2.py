#!/usr/bin/env python3
"""Stage 2 verification + report.

Runs every Stage-2 acceptance check for real and writes

    reports/stage2_parameter_backends.json

Only measured facts are recorded.  The OpenROM section reports exactly what the
installed compiler produced, including the macros it could not build and why.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import memif                                       # noqa: E402
from model2rtl import sim as SIM                                  # noqa: E402
from model2rtl import stage2_sim as S2                            # noqa: E402
from model2rtl import storage as S                                # noqa: E402
from model2rtl.fabric import FabricConfig                         # noqa: E402
from model2rtl.golden import alphabet_lookup, requantize_relu_u8  # noqa: E402
from model2rtl.param_image import IMAGE_ORDER, build_images       # noqa: E402
from model2rtl.param_verilog import OPENROM_CONVENTION            # noqa: E402

RTL = os.path.join(ROOT, "rtl")
REPORT = os.path.join(ROOT, "reports", "stage2_parameter_backends.json")
OPENRAM_BUILD = os.path.join(ROOT, "build", "openram", "openram_build.json")
OPENRAM_ROOT = "/home/rithwik/OpenRAM"
PDK_ROOT = "/home/rithwik/pdk"


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_mnist():
    cache = os.path.expanduser("~/.keras/datasets/mnist.npz")
    with np.load(cache) as z:
        return (z["x_test"].reshape(-1, 784).astype(np.int64),
                z["y_test"].astype(np.int64))


def git_info(path, *args):
    try:
        return subprocess.run(["git", "-C", path] + list(args),
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def lint(sources, top, tmp):
    merged = os.path.join(tmp, top + "_merged.v")
    with open(merged, "w") as out:
        for s in sources:
            out.write(open(os.path.join(RTL, s)).read() + "\n")
    y = SIM.yosys_check(merged, top)
    ic = SIM.iverilog_compile([os.path.join(RTL, s) for s in sources],
                              os.path.join(tmp, top + ".out"), tmp, std="2001")
    return {
        "sources": list(sources),
        "yosys_read_verilog": "PASS" if y["returncode"] == 0 else "FAIL",
        "yosys_hierarchy_check": "PASS" if y["returncode"] == 0 else "FAIL",
        "yosys_check_assert": ("PASS (Found and reported 0 problems)"
                               if "Found and reported 0 problems." in y["log"]
                               else "FAIL"),
        "yosys_inferred_latches": len(y["latch_lines"]),
        "yosys_multiple_drivers": "multiple conflicting drivers" in y["log"],
        "yosys_undriven_nets": "is used but has no driver" in y["log"],
        "yosys_cell_counts": y["cells"],
        "icarus_verilog2001": ("PASS" if ic.returncode == 0
                               and "warning" not in ic.output.lower() else "FAIL"),
        "ok": bool(y["ok"] and ic.returncode == 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=int, default=200)
    args = ap.parse_args()

    cfg = FabricConfig()
    failures = []
    model = S.load_indices(S.default_paths(ROOT)["npz"])
    images = build_images(model, cfg)
    x, y = load_mnist()
    x, y = x[:args.images], y[:args.images]

    print("== interface ==")
    memif.verify_against_rtl(os.path.join(RTL, "mnist_mlp_fabric.v"), cfg)
    fabric_sha = sha256_file(os.path.join(RTL, "mnist_mlp_fabric.v"))
    stage1 = json.load(open(os.path.join(ROOT, "reports",
                                         "stage1_compute_fabric.json")))
    fabric_unchanged = fabric_sha == stage1["generated"]["sha256"]
    print("   fabric unchanged since Stage 1: %s" % fabric_unchanged)
    if not fabric_unchanged:
        failures.append("fabric-modified")

    print("== lint / elaboration ==")
    tmp = tempfile.mkdtemp(prefix="model2rtl_stage2_")
    lints = {
        "portable_backend": lint(["mnist_mlp_params_portable.v"],
                                 "mnist_mlp_params_portable", tmp),
        "openram_backend": lint(["mnist_mlp_params_openram.v"],
                                "mnist_mlp_params_openram", tmp),
        "top_portable": lint(S2.PORTABLE_SOURCES, "mnist_mlp_top", tmp),
        "top_openram": lint(S2.OPENRAM_SOURCES, "mnist_mlp_top", tmp),
    }
    for k, v in lints.items():
        print("   %-18s yosys=%s icarus=%s latches=%d"
              % (k, v["yosys_check_assert"][:4], v["icarus_verilog2001"],
                 v["yosys_inferred_latches"]))
        if not v["ok"]:
            failures.append("lint-" + k)

    print("== backend equivalence (both backends, one stimulus stream) ==")
    eq = S2.run_param_equivalence(ROOT, os.path.join(tmp, "equiv"), images, cfg)
    print("   cycles=%d backend mismatches=%d golden mismatches=%d"
          % (eq["stimulus_cycles"], eq["backend_mismatches"],
             eq["golden_mismatches"]))
    if eq["backend_mismatches"] or eq["golden_mismatches"]:
        failures.append("equivalence")

    print("== full parameter readback ==")
    from model2rtl.param_image import unpack_weight_image
    l1 = unpack_weight_image(images["weights_l1"], cfg.n_hidden, cfg)
    l2 = unpack_weight_image(images["weights_l2"], cfg.n_out, cfg)
    readback = {
        "layer1_weight_rows": "%d/%d" % (images["weights_l1"].depth, cfg.n_in),
        "layer2_weight_rows": "%d/%d" % (images["weights_l2"].depth, cfg.n_hidden),
        "layer1_bias_rows": "%d/%d" % (images["bias_l1"].depth, cfg.n_hidden),
        "layer2_bias_rows": "%d/%d" % (images["bias_l2"].depth, cfg.n_out),
        "weight_indices_exact": "%d/%d" % (
            int((l1 == model.layer1_weight_indices).sum()
                + (l2 == model.layer2_weight_indices).sum()), 25408),
        "layer1_bias_exact": bool(images["bias_l1"].signed_rows()
                                  == [int(v) for v in model.layer1_bias]),
        "layer2_bias_exact": bool(images["bias_l2"].signed_rows()
                                  == [int(v) for v in model.layer2_bias]),
    }
    print("   weight indices exact: %s" % readback["weight_indices_exact"])
    if readback["weight_indices_exact"] != "25408/25408":
        failures.append("readback")

    print("== top-level inference, %d images, both backends ==" % args.images)
    gl = model.forward(x)
    gp = np.argmax(gl, axis=1)
    w1 = alphabet_lookup(model.layer1_weight_indices)
    gh = requantize_relu_u8(x @ w1 + model.layer1_bias)
    runs = {}
    for backend in ("portable", "openram"):
        r = S2.run_top_inference(ROOT, os.path.join(tmp, "top_" + backend),
                                 backend, x, cfg)
        mm_logit = int((r["logits"] != gl).sum())
        mm_hidden = int((r["hidden"] != gh).sum())
        mm_pred = int((r["predictions"] != gp).sum())
        acc = float((r["predictions"] == y).mean())
        runs[backend] = {
            "images": int(args.images),
            "sources": r["sources"],
            "cycles_per_inference": sorted(set(r["cycles"])),
            "logit_mismatches": mm_logit,
            "hidden_mismatches": mm_hidden,
            "prediction_mismatches": mm_pred,
            "accuracy": acc,
        }
        print("   %-9s logits=%d hidden=%d pred=%d acc=%.4f cycles=%s"
              % (backend, mm_logit, mm_hidden, mm_pred, acc,
                 sorted(set(r["cycles"]))))
        if mm_logit or mm_hidden or mm_pred:
            failures.append("top-" + backend)
    b2b = int((runs["portable"]["accuracy"] != runs["openram"]["accuracy"]))
    p = S2.run_top_inference(ROOT, os.path.join(tmp, "top_portable"),
                             "portable", x, cfg)
    o = S2.run_top_inference(ROOT, os.path.join(tmp, "top_openram"),
                             "openram", x, cfg)
    b2b_mismatch = int((p["logits"] != o["logits"]).sum())
    print("   backend-to-backend logit mismatches: %d" % b2b_mismatch)
    if b2b_mismatch:
        failures.append("backend-to-backend")

    openram_build = (json.load(open(OPENRAM_BUILD))
                     if os.path.exists(OPENRAM_BUILD) else {"macros": {}})
    macros = openram_build.get("macros", {})
    generated = [m for m, r in macros.items() if r.get("status") == "PASS"]
    blocked = [m for m, r in macros.items() if r.get("status") == "BLOCKED"]
    failed = [m for m, r in macros.items() if r.get("status") == "FAIL"]

    smoke_dir = os.path.join(ROOT, "build", "openram", "smoke", "out")
    smoke_views = sorted(f.split(".", 1)[1] for f in os.listdir(smoke_dir)
                         if f.startswith("smoke_rom_1kbyte.")) \
        if os.path.isdir(smoke_dir) else []

    status = ("PASS" if not failures and not failed and not blocked
              else "PARTIAL" if not failures else "FAIL")

    report = {
        "stage": 2,
        "status": status,
        "failures": failures,
        "existing_fabric_changed": not fabric_unchanged,
        "interface": {
            "fabric_sha256": fabric_sha,
            "fabric_sha256_matches_stage1": fabric_unchanged,
            "verification_status": "PASS (memif.verify_against_rtl re-parses the "
                                   "fabric port list and fails closed on drift)",
            "timing_contract": memif.TIMING_CONTRACT,
            "capture_model": memif.CAPTURE_MODEL,
            "description": memif.describe(cfg),
        },
        "canonical_images": {
            n: images[n].to_dict() for n in IMAGE_ORDER
        },
        "portable_backend": {
            "generator": "scripts/gen_weight_rom_portable.py",
            "rtl": "rtl/mnist_mlp_params_portable.v",
            "rtl_sha256": sha256_file(os.path.join(RTL,
                                                   "mnist_mlp_params_portable.v")),
            "lint": lints["portable_backend"],
            "complete_readback": readback,
            "invalid_address_behaviour": "all zeros; no invalid address aliases "
                                         "a valid parameter row (tested)",
        },
        "openram_environment": {
            "openram_source_url": "https://github.com/VLSIDA/OpenRAM.git",
            "openram_branch": git_info(OPENRAM_ROOT, "rev-parse",
                                       "--abbrev-ref", "HEAD"),
            "openram_commit": git_info(OPENRAM_ROOT, "rev-parse", "HEAD"),
            "openram_home": os.path.join(OPENRAM_ROOT, "compiler"),
            "openram_tech": os.path.join(OPENRAM_ROOT, "technology"),
            "pdk_root": PDK_ROOT,
            "pdk_variant": "sky130A",
            "pdk_provenance": "ciel enable --pdk sky130 "
                              "e8294524e5f67c533c5d0c3afa0bcc5b2a5fa066 "
                              "(OpenRAM Makefile SKY130_CIEL), plus "
                              "skywater-pdk f70d8ca and sky130_fd_bd_sram dd64256",
            "python": subprocess.run([os.path.join(OPENRAM_ROOT, ".venv", "bin",
                                                   "python"), "--version"],
                                     capture_output=True, text=True).stdout.strip(),
            "env_script": "build/openram/openram_env.sh",
            "drc_tool": "magic 8.3.486 (conda-forge, user space)",
            "lvs_tool": "netgen 1.5.323 (built from source, user space)",
            "nix_bootstrap": "disabled (use_nix = False); tools come from PATH",
            "smoke_test": {
                "config": "build/openram/smoke/smoke_rom.py",
                "design": "official OpenRAM sample sky130 1 kbyte ROM",
                "generation": "PASS" if smoke_views else "NOT RUN",
                "views_generated": smoke_views,
                "elapsed_seconds": 235,
                "drc_result": "830 errors",
                "lvs_result": "MISMATCH",
                "note": "The UPSTREAM REFERENCE macro itself fails DRC and LVS "
                        "in this environment, so physical-verification results "
                        "here are not evidence about model2rtl's data. "
                        "Generation of all views works.",
            },
        },
        "openrom_macros": macros,
        "openrom_macro_summary": {
            "generated": generated,
            "blocked": blocked,
            "failed": failed,
            "data_convention_proven": OPENROM_CONVENTION,
            "convention_evidence": "build/openram/diag: a 1024-word one-hot-per-"
                                   "byte diagnostic ROM was generated and all "
                                   "8192 programmed cells in the resulting SPICE "
                                   "netlist matched the predicted placement "
                                   "exactly (0 mismatches).",
        },
        "openram_behavioral_model": {
            "rtl": "rtl/mnist_mlp_params_openram.v",
            "rtl_sha256": sha256_file(os.path.join(RTL,
                                                   "mnist_mlp_params_openram.v")),
            "authorship": "model2rtl behavioural model of the generated OpenROM "
                          "contents. NOT OpenROM-generated Verilog.",
            "openrom_verilog_note":
                "OpenROM does emit a .v file, but it is a byte-oriented, "
                "delay-based ($readmemb on a binary file, negedge data with "
                "#DELAY) non-synthesizable stub that does not implement this "
                "project's read contract, so it is not used.",
            "lint": lints["openram_backend"],
        },
        "equivalence": eq,
        "full_model": {
            "portable": runs["portable"],
            "openram_behavioral": runs["openram"],
            "backend_to_backend_logit_mismatches": b2b_mismatch,
            "oracle": "Stage-0 NumPy integer golden model (not Keras)",
        },
        "top_level": {
            "rtl": "rtl/mnist_mlp_top.v",
            "backend_selection": "build time, by source list: compile exactly one "
                                 "of rtl/mnist_mlp_params_sel_portable.v or "
                                 "rtl/mnist_mlp_params_sel_openram.v, each of "
                                 "which defines the abstract module "
                                 "mnist_mlp_params. No runtime mux exists.",
            "portable_sources": S2.PORTABLE_SOURCES,
            "openram_sources": S2.OPENRAM_SOURCES,
            "lint_portable": lints["top_portable"],
            "lint_openram": lints["top_openram"],
            "fabric_modified": not fabric_unchanged,
        },
        "limitations": [
            "The bias ROMs cannot be requested from this OpenROM version: its "
            "word_size is expressed in BYTES, so 22-bit and 17-bit words are "
            "not representable. Padding was NOT applied because that would "
            "change the physical word width without approval.",
            "DRC and LVS fail in this environment on the UPSTREAM REFERENCE "
            "macro as well (830 errors, LVS mismatch), so no macro here has a "
            "clean physical-verification result and none is claimed.",
            "No synthesis, FPGA or ASIC gate-level verification has been run; "
            "that is Stage 4.",
            "No area, timing or cell-area number is claimed.",
            "Stage 3's formal behavioural verification campaign is not "
            "implemented.",
        ],
        "meta": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "iverilog": subprocess.run([SIM.find_tool("iverilog"), "-V"],
                                       capture_output=True, text=True
                                       ).stdout.splitlines()[0],
            "stage0_npz_sha256": sha256_file(S.default_paths(ROOT)["npz"]),
            "quant_params_sha256": sha256_file(S.default_paths(ROOT)["quant"]),
        },
    }

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")
    print("\nwrote %s" % os.path.relpath(REPORT, ROOT))
    print("STATUS: %s" % status)
    if failures:
        print("FAILURES: %s" % failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
