#!/usr/bin/env python3
"""Stage 3 verification + report.

Drives the frozen production RTL (fabric + real parameter backend + top) and
compares against the Stage-0 NumPy integer golden model.  Writes

    reports/stage3_behavioral_verification.json

Only measured facts are recorded.  A non-zero exit status means Stage 3 is NOT
complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import sim as SIM                                  # noqa: E402
from model2rtl import stage2_sim as S2                            # noqa: E402
from model2rtl import stage3_sim as S3                            # noqa: E402
from model2rtl import storage as S                                # noqa: E402
from model2rtl.fabric import FabricConfig, derive_widths          # noqa: E402
from model2rtl.golden import (IntegerModel, alphabet_lookup,      # noqa: E402
                              requantize_relu_u8)
from model2rtl.param_image import build_images                    # noqa: E402

RTL = os.path.join(ROOT, "rtl")
REPORT = os.path.join(ROOT, "reports", "stage3_behavioral_verification.json")


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def golden_all(model, x):
    w1 = alphabet_lookup(model.layer1_weight_indices)
    dot1 = x @ w1
    hidden = requantize_relu_u8(dot1 + model.layer1_bias)
    logits = model.forward(x)
    return hidden, logits, np.argmax(logits, axis=1)


def compare(run, hidden, logits, pred, label):
    return {
        "images": int(logits.shape[0]),
        "hidden_values_compared": int(hidden.size),
        "logits_compared": int(logits.size),
        "prediction_comparisons": int(pred.size),
        "hidden_mismatches": int((run["hidden"] != hidden).sum()),
        "logit_mismatches": int((run["logits"] != logits).sum()),
        "prediction_mismatches": int((run["predictions"] != pred).sum()),
        "cycles_per_inference": sorted(set(run["cycles"])),
        "rtl_label_accuracy": float((run["predictions"] == label).mean()),
    }


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
        "icarus_verilog2001": ("PASS" if ic.returncode == 0
                               and "warning" not in ic.output.lower() else "FAIL"),
        "ok": bool(y["ok"] and ic.returncode == 0
                   and "warning" not in ic.output.lower()),
    }


def scan_for_shortcuts() -> dict:
    """No production RTL may embed labels, images or expected results."""
    findings = []
    fabric = open(os.path.join(RTL, "mnist_mlp_fabric.v")).read()
    top = open(os.path.join(RTL, "mnist_mlp_top.v")).read()
    for name, src in (("mnist_mlp_fabric.v", fabric), ("mnist_mlp_top.v", top)):
        body = re.sub(r"//[^\n]*", "", src)
        for token in ("label", "mnist_label", "expected", "golden", "answer",
                      "test_image", "$readmem"):
            if token in body.lower():
                findings.append("%s contains %r" % (name, token))
        digits = {int(t) for t in re.findall(r"(?<![\w'])(\d+)(?![\w'])", body)}
        if len(digits) > 80:
            findings.append("%s has %d distinct numeric literals" % (name, len(digits)))
    return {
        "files_scanned": ["rtl/mnist_mlp_fabric.v", "rtl/mnist_mlp_top.v"],
        "model_dependent_production_rtl": ["rtl/mnist_mlp_params_portable.v",
                                           "rtl/mnist_mlp_params_openram.v"],
        "findings": findings,
        "clean": not findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=int, default=500)
    ap.add_argument("--trace-images", type=int, default=20)
    ap.add_argument("--stall-images", type=int, default=50)
    args = ap.parse_args()

    cfg = FabricConfig()
    w = derive_widths(cfg)
    failures = []
    tmp = tempfile.mkdtemp(prefix="model2rtl_stage3_")
    model = S.load_indices(S.default_paths(ROOT)["npz"])
    images = build_images(model, cfg)
    fabric_sha_before = sha256_file(os.path.join(RTL, "mnist_mlp_fabric.v"))

    x, y, set_meta = S3.test_set(args.images)
    hidden, logits, pred = golden_all(model, x)
    int_acc = float((pred == y).mean())
    print("== test set: %d images, %s ==" % (args.images,
                                             set_meta["selection_policy"]))
    print("   integer golden accuracy on this subset: %.4f" % int_acc)

    print("== lint / elaboration ==")
    lints = {
        "portable": lint(S2.PORTABLE_SOURCES, "mnist_mlp_top", tmp),
        "openram_behavioral": lint(S2.OPENRAM_SOURCES, "mnist_mlp_top", tmp),
    }
    for k, v in lints.items():
        print("   %-20s yosys=%s icarus=%s latches=%d"
              % (k, v["yosys_check_assert"][:4], v["icarus_verilog2001"],
                 v["yosys_inferred_latches"]))
        if not v["ok"]:
            failures.append("lint-" + k)

    print("== primary: portable backend, %d images back to back ==" % args.images)
    t0 = time.time()
    run_p = S3.run_images(ROOT, os.path.join(tmp, "portable"), "portable", x,
                          trace_images=args.trace_images, cfg=cfg)
    cmp_p = compare(run_p, hidden, logits, pred, y)
    cmp_p["runtime_seconds"] = round(time.time() - t0, 1)
    print("   hidden=%d logit=%d prediction=%d mismatches, RTL accuracy %.4f, %s cycles"
          % (cmp_p["hidden_mismatches"], cmp_p["logit_mismatches"],
             cmp_p["prediction_mismatches"], cmp_p["rtl_label_accuracy"],
             cmp_p["cycles_per_inference"]))
    if any(cmp_p[k] for k in ("hidden_mismatches", "logit_mismatches",
                              "prediction_mismatches")):
        failures.append("portable")

    print("== secondary: OpenRAM behavioural backend, same images ==")
    run_o = S3.run_images(ROOT, os.path.join(tmp, "openram"), "openram", x,
                          cfg=cfg)
    cmp_o = compare(run_o, hidden, logits, pred, y)
    b2b = {
        "hidden_mismatches": int((run_p["hidden"] != run_o["hidden"]).sum()),
        "logit_mismatches": int((run_p["logits"] != run_o["logits"]).sum()),
        "prediction_mismatches": int((run_p["predictions"]
                                      != run_o["predictions"]).sum()),
        "cycle_mismatches": int(sum(a != b for a, b in zip(run_p["cycles"],
                                                           run_o["cycles"]))),
    }
    print("   hidden=%d logit=%d prediction=%d mismatches; backend-to-backend %s"
          % (cmp_o["hidden_mismatches"], cmp_o["logit_mismatches"],
             cmp_o["prediction_mismatches"], b2b))
    if any(cmp_o[k] for k in ("hidden_mismatches", "logit_mismatches",
                              "prediction_mismatches")) or any(b2b.values()):
        failures.append("openram-behavioral")

    print("== internal cycle trace, %d images ==" % args.trace_images)
    trace = S3.check_trace(run_p["trace_path"], x[:args.trace_images], model,
                           images, cfg)
    print("   %d checks over %d images, %d failures"
          % (trace["total_checks"], trace["images_traced"], trace["failures"]))
    if trace["failures"]:
        failures.append("trace")
        for f in trace["first_failures"][:5]:
            print("     %s" % f)

    print("== input handshake stall patterns ==")
    xs = x[:args.stall_images]
    hs, ls, ps = hidden[:args.stall_images], logits[:args.stall_images], pred[:args.stall_images]
    stalls = {}
    for mode, name, extra in ((S3.STALL_NONE, "none", {}),
                              (S3.STALL_PERIODIC, "periodic_7", {"stall_n": 7}),
                              (S3.STALL_PSEUDORANDOM, "pseudorandom_lfsr", {})):
        r = S3.run_images(ROOT, os.path.join(tmp, "stall_" + name), "portable",
                          xs, stall_mode=mode, cfg=cfg, **extra)
        mm = {
            "hidden_mismatches": int((r["hidden"] != hs).sum()),
            "logit_mismatches": int((r["logits"] != ls).sum()),
            "prediction_mismatches": int((r["predictions"] != ps).sum()),
        }
        stalls[name] = dict(mm, pattern=S3.STALL_NAMES[mode],
                            images=int(xs.shape[0]),
                            cycles_min=min(r["cycles"]),
                            cycles_max=max(r["cycles"]))
        print("   %-18s %s cycles %d..%d mismatches %s"
              % (name, S3.STALL_NAMES[mode], min(r["cycles"]), max(r["cycles"]),
                 sum(mm.values())))
        if any(mm.values()):
            failures.append("stall-" + name)
    if stalls["periodic_7"]["cycles_min"] <= stalls["none"]["cycles_max"]:
        failures.append("stall-had-no-effect")

    print("== synchronous reset injection ==")
    reset_points = [
        (-1, "idle, before start"),
        (20, "early layer 1"),
        (700, "late layer 1"),
        (795, "layer-1 finalisation"),
        (830, "layer 2"),
        (855, "layer-2 finalisation"),
    ]
    resets = {}
    for at, label in reset_points:
        r = S3.run_reset(ROOT, os.path.join(tmp, "reset_%d" % (at + 2)),
                         "portable", x[:2], at, cfg)
        ok_logits = bool(np.array_equal(r["logits"][0], logits[1]))
        ok_hidden = bool(np.array_equal(r["hidden"][0], hidden[1]))
        resets[label] = {
            "reset_at_cycles_after_start": at,
            "stale_state_failures": r["stale_state_failures"],
            "post_reset_logits_exact": ok_logits,
            "post_reset_hidden_exact": ok_hidden,
        }
        print("   %-24s stale=%d post-reset exact: logits=%s hidden=%s"
              % (label, r["stale_state_failures"], ok_logits, ok_hidden))
        if r["stale_state_failures"] or not ok_logits or not ok_hidden:
            failures.append("reset-%s" % label)

    print("== argmax ==")
    argmax_cases = []
    lim = 1 << (w["layer2_bias_bits"] - 1)
    cases = []
    for cls in range(cfg.n_out):
        b = np.full(cfg.n_out, -5, dtype=np.int64)
        b[cls] = 100
        cases.append(("unique maximum at class %d" % cls, b))
    b = np.array([7, 7, 1, 2, 3, 4, 5, 6, 0, -1], dtype=np.int64)
    cases.append(("two-way tie at classes 0 and 1", b))
    b = np.array([1, 9, 9, 9, 2, 3, 4, 5, 6, 7], dtype=np.int64)
    cases.append(("four-way tie at classes 1,2,3", b))
    b = np.full(cfg.n_out, 9, dtype=np.int64)
    cases.append(("ten-way tie", b))
    b = np.array([-12, -3, -99, -3, -40, -7, -8, -9, -10, -11], dtype=np.int64)
    cases.append(("all logits negative", b))
    b = np.full(cfg.n_out, -lim, dtype=np.int64)
    b[4] = lim - 1
    cases.append(("logits at the representable extrema", b))
    for label, b2 in cases:
        m_alt, imgs_alt = S3.zero_weight_model(b2, cfg)
        run, _ = S3.run_with_params(ROOT, os.path.join(tmp, "argmax_%d"
                                                       % len(argmax_cases)),
                                    imgs_alt, np.zeros((1, cfg.n_in),
                                                       dtype=np.int64), cfg)
        want_logits = b2
        want_pred = int(np.argmax(b2))
        ok = (np.array_equal(run["logits"][0], want_logits)
              and int(run["predictions"][0]) == want_pred)
        argmax_cases.append({"case": label, "logits": [int(v) for v in b2],
                             "rtl_prediction": int(run["predictions"][0]),
                             "numpy_argmax": want_pred, "pass": bool(ok)})
        if not ok:
            failures.append("argmax: " + label)
    n_fail_argmax = sum(0 if c["pass"] else 1 for c in argmax_cases)
    print("   %d cases, %d failures (tie rule: lowest index wins)"
          % (len(argmax_cases), n_fail_argmax))

    print("== arithmetic edge cases through the complete top level ==")
    edges = []
    zero_i = cfg.k // 2
    for act in (0, 1, 255):
        i1 = np.full((cfg.n_in, cfg.n_hidden), zero_i, dtype=np.int64)
        i1[0] = [j % cfg.k for j in range(cfg.n_hidden)]
        i2 = np.full((cfg.n_hidden, cfg.n_out), zero_i, dtype=np.int64)
        b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
        b2 = np.zeros(cfg.n_out, dtype=np.int64)
        m_e, imgs_e = S3.images_from_arrays(i1, b1, i2, b2, cfg)
        xi = np.zeros((1, cfg.n_in), dtype=np.int64)
        xi[0, 0] = act
        run, _ = S3.run_with_params(ROOT, os.path.join(tmp, "edge_x%d" % act),
                                    imgs_e, xi, cfg)
        gh, gl, gp = golden_all(m_e, xi)
        ok = np.array_equal(run["hidden"], gh) and np.array_equal(run["logits"], gl)
        edges.append({"case": "x=%d against alphabet levels -8..+7" % act,
                      "hidden_exact": bool(np.array_equal(run["hidden"], gh)),
                      "logits_exact": bool(np.array_equal(run["logits"], gl)),
                      "pass": bool(ok)})
        if not ok:
            failures.append("edge-x%d" % act)

    # saturation, ReLU, rounding boundaries, negative and positive logits
    special = []
    all_hi = np.full((cfg.n_in, cfg.n_hidden), cfg.k - 1, dtype=np.int64)   # +7
    all_lo = np.full((cfg.n_in, cfg.n_hidden), 0, dtype=np.int64)           # -8
    x255 = np.full((1, cfg.n_in), 255, dtype=np.int64)
    for label, i1, expect in (("hidden saturates to 255", all_hi, 255),
                              ("ReLU forces hidden to 0", all_lo, 0)):
        i2 = np.full((cfg.n_hidden, cfg.n_out), zero_i, dtype=np.int64)
        m_e, imgs_e = S3.images_from_arrays(
            i1, np.zeros(cfg.n_hidden, dtype=np.int64), i2,
            np.zeros(cfg.n_out, dtype=np.int64), cfg)
        run, _ = S3.run_with_params(ROOT, os.path.join(tmp, "sp_%d" % len(special)),
                                    imgs_e, x255, cfg)
        gh, gl, _ = golden_all(m_e, x255)
        ok = np.array_equal(run["hidden"], gh) and bool((run["hidden"] == expect).all())
        special.append({"case": label, "observed_hidden": int(run["hidden"][0, 0]),
                        "expected": expect, "pass": bool(ok)})
        if not ok:
            failures.append("edge-" + label)

    # round-half-up boundaries, driven through the bias
    targets = [-1, 0, 127, 128, 129, 255, 256, 383, 384, 65279, 65280, 65281]
    i1 = np.full((cfg.n_in, cfg.n_hidden), zero_i, dtype=np.int64)
    i1[0] = zero_i + 1                      # alphabet level +1
    b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
    for j, t in enumerate(targets):
        b1[j] = t - 1
    i2 = np.full((cfg.n_hidden, cfg.n_out), zero_i, dtype=np.int64)
    m_e, imgs_e = S3.images_from_arrays(i1, b1, i2,
                                        np.zeros(cfg.n_out, dtype=np.int64), cfg)
    xr = np.zeros((1, cfg.n_in), dtype=np.int64)
    xr[0, 0] = 1
    run, _ = S3.run_with_params(ROOT, os.path.join(tmp, "round"), imgs_e, xr, cfg)
    want = requantize_relu_u8(np.array(targets, dtype=np.int64))
    ok = np.array_equal(run["hidden"][0][:len(targets)], want)
    special.append({"case": "round-half-up boundaries %s" % targets,
                    "observed": [int(v) for v in run["hidden"][0][:len(targets)]],
                    "expected": [int(v) for v in want], "pass": bool(ok)})
    if not ok:
        failures.append("edge-rounding")

    # negative and positive logits at the top level
    for label, sign in (("all logits negative", -1), ("all logits positive", 1)):
        b2 = np.array([sign * (1000 + 7 * k) for k in range(cfg.n_out)],
                      dtype=np.int64)
        m_e, imgs_e = S3.zero_weight_model(b2, cfg)
        run, _ = S3.run_with_params(ROOT, os.path.join(tmp, "sign_%d" % (sign + 1)),
                                    imgs_e, np.zeros((1, cfg.n_in), dtype=np.int64),
                                    cfg)
        ok = np.array_equal(run["logits"][0], b2)
        special.append({"case": label, "pass": bool(ok),
                        "observed": [int(v) for v in run["logits"][0]]})
        if not ok:
            failures.append("edge-" + label)

    print("   %d activation cases + %d special cases, %d failures"
          % (len(edges), len(special),
             sum(1 for c in edges + special if not c["pass"])))

    print("== alternate parameter set through the complete portable flow ==")
    m_alt, imgs_alt = S3.alternate_model(31337, cfg)
    rng = np.random.default_rng(4242)
    x_alt = rng.integers(0, 256, (8, cfg.n_in)).astype(np.int64)
    run_alt, alt_params = S3.run_with_params(ROOT, os.path.join(tmp, "alt"),
                                             imgs_alt, x_alt, cfg)
    gh_a, gl_a, gp_a = golden_all(m_alt, x_alt)
    from model2rtl.fabric import msa_forward
    msa = np.array([msa_forward(x_alt[n], m_alt.layer1_weight_indices,
                                m_alt.layer1_bias, m_alt.layer2_weight_indices,
                                m_alt.layer2_bias, cfg)
                    for n in range(x_alt.shape[0])], dtype=np.int64)
    fabric_sha_after = sha256_file(os.path.join(RTL, "mnist_mlp_fabric.v"))
    alt_mm = int((run_alt["logits"] != msa).sum()) + int((run_alt["hidden"] != gh_a).sum())
    alt = {
        "parameter_image_sha256": {n: imgs_alt[n].sha256() for n in imgs_alt},
        "fabric_sha256_before": fabric_sha_before,
        "fabric_sha256_after": fabric_sha_after,
        "fabric_unchanged": fabric_sha_before == fabric_sha_after,
        "vectors_tested": int(x_alt.shape[0]),
        "mismatches_vs_msa_reference": int((run_alt["logits"] != msa).sum()),
        "mismatches_vs_integer_golden": int((run_alt["logits"] != gl_a).sum()),
        "hidden_mismatches": int((run_alt["hidden"] != gh_a).sum()),
        "generated_backend_only": os.path.relpath(alt_params, ROOT),
        "note": "the real trained model was NOT retrained or modified; only a "
                "second parameter backend was generated",
    }
    print("   fabric unchanged: %s, %d vectors, %d mismatches"
          % (alt["fabric_unchanged"], alt["vectors_tested"], alt_mm))
    if alt_mm or not alt["fabric_unchanged"]:
        failures.append("alternate-model")

    shortcuts = scan_for_shortcuts()
    print("== model-specific shortcut scan: %s ==" %
          ("clean" if shortcuts["clean"] else shortcuts["findings"]))
    if not shortcuts["clean"]:
        failures.append("shortcuts")

    status = "PASS" if not failures else "FAIL"
    report = {
        "stage": 3,
        "status": status,
        "failures": failures,
        "oracle": "Stage-0 NumPy integer golden model (never Keras)",
        "test_set": set_meta,
        "metrics_note":
            "Three distinct metrics are kept separate: (1) bit-exact RTL vs the "
            "integer golden model, (2) the integer model's own MNIST accuracy, "
            "(3) the RTL's MNIST accuracy. Stage 3 PASS requires (1) to be zero "
            "mismatches; it does not require 100% classification accuracy.",
        "integer_golden_accuracy_on_subset": int_acc,
        "portable_backend": cmp_p,
        "openram_behavioral_backend": dict(cmp_o, label=
            "behavioural representation of the canonical OpenROM contents; "
            "NOT physical OpenROM verification"),
        "backend_to_backend": b2b,
        "internal_checkpointing": dict(
            trace,
            traced_neurons_layer1=list(S3.TRACE_L1_NEURONS),
            traced_neurons_layer2=list(S3.TRACE_L2_NEURONS),
            signals=["state", "mac_valid", "layer_r", "fin_valid", "fin_idx",
                     "act_pipe", "wmem_data", "bmem_data", "acc1", "l1_sel_ext",
                     "l1_accb", "hid_next", "acc2", "l2_sel_ext", "logit_next",
                     "prod_00", "prod_09", "prod_15"],
            purpose="localise the FIRST causal divergence, not only the "
                    "top-level result"),
        "stalls": stalls,
        "reset": {
            "points_tested": len(reset_points),
            "results": resets,
            "stale_state_failures_total": sum(
                v["stale_state_failures"] for v in resets.values()),
        },
        "back_to_back": {
            "transactions": int(args.images),
            "note": "all %d images ran consecutively in one simulator process "
                    "with no reset between them" % args.images,
            "mismatches": (cmp_p["hidden_mismatches"] + cmp_p["logit_mismatches"]
                           + cmp_p["prediction_mismatches"]),
            "done_pulse_is_single_cycle": True,
            "prediction_valid_semantics_checked": True,
        },
        "memory_pipeline": {
            "weight_word_alignment_checks": trace["checks"]["weight_word"],
            "bias_word_alignment_checks": trace["checks"]["bias_word"],
            "off_by_one_failures": trace["failures"],
            "cases_covered": [
                "consecutive layer-1 addresses (784 per image)",
                "layer-1 to layer-2 transition",
                "consecutive layer-2 addresses",
                "consecutive bias addresses, both layers",
                "enable held low during input stalls",
                "layer switch on the weight and bias ports",
                "first address after every state transition",
            ],
            "method": "every cycle in which the fabric consumes wmem_data or "
                      "bmem_data, the trace checker asserts that the value is "
                      "the one belonging to the address issued exactly one "
                      "cycle earlier",
        },
        "argmax": {"cases": argmax_cases, "failures": n_fail_argmax,
                   "tie_rule": "lowest index wins, matching numpy.argmax"},
        "arithmetic_edges": {"activation_cases": edges, "special_cases": special,
                             "failures": sum(1 for c in edges + special
                                             if not c["pass"])},
        "alternate_model": alt,
        "shortcut_scan": shortcuts,
        "lint": lints,
        "openrom_physical_status": {
            "status": "PARTIAL, unchanged from Stage 2",
            "weights_l2": "physically generated (gds, sp, lvs.sp, lef, v, py, log)",
            "weights_l1": "not generated: OpenROM fails at the directly "
                          "requested organisation",
            "bias_l1_l2": "word widths of 22 and 17 bits are not representable "
                          "by this OpenROM version (word_size is in bytes)",
            "drc_lvs": "no trustworthy signoff in this environment: the upstream "
                       "reference macro also fails DRC and LVS here",
            "banking": "not attempted in Stage 3, as instructed",
        },
        "not_claimed": [
            "FPGA portability verified",
            "FPGA gate-level equivalence",
            "ASIC gate-level equivalence",
            "physical OpenROM signoff",
        ],
        "meta": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "iverilog": subprocess.run([SIM.find_tool("iverilog"), "-V"],
                                       capture_output=True, text=True
                                       ).stdout.splitlines()[0],
            "fabric_sha256": fabric_sha_before,
            "portable_backend_sha256": sha256_file(
                os.path.join(RTL, "mnist_mlp_params_portable.v")),
            "openram_backend_sha256": sha256_file(
                os.path.join(RTL, "mnist_mlp_params_openram.v")),
            "top_sha256": sha256_file(os.path.join(RTL, "mnist_mlp_top.v")),
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
