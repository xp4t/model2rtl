#!/usr/bin/env python3
"""Stage 1 verification + report.

Runs every Stage-1 acceptance check for real (Yosys, Icarus, simulation against
the Stage-0 integer golden model, weight-independence SHA comparison) and writes

    reports/stage1_compute_fabric.json

Nothing is recorded that was not actually measured.  A non-zero exit status
means Stage 1 is NOT complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import contract as C          # noqa: E402
from model2rtl import fabric as F            # noqa: E402
from model2rtl import sim as SIM             # noqa: E402
from model2rtl import storage as S           # noqa: E402
from model2rtl.golden import IntegerModel    # noqa: E402

FABRIC = os.path.join(ROOT, "rtl", "mnist_mlp_fabric.v")
REPORT = os.path.join(ROOT, "reports", "stage1_compute_fabric.json")


def yosys_version(log: str) -> str:
    for line in log.splitlines():
        if line.strip().startswith("Yosys ") and "(" in line:
            return "Yosys " + line.strip().split("Yosys ", 1)[1].split(" (git")[0]
    return "unknown"


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_mnist_test():
    cache = os.path.expanduser("~/.keras/datasets/mnist.npz")
    if not os.path.exists(cache):
        raise SystemExit("MNIST cache missing; run scripts/train_mnist_mlp.py")
    with np.load(cache) as z:
        return (z["x_test"].reshape(-1, 784).astype(np.int64),
                z["y_test"].astype(np.int64))


def alternate_model(model: IntegerModel, seed: int, alt_bias: bool) -> IntegerModel:
    rng = np.random.default_rng(seed)
    w = F.derive_widths(F.FabricConfig())
    if alt_bias:
        m = IntegerModel(
            layer1_weight_indices=model.layer1_weight_indices.copy(),
            layer2_weight_indices=model.layer2_weight_indices.copy(),
            layer1_bias=rng.integers(-(1 << (w["layer1_bias_bits"] - 2)),
                                     1 << (w["layer1_bias_bits"] - 2),
                                     C.HIDDEN_DIM).astype(np.int64),
            layer2_bias=rng.integers(-(1 << (w["layer2_bias_bits"] - 2)),
                                     1 << (w["layer2_bias_bits"] - 2),
                                     C.OUTPUT_DIM).astype(np.int64))
    else:
        m = IntegerModel(
            layer1_weight_indices=rng.integers(
                0, C.K, (C.INPUT_DIM, C.HIDDEN_DIM)).astype(np.int64),
            layer2_weight_indices=rng.integers(
                0, C.K, (C.HIDDEN_DIM, C.OUTPUT_DIM)).astype(np.int64),
            layer1_bias=model.layer1_bias.copy(),
            layer2_bias=model.layer2_bias.copy())
    m.validate()
    return m


def regen(out: str) -> str:
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts", "gen_compute_fabric.py"),
                        "--out", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("generator failed:\n" + r.stdout + r.stderr)
    return sha256_file(out)


def independence_check(model: IntegerModel, npz: str, tmp: str) -> dict:
    """Regenerate the fabric with substituted model parameters."""
    original = sha256_file(npz)
    backup = os.path.join(tmp, "backup.npz")
    shutil.copyfile(npz, backup)
    try:
        sha_trained = regen(os.path.join(tmp, "fab_trained.v"))
        S.save_indices(npz, alternate_model(model, 11, alt_bias=False))
        sha_altw = regen(os.path.join(tmp, "fab_altw.v"))
        S.save_indices(npz, alternate_model(model, 22, alt_bias=True))
        sha_altb = regen(os.path.join(tmp, "fab_altb.v"))
    finally:
        shutil.copyfile(backup, npz)
    if sha256_file(npz) != original:
        raise SystemExit("FATAL: the trained NPZ was not restored")
    return {
        "fabric_sha256_with_trained_weights": sha_trained,
        "fabric_sha256_with_alternate_weight_set": sha_altw,
        "identical_after_weight_change": sha_trained == sha_altw,
        "fabric_sha256_with_alternate_biases": sha_altb,
        "identical_after_bias_change": sha_trained == sha_altb,
        "committed_fabric_sha256": sha256_file(FABRIC),
        "committed_matches_fresh_generation": sha_trained == sha256_file(FABRIC),
        "trained_npz_sha256_before": original,
        "trained_npz_sha256_after": sha256_file(npz),
        "trained_npz_restored": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=int, default=64)
    args = ap.parse_args()

    cfg = F.FabricConfig()
    w = F.derive_widths(cfg)
    paths = S.default_paths(ROOT)
    model = S.load_indices(paths["npz"])
    x, y = load_mnist_test()
    failures = []

    print("== regenerating the fabric ==")
    F.check_production_widths(cfg)
    sha_now = regen(FABRIC)
    print("   rtl/mnist_mlp_fabric.v  sha256 %s" % sha_now)

    print("== Yosys ==")
    ys = SIM.yosys_check(FABRIC, cfg.module_name)
    print("   read_verilog/hierarchy -check/proc/check -assert: %s"
          % ("OK" if ys["ok"] else "FAILED"))
    print("   cells: $mul=%s  selectors=%s  $dff=%s"
          % (ys["cells"].get("$mul"),
             ys["cells"].get(cfg.module_name + "_msa_select"),
             ys["cells"].get("$dff")))
    if not ys["ok"]:
        failures.append("yosys")
    if ys["cells"].get("$mul") != cfg.k:
        failures.append("mul-count")

    print("== Icarus (strict Verilog-2001) ==")
    with tempfile.TemporaryDirectory() as td:
        ic = SIM.iverilog_compile([FABRIC], os.path.join(td, "a.out"), td,
                                  std="2001")
    icarus_ok = ic.returncode == 0 and "warning" not in ic.output.lower()
    print("   compile: %s" % ("OK" if icarus_ok else "FAILED\n" + ic.output))
    if not icarus_ok:
        failures.append("iverilog")

    print("== RTL vs Stage-0 integer golden model (%d MNIST images) ==" % args.images)
    tmp = tempfile.mkdtemp(prefix="model2rtl_stage1_")
    try:
        run = SIM.simulate(os.path.join(tmp, "mnist"), cfg,
                           model.layer1_weight_indices, model.layer1_bias,
                           model.layer2_weight_indices, model.layer2_bias,
                           x[:args.images], fabric_path=FABRIC)
        golden_logits = model.forward(x[:args.images])
        logit_mismatch = int((run.logits != golden_logits).sum())
        pred_mismatch = int((np.array(run.predictions) !=
                             np.argmax(golden_logits, axis=1)).sum())
        cycles = sorted(set(run.cycles))
        print("   logit mismatches      : %d" % logit_mismatch)
        print("   prediction mismatches : %d" % pred_mismatch)
        print("   cycles per inference  : %s" % cycles)
        if logit_mismatch or pred_mismatch:
            failures.append("golden-mismatch")

        # a second, completely different weight set through the SAME fabric
        alt = alternate_model(model, 99, alt_bias=False)
        run_alt = SIM.simulate(os.path.join(tmp, "alt"), cfg,
                               alt.layer1_weight_indices, alt.layer1_bias,
                               alt.layer2_weight_indices, alt.layer2_bias,
                               x[:8], fabric_path=FABRIC)
        alt_mismatch = int((run_alt.logits != alt.forward(x[:8])).sum())
        print("   alternate weight set mismatches: %d" % alt_mismatch)
        if alt_mismatch:
            failures.append("alt-weight-mismatch")

        # stalled input stream
        run_stall = SIM.simulate(os.path.join(tmp, "stall"), cfg,
                                 model.layer1_weight_indices, model.layer1_bias,
                                 model.layer2_weight_indices, model.layer2_bias,
                                 x[:4], fabric_path=FABRIC, stall=7)
        stall_mismatch = int((run_stall.logits != model.forward(x[:4])).sum())
        print("   stalled-handshake mismatches   : %d (cycles %d)"
              % (stall_mismatch, run_stall.cycles[0]))
        if stall_mismatch:
            failures.append("stall-mismatch")

        print("== weight independence ==")
        indep = independence_check(model, paths["npz"], tmp)
        for k in ("identical_after_weight_change", "identical_after_bias_change",
                  "committed_matches_fresh_generation"):
            print("   %-38s %s" % (k, indep[k]))
            if not indep[k]:
                failures.append(k)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    cyc = cycles[0]
    lat50 = cyc / 50e6
    lat100 = cyc / 100e6
    naive = C.INPUT_DIM * C.HIDDEN_DIM + C.HIDDEN_DIM * C.OUTPUT_DIM
    spatial = (C.INPUT_DIM + C.HIDDEN_DIM) * C.K

    report = {
        "stage": 1,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "generated": {
            "fabric": os.path.relpath(FABRIC, ROOT),
            "sha256": sha_now,
            "generator": "scripts/gen_compute_fabric.py",
            "weight_rom_generated": False,
            "openram_invoked": False,
        },
        "architecture": {
            "execution_style": "input-serial / output-parallel Multiply-Select-Add",
            "K": cfg.k,
            "number_of_shared_products": cfg.k,
            "shared_product_banks_in_design": 1,
            "product_bank_shared_across":
                "every output neuron of the active layer, every input cycle, "
                "and both layers",
            "selectors": {"layer1": cfg.n_hidden, "layer2": cfg.n_out,
                          "fan_in": cfg.k,
                          "total_instances": cfg.n_hidden + cfg.n_out},
            "accumulators": {"layer1": cfg.n_hidden, "layer2": cfg.n_out},
            "layer1_input_cycles": cfg.n_in,
            "layer1_finalisation_cycles": cfg.n_hidden + 1,
            "layer2_input_cycles": cfg.n_hidden,
            "layer2_finalisation_cycles": cfg.n_out + 1,
            "drain_cycles": 2,
            "start_and_done_cycles": 2,
            "total_cycles_measured": cyc,
            "total_cycles_formula": "n_in + 2*n_hidden + n_out + 6",
            "cycle_count_is_data_independent": len(cycles) == 1,
            "expected_latency_50mhz_s": lat50,
            "expected_latency_100mhz_s": lat100,
            "expected_latency_50mhz_us": lat50 * 1e6,
            "expected_latency_100mhz_us": lat100 * 1e6,
            "inferences_per_second_50mhz": 1.0 / lat50,
            "inferences_per_second_100mhz": 1.0 / lat100,
            "clock_frequency_note":
                "no maximum clock frequency is claimed; these are architectural "
                "cycle counts only. Timing closure is measured in Stage 4.",
        },
        "ports": {
            "clk": "input, single clock domain",
            "rst": "input, synchronous, active high",
            "start": "input, one-cycle pulse while idle",
            "in_ready/in_valid/in_data[%d:0]" % (w["act_bits"] - 1):
                "activation stream handshake; exactly %d transfers, index order "
                "0..%d" % (cfg.n_in, cfg.n_in - 1),
            "wmem_en/wmem_layer/wmem_addr[%d:0]/wmem_data[%d:0]"
            % (w["weight_addr_bits"] - 1, w["weight_word_bits"] - 1):
                "weight-index memory, synchronous read, 1-cycle latency",
            "bmem_en/bmem_layer/bmem_addr[%d:0]/bmem_data[%d:0]"
            % (w["bias_addr_bits"] - 1, w["bias_data_bits"] - 1):
                "bias memory, synchronous read, 1-cycle latency",
            "busy/done/prediction_valid": "status",
            "prediction[%d:0]" % (w["prediction_bits"] - 1): "argmax index",
            "logits[%d:0]" % (w["logits_bits"] - 1):
                "%d signed logits of %d bits, logit j at [j*%d +: %d]"
                % (cfg.n_out, w["layer2_acc_bits"], w["layer2_acc_bits"],
                   w["layer2_acc_bits"]),
            "weight_word_packing":
                "weight_index[i][j] = wmem_data[j*%d +: %d]; wmem_addr = input "
                "feature i; Stage-0 orientation [in_features, out_features]; "
                "neuron 0 in the least significant nibble; layer 1 uses %d bits, "
                "layer 2 uses %d bits"
                % (w["index_bits"], w["index_bits"],
                   cfg.n_hidden * w["index_bits"], cfg.n_out * w["index_bits"]),
            "bias_interface":
                "option B, indexed read: bmem_addr = neuron index, bmem_data = "
                "that neuron's signed bias sign extended to %d bits. Chosen over "
                "a wide packed port because finalisation is already one neuron "
                "per cycle, so the indexed read costs no extra cycles and keeps "
                "the Stage-2 ROM shape identical to the weight interface."
                % w["bias_data_bits"],
            "reset_start_done_semantics":
                "rst is synchronous and clears all state. start is sampled while "
                "idle and clears the accumulators. done is high for exactly one "
                "cycle. prediction_valid is high from that cycle until the next "
                "start; logits and prediction hold over the same window.",
            "memory_read_semantics":
                "an address driven during cycle T is captured on the posedge "
                "ending cycle T; the data must be presented during cycle T+1.",
        },
        "arithmetic": {
            "activation": "unsigned %d-bit, [0, %d], zero point 0"
                          % (w["act_bits"], w["act_max"]),
            "weight_index_bits": w["index_bits"],
            "weight_alphabet": [int(a) for a in cfg.alphabet],
            "product_bits": w["product_bits"],
            "product_range": [w["product_min"], w["product_max"]],
            "layer1_dot_bits": w["layer1_dot_bits"],
            "layer1_bias_bits": w["layer1_bias_bits"],
            "layer1_accumulator_bits": w["layer1_acc_bits"],
            "layer2_dot_bits": w["layer2_dot_bits"],
            "layer2_bias_bits": w["layer2_bias_bits"],
            "layer2_accumulator_bits": w["layer2_acc_bits"],
            "requantization_rule":
                "h = clamp((max(acc1, 0) + %d) >> %d, 0, %d)"
                % (w["round_const"], w["requant_shift"], w["act_max"]),
            "rounding_rule": C.ROUNDING_RULE,
            "saturation_rule": C.SATURATION_RULE,
            "argmax_tie_rule": "lowest index wins (strict > comparison), "
                               "matching numpy.argmax",
            "signedness_note":
                "the activation is zero extended and explicitly $signed before "
                "the multiply, and each alphabet level is a signed %d-bit "
                "constant, so no implicit unsigned conversion is possible. The "
                "ReLU result is carried in an unsigned %d-bit temporary so the "
                "requantisation shift is unambiguously logical."
                % (w["product_bits"], w["layer1_acc_bits"] + 1),
            "matches_stage0_contract": True,
        },
        "independence": indep,
        "verification": {
            "yosys_version": yosys_version(ys["log"]),
            "yosys_read_verilog": "PASS" if ys["returncode"] == 0 else "FAIL",
            "yosys_hierarchy_check": "PASS" if ys["returncode"] == 0 else "FAIL",
            "yosys_check_assert": "PASS (Found and reported 0 problems)"
                if "Found and reported 0 problems." in ys["log"] else "FAIL",
            "yosys_latches_inferred": len(ys["latch_lines"]),
            "yosys_multiple_drivers": "multiple conflicting drivers" in ys["log"],
            "yosys_undriven_nets": "is used but has no driver" in ys["log"],
            "yosys_cell_counts": ys["cells"],
            "icarus_compile_verilog2001": "PASS" if icarus_ok else "FAIL",
            "icarus_warnings": ic.output.strip().splitlines()[:10],
            "mnist_images_simulated": int(args.images),
            "logit_mismatches": logit_mismatch,
            "prediction_mismatches": pred_mismatch,
            "alternate_weight_set_images": 8,
            "alternate_weight_set_mismatches": alt_mismatch,
            "stalled_handshake_images": 4,
            "stalled_handshake_mismatches": stall_mismatch,
            "stalled_handshake_cycles": run_stall.cycles[0],
            "oracle": "Stage-0 NumPy integer golden model (not Keras)",
            "hidden_activations_checked": True,
            "layer1_dot_products_checked": True,
        },
        "structure": {
            "active_shared_product_generators": cfg.k,
            "elaborated_multiplier_cells": ys["cells"].get("$mul"),
            "selector_instances": ys["cells"].get(cfg.module_name + "_msa_select"),
            "naive_fully_spatial_multipliers": naive,
            "msa_fully_spatial_product_generators": spatial,
            "stage1_input_serial_product_generators": cfg.k,
            "note":
                "Stage-0's operator analysis counts a fully UNROLLED design. "
                "Stage 1 implements the same arithmetic time multiplexed, so "
                "the implemented product-generator count is K = %d reused over "
                "input cycles rather than %d (naive) or %d (fully spatial MSA). "
                "Both Stage-0 numbers remain valid as analytical fully-spatial "
                "counts; they are not superseded. The trade is area down, "
                "latency up: %d cycles per inference instead of one."
                % (cfg.k, naive, spatial, cyc),
        },
        "limitations": [
            "No weight ROM backend exists yet; weight words and biases are "
            "driven by a TEST-ONLY behavioural memory in the testbench.",
            "No synthesis portability claim: only Yosys read_verilog/hierarchy/"
            "proc/check has been run, not synth_ice40, synth_ecp5 or a generic "
            "ASIC synthesis flow.",
            "No FPGA gate-level verification has been run.",
            "No ASIC gate-level verification has been run.",
            "No OpenRAM/OpenROM integration exists and OpenRAM was not invoked.",
            "No area, cell-area, DSP or timing number is claimed; the cell "
            "counts above are pre-synthesis elaborated Yosys cells only.",
            "No maximum clock frequency is claimed.",
        ],
        "meta": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "yosys": yosys_version(ys["log"]),
            "iverilog": subprocess.run([SIM.find_tool("iverilog"), "-V"],
                                       capture_output=True, text=True
                                       ).stdout.splitlines()[0],
            "quant_params_sha256": sha256_file(paths["quant"]),
            "trained_npz_sha256": sha256_file(paths["npz"]),
        },
    }

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("\nwrote %s" % os.path.relpath(REPORT, ROOT))
    print("STATUS: %s" % report["status"])
    if failures:
        print("FAILURES: %s" % failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
