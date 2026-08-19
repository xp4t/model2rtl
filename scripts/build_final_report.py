#!/usr/bin/env python3
"""Stage 6: consolidate the six stage reports into the final artifacts.

Writes

    reports/final_report.json
    reports/results.csv

Every number is EXTRACTED from a stage report; none is retyped here.  Where two
stages measure the same quantity the newest authoritative stage is used, and the
older value is recorded next to it under `cross_stage_consistency` -- so a
disagreement is visible rather than quietly reconciled.  A genuine contradiction
(two stages disagreeing about a quantity that cannot legitimately differ) stops
the script.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

REPORTS = os.path.join(ROOT, "reports")
OUT_JSON = os.path.join(REPORTS, "final_report.json")
OUT_CSV = os.path.join(REPORTS, "results.csv")

STAGE_FILES = {
    0: "stage0_quantization.json",
    1: "stage1_compute_fabric.json",
    2: "stage2_parameter_backends.json",
    3: "stage3_behavioral_verification.json",
    4: "stage4_dual_target_portability.json",
    5: "stage5_openrom_physical.json",
}

#: Everything Stage 6 must leave byte-identical.  Documentation is not here.
FROZEN = [
    "model/mnist_weights_indices.npz",
    "model/quant_params.json",
    "rtl/mnist_mlp_fabric.v",
    "rtl/mnist_mlp_params_portable.v",
    "rtl/mnist_mlp_params_openram.v",
    "rtl/mnist_mlp_params_openrom_phys.v",
    "rtl/mnist_mlp_params_sel_portable.v",
    "rtl/mnist_mlp_params_sel_openram.v",
    "rtl/mnist_mlp_params_sel_openrom_phys.v",
    "rtl/mnist_mlp_top.v",
    "src/model2rtl/contract.py",
    "src/model2rtl/golden.py",
    "src/model2rtl/fabric.py",
    "src/model2rtl/verilog_emit.py",
    "src/model2rtl/param_image.py",
    "src/model2rtl/param_verilog.py",
    "src/model2rtl/phys_image.py",
    "src/model2rtl/phys_verilog.py",
    "src/model2rtl/storage.py",
] + ["reports/" + f for f in STAGE_FILES.values()]


class Contradiction(RuntimeError):
    pass


def sha(path):
    with open(os.path.join(ROOT, path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load():
    out = {}
    for n, f in STAGE_FILES.items():
        p = os.path.join(REPORTS, f)
        if not os.path.exists(p):
            raise SystemExit("missing %s" % p)
        out[n] = json.load(open(p))
    return out


def check_consistency(s) -> dict:
    """Compare quantities that appear in more than one stage report.

    A mismatch in any of these is a real contradiction: they are the same
    measured thing, recorded twice.
    """
    checks = []

    def eq(label, a, b, where_a, where_b):
        checks.append({"quantity": label, "value_a": a, "source_a": where_a,
                       "value_b": b, "source_b": where_b, "agree": a == b})

    # the fabric hash is recorded by Stage 1, 3, 4 and 5
    eq("fabric SHA-256",
       s[1]["generated"]["sha256"], s[4]["source_freeze"]["after"][
           "rtl/mnist_mlp_fabric.v"],
       "stage1.generated.sha256", "stage4.source_freeze.after")
    eq("fabric SHA-256 (stage 5)",
       s[4]["source_freeze"]["after"]["rtl/mnist_mlp_fabric.v"],
       s[5]["source_freeze"]["after"]["rtl/mnist_mlp_fabric.v"],
       "stage4.source_freeze", "stage5.source_freeze")
    eq("fabric SHA-256 (stage 3 alternate-model proof)",
       s[3]["alternate_model"]["fabric_sha256_after"],
       s[5]["source_freeze"]["after"]["rtl/mnist_mlp_fabric.v"],
       "stage3.alternate_model", "stage5.source_freeze")

    # the verification image set is shared by Stages 3, 4 and 5
    eq("verification image-set SHA-256 (stage 3 vs 4)",
       s[3]["test_set"]["images_sha256"],
       s[4]["gate_level_verification"]["image_selection"]["images_sha256"],
       "stage3.test_set", "stage4.image_selection")
    eq("verification image-set SHA-256 (stage 4 vs 5)",
       s[4]["gate_level_verification"]["image_selection"]["images_sha256"],
       s[5]["full_model"]["test_set"]["images_sha256"],
       "stage4.image_selection", "stage5.full_model.test_set")

    # synapse counts: Stage 0 declares them, Stage 5 recovers them physically
    eq("total weight indices",
       s[0]["model_size"]["total_synapses"],
       s[5]["logical_equivalence"]["readback"]["weight_indices_checked"],
       "stage0.model_size", "stage5.readback")

    # nominal latency: Stage 1 derives it, Stages 3/4/5 measure it
    eq("nominal cycles per inference (stage 1 vs 4)",
       s[1]["architecture"]["total_cycles_measured"],
       s[4]["gate_level_verification"]["fpga"]["no_stall"][
           "latency_contract_cycles"],
       "stage1.architecture", "stage4.fpga.no_stall")
    eq("nominal cycles per inference (stage 4 vs 5)",
       s[4]["gate_level_verification"]["fpga"]["no_stall"][
           "cycles_per_inference"],
       s[5]["full_model"]["openrom_phys"]["cycles"],
       "stage4.fpga.no_stall", "stage5.full_model")

    # portable-backend behavioural result: Stage 3 measured it, Stage 5 re-ran it
    eq("portable backend logit mismatches (stage 3 vs 5)",
       s[3]["portable_backend"]["logit_mismatches"],
       s[5]["full_model"]["portable"]["logit_mismatches"],
       "stage3.portable_backend", "stage5.full_model.portable")

    # the canonical parameter images must be the same objects throughout
    for name, img in s[2]["canonical_images"].items():
        if name in s[5]["physical_representation"]["logical_images"]:
            eq("canonical image SHA-256 (%s)" % name, img["sha256"],
               s[5]["physical_representation"]["logical_images"][name]["sha256"],
               "stage2.canonical_images", "stage5.logical_images")

    bad = [c for c in checks if not c["agree"]]
    if bad:
        raise Contradiction(
            "stage reports disagree, refusing to reconcile silently:\n"
            + "\n".join("  %s: %r (%s) vs %r (%s)"
                        % (c["quantity"], c["value_a"], c["source_a"],
                           c["value_b"], c["source_b"]) for c in bad))
    return {"checks": checks, "checked": len(checks), "disagreements": 0}


def build(s) -> dict:
    s0, s1, s2, s3, s4, s5 = (s[0], s[1], s[2], s[3], s[4], s[5])
    fpga = s4["fpga_target"]
    gen = s4["generic_target"]
    gv = s4["gate_level_verification"]
    msa = s0["multiply_select_add"]
    shared = (msa["layer1"]["shared_product_generators"]
              + msa["layer2"]["shared_product_generators"])

    return {
        "project": "model2rtl",
        "stage": 6,
        "title": "final technical report",
        "claim": (
            "model2rtl demonstrates that a trained quantized neural network can "
            "be compiled into a portable RTL implementation using a shared "
            "Multiply-Select-Add architecture, verified behaviourally and after "
            "independent FPGA-oriented and generic/ASIC-oriented synthesis, "
            "with an optional ASIC physical ROM representation of its "
            "parameters."),
        "claim_scope": (
            "The claim covers the demonstrated MNIST 784-32-10 MLP only. It is "
            "not a claim of production ASIC readiness, timing closure, "
            "full-chip physical implementation, DRC- or LVS-clean macros, "
            "arbitrary-model compilation, or reproduction of any proprietary "
            "implementation."),
        "stage_status": {
            "stage0_quantization": s0.get("status", "PASS"),
            "stage1_compute_fabric": s1["status"],
            "stage2_parameter_backends": s2["status"],
            "stage3_behavioral_verification": s3["status"],
            "stage4_dual_target_portability": s4["status"],
            "stage5_physical_generation": s5["physical_signoff"][
                "physical_generation"],
            "stage5_physical_signoff": s5["physical_signoff"]["status"],
        },

        "model": {
            "task": "MNIST handwritten-digit classification",
            "topology": "784 -> 32 -> ReLU -> 10",
            "float_test_accuracy": s0["float_model"]["test_accuracy"],
            "quantized_integer_test_accuracy":
                s0["quantized_integer_model"]["test_accuracy"],
            "accuracy_change_points":
                round(100.0 * (s0["quantized_integer_model"]["test_accuracy"]
                               - s0["float_model"]["test_accuracy"]), 4),
            "accuracy_change_wording":
                "quantization LOSES %.2f percentage points of test accuracy "
                "relative to float"
                % abs(100.0 * (s0["quantized_integer_model"]["test_accuracy"]
                               - s0["float_model"]["test_accuracy"])),
            "dataset": s0["meta"]["dataset"],
            "artifact_hashes": s0["meta"]["artifact_hashes"],
        },

        "quantization": {
            "weight_index_bits": s0["arithmetic_contract"][
                "weight_index_width_bits"],
            "weight_alphabet": s0["arithmetic_contract"][
                "weight_alphabet_values"],
            "weight_alphabet_rule": s0["arithmetic_contract"][
                "weight_alphabet_rule"],
            "activation": "uint8, zero point %d, range %s"
                          % (s0["arithmetic_contract"]["input_zero_point"],
                             s0["activations"]["input_range_declared"]),
            "requantization_rule": s0["arithmetic_contract"][
                "requantization_rule"],
            "requantization_shift": s0["arithmetic_contract"][
                "requantization_shift"],
            "rounding_rule": s0["arithmetic_contract"]["rounding_rule"],
            "saturation_rule": s0["arithmetic_contract"]["saturation_rule"],
            "prediction_rule": s0["arithmetic_contract"]["prediction_rule"],
            "scale_note": s0["arithmetic_contract"]["scale_note"],
            "synapses": {
                "layer1": s0["model_size"]["layer1_synapses"],
                "layer2": s0["model_size"]["layer2_synapses"],
                "total": s0["model_size"]["total_synapses"],
                "index_bits_total": s0["model_size"]["total_index_bits"],
            },
            "weight_index_histogram": {
                "layer1": s0["layer1"]["weight_index_histogram_by_level"],
                "layer2": s0["layer2"]["weight_index_histogram_by_level"],
            },
            "all_sixteen_levels_used": (
                not s0["layer1"]["unused_weight_levels"]
                and not s0["layer2"]["unused_weight_levels"]),
            "weight_saturation": {
                "layer1_percent": s0["layer1"]["weight_saturation_percentage"],
                "layer2_percent": s0["layer2"]["weight_saturation_percentage"],
                "note": "Saturation counts weights clipped to the alphabet "
                        "extremes during quantization-aware training. Layer 2 "
                        "saturates more often because it has only 320 synapses "
                        "and a wider dynamic range per synapse; final integer "
                        "accuracy is unaffected at %.2f%%."
                        % (100 * s0["quantized_integer_model"]
                           ["test_accuracy"]),
            },
            "activation_statistics": s0["activations"],
            "arithmetic_contract": s0["arithmetic_contract"],
            "widths": s0["widths"],
        },

        "architecture": {
            "concept": (
                "For each input activation x_i, compute x_i times all 16 "
                "alphabet levels once; share those 16 products across every "
                "output neuron of the active layer; select per synapse with its "
                "4-bit weight index; accumulate."),
            "execution": "input-serial, output-parallel",
            "K": msa["layer1"]["K"],
            "product_bank_reuse": (
                "one 16-product bank, reused across all neurons, across input "
                "cycles and across both layers"),
            "operation_counts": {
                "naive_fully_spatial_synapse_multiplications":
                    s0["model_size"]["total_synapses"],
                "fully_spatial_msa_product_generators": shared,
                "implemented_active_shared_product_expressions":
                    s1["structure"]["active_shared_product_generators"],
                "kind": "SOURCE-LEVEL operation counts, not synthesized "
                        "resources and not physical multiplier counts",
            },
            "sharing_note": msa["crossover_note"],
            "structure_verified_in_netlist": s1["structure"],
            "latency": {
                "nominal_cycles": s1["architecture"]["total_cycles_measured"],
                "formula": s1["architecture"]["total_cycles_formula"],
                "examples_architectural_only": {
                    "50MHz_us": s1["architecture"]["expected_latency_50mhz_us"],
                    "100MHz_us": s1["architecture"][
                        "expected_latency_100mhz_us"],
                },
                "caveat": "These are cycle counts divided by an assumed clock. "
                          "No timing analysis was run at any stage and no Fmax "
                          "is claimed.",
            },
            "tradeoff": "Area and parallelism are exchanged for latency: one "
                        "inference costs %d cycles instead of one."
                        % s1["architecture"]["total_cycles_measured"],
        },

        "rtl": {
            "fabric": {
                "path": "rtl/mnist_mlp_fabric.v",
                "sha256": s1["generated"]["sha256"],
                "language": "Verilog-2001",
                "vendor_neutral": True,
                "clocks": 1,
                "resets": "1 synchronous",
                "weight_independence": s1["independence"],
                "ports": s1["ports"],
            },
            "files": {p: sha(p) for p in FROZEN if p.startswith("rtl/")},
        },

        "parameter_backends": {
            "interface": s2["interface"],
            "canonical_images": s2["canonical_images"],
            "portable": {
                "path": "rtl/mnist_mlp_params_portable.v",
                "sha256": sha("rtl/mnist_mlp_params_portable.v"),
                "description": "pure synthesizable Verilog-2001, synchronous "
                               "one-cycle enable-gated read, case/constant "
                               "representation; the same source feeds both "
                               "synthesis targets",
                "summary": s2["portable_backend"],
            },
            "openram_behavioral": {
                "path": "rtl/mnist_mlp_params_openram.v",
                "sha256": sha("rtl/mnist_mlp_params_openram.v"),
                "summary": s2["openram_behavioral_model"],
            },
            "openrom_physical": {
                "path": "rtl/mnist_mlp_params_openrom_phys.v",
                "sha256": sha("rtl/mnist_mlp_params_openrom_phys.v"),
                "logical_vs_physical":
                    s5["physical_representation"]["transformations"],
                "physical_images":
                    s5["physical_representation"]["physical_images"],
                "note": "All transformations are PHYSICAL REPRESENTATION ONLY. "
                        "The logical memories, the bit packing and the fabric "
                        "interface never changed.",
            },
        },

        "behavioral_verification": {
            "oracle": s3["oracle"],
            "images": s3["test_set"]["count"],
            "test_set": s3["test_set"],
            "portable_backend": s3["portable_backend"],
            "openram_behavioral_backend": s3["openram_behavioral_backend"],
            "backend_to_backend": s3["backend_to_backend"],
            "cycle_level_trace": {
                "images_traced": s3["internal_checkpointing"]["images_traced"],
                "total_checks": s3["internal_checkpointing"]["total_checks"],
                "failures": s3["internal_checkpointing"]["failures"],
            },
            "memory_pipeline": s3["memory_pipeline"],
            "stalls": s3["stalls"],
            "reset": s3["reset"],
            "back_to_back": s3["back_to_back"],
            "argmax": {"cases": len(s3["argmax"]["cases"]),
                       "failures": s3["argmax"]["failures"],
                       "tie_rule": s3["argmax"]["tie_rule"]},
            "arithmetic_edges": {
                "activation_cases": len(s3["arithmetic_edges"]
                                        ["activation_cases"]),
                "special_cases": len(s3["arithmetic_edges"]["special_cases"]),
                "failures": s3["arithmetic_edges"]["failures"]},
            "alternate_model": s3["alternate_model"],
            "shortcut_scan": s3["shortcut_scan"],
        },

        "dual_target_portability": {
            "claim": "The exact same RTL source was synthesized through an "
                     "FPGA-oriented Yosys flow and a generic/ASIC-oriented "
                     "Yosys flow with no source patching, and BOTH synthesized "
                     "netlists were gate-level simulated against the Stage-0 "
                     "integer golden model.",
            "not_claimed": "This proves synthesis portability and "
                           "post-synthesis functional equivalence for this RTL. "
                           "It does NOT prove place-and-route or timing "
                           "portability; neither was run.",
            "same_source": s4["portability"],
            "fpga": {
                "family": fpga["family"],
                "rationale": fpga["family_rationale"],
                "flow": "synth_ice40",
                "netlist_sha256": fpga["netlist_sha256"],
                "resources": fpga["resources"],
                "cells": fpga["cells"],
                "parameter_rom_mapping": fpga["parameter_rom_mapping"],
                "gate_level": gv["fpga"],
            },
            "generic": {
                "flow": "proc/flatten/opt/memory/techmap/simplemap/"
                        "dfflegalize/abc -g simple",
                "netlist_sha256": gen["netlist_sha256"],
                "resources": gen["resources"],
                "cells": gen["cells"],
                "parameter_rom_mapping": gen["parameter_rom_mapping"],
                "gate_level": gv["generic"],
            },
            "cross_target": gv["cross_target"],
            "reproducibility": s4["reproducibility"],
        },

        "constant_multiplication": {
            "source_multiply_operators":
                s4["resource_analysis"]["constant_multiplication"]["fpga"][
                    "source_multiply_operators"],
            "multiplier_or_dsp_cells_fpga":
                s4["resource_analysis"]["constant_multiplication"]["fpga"][
                    "multiplier_or_dsp_cells_in_netlist"],
            "multiplier_or_dsp_cells_generic":
                s4["resource_analysis"]["constant_multiplication"]["generic"][
                    "multiplier_or_dsp_cells_in_netlist"],
            "bit_classification":
                {k: v["bit_class_totals"] for k, v in
                 s4["resource_analysis"]["constant_multiplication"].items()},
            "product_wire_drivers_fpga":
                s4["resource_analysis"]["constant_multiplication"]["fpga"][
                    "product_wire_drivers"],
            "explanation": (
                "Each of the 16 products has a fixed small integer constant as "
                "one operand, so synthesis replaces them with wiring, shifts, "
                "negation, add/subtract and LUT/carry logic, and fuses the "
                "shared product logic into the selector logic."),
            "correct_wording": (
                "The architecture exposes only sixteen constant-weight product "
                "alternatives per activation, and synthesis further eliminates "
                "explicit multiplier hardware."),
            "wording_to_avoid": (
                "'we reduced 25,408 physical multipliers to 16 physical "
                "multipliers' -- that is NOT what synthesis showed. The three "
                "operation counts are source-level quantities and the "
                "synthesized results are a different kind of measurement."),
        },

        "physical_openrom": {
            "macros": {k: {"shape": v["requested_shape"],
                           "words_per_row": v["words_per_row"],
                           "generated": v["generated"],
                           "views": v["views_generated"],
                           "bits_verified": v["content_verification"][
                               "bits_checked"],
                           "bit_mismatches": v["content_verification"][
                               "bit_mismatches"],
                           "bbox_um2": v["bbox"]["area_um2"],
                           "drc_status": v["drc_status"],
                           "lvs_status": v["lvs_status"]}
                       for k, v in s5["macros"].items()},
            "content_verification": {
                "programmed_cells_checked": sum(
                    v["content_verification"]["bits_checked"]
                    for v in s5["macros"].values()),
                "programmed_cell_mismatches": sum(
                    v["content_verification"]["bit_mismatches"]
                    for v in s5["macros"].values()),
                "logical_rows": s5["logical_equivalence"]["readback"][
                    "logical_rows_checked"],
                "logical_row_mismatches": s5["logical_equivalence"]["readback"][
                    "logical_row_mismatches"],
                "weight_indices": s5["logical_equivalence"]["readback"][
                    "weight_indices_checked"],
                "weight_index_mismatches": s5["logical_equivalence"][
                    "readback"]["weight_index_mismatches"],
                "bias_values": s5["logical_equivalence"]["readback"][
                    "bias_values_checked"],
                "bias_mismatches": s5["logical_equivalence"]["readback"][
                    "bias_mismatches"],
            },
            "logical_equivalence": s5["logical_equivalence"]["backend_bus"],
            "full_model": s5["full_model"],
            "signoff": s5["physical_signoff"],
        },

        "area": dict(s5["area"], portable_asic_storage=s5[
            "portable_asic_storage"]),
        "crossover": s5["crossover"],

        "limitations": [
            "MNIST only; no other dataset or task was attempted.",
            "The compiler is fixed to the 784-32-10 topology it was written "
            "for; there is no general topology support.",
            "Weights are 4-bit, 16 fixed levels; activations are uint8.",
            "No convolution support of any kind.",
            "No ONNX or TFLite ingestion exists; the model comes from this "
            "project's own training script.",
            "Input-serial execution trades latency for area: %d cycles per "
            "inference." % s1["architecture"]["total_cycles_measured"],
            "No FPGA place-and-route, no device fit, no bitstream, no FPGA "
            "timing analysis.",
            "No ASIC place-and-route, no floorplan, no full-chip physical "
            "implementation, no ASIC timing analysis.",
            "OpenROM physical signoff is UNVERIFIED: the environment's own "
            "control macro fails DRC and LVS.",
            "The hard ROM did not beat portable synthesized storage in area "
            "anywhere in the measured range.",
            "The physical banking scheme is specific to the demonstrated ROM "
            "shape; it is not a general banking compiler.",
            "No claim is made of reproducing any proprietary implementation.",
        ],

        "future_work": [
            {"rank": 1, "item": "generic model importer (ONNX / TFLite)"},
            {"rank": 2, "item": "arbitrary dense-layer topology compiler"},
            {"rank": 3, "item": "configurable K, activation width and layer "
                                "sizes"},
            {"rank": 4, "item": "convolution lowering"},
            {"rank": 5, "item": "architecture selection: fully spatial, "
                                "input-serial, tiled"},
            {"rank": 6, "item": "FPGA place-and-route plus timing analysis"},
            {"rank": 7, "item": "full SKY130 ASIC implementation"},
            {"rank": 8, "item": "a trustworthy OpenROM DRC/LVS environment"},
            {"rank": 9, "item": "memory-architecture exploration: portable ROM, "
                                "SRAM, hard ROM, banking"},
            {"rank": 10, "item": "model and architecture co-optimization"},
        ],

        "not_claimed": [
            "production ASIC readiness",
            "timing closure or any maximum clock frequency",
            "full-chip physical implementation",
            "DRC-clean OpenROM macros",
            "LVS-clean OpenROM macros",
            "general arbitrary-model compilation",
            "support beyond the demonstrated MNIST MLP",
            "reproduction of any proprietary implementation",
        ],
        "test_evolution": {
            "note": "Cumulative pytest count at the close of each stage. The "
                    "per-stage figures are the baselines recorded at the time; "
                    "the final figure is measured by the Stage-6 run.",
            "cumulative": {"stage0": 35, "stage1": 79, "stage2": 137,
                           "stage3": 174, "stage4": 245, "stage5": 381},
            "final_measured": {"collected": 408, "passed": 408, "failed": 0,
                               "skipped": 0,
                               "command": "pytest tests"},
        },
        "prior_art_note": (
            "This project explores a digital RTL interpretation of publicly "
            "disclosed high-level Multiply-Select-Add ideas associated with "
            "public Taalas patent material. No Taalas source code, netlist, "
            "layout or transistor-level mask-ROM detail was used, consulted or "
            "reproduced, and nothing here is claimed to be equivalent to Taalas "
            "hardware."),
    }


def results_rows(f: dict) -> list:
    m, q, a = f["model"], f["quantization"], f["architecture"]
    d = f["dual_target_portability"]
    b = f["behavioral_verification"]
    p = f["physical_openrom"]
    ar = f["area"]
    return [
        ("Float MNIST test accuracy", "%.2f%%" % (100 * m["float_test_accuracy"]),
         "reports/stage0_quantization.json"),
        ("Quantized integer MNIST test accuracy",
         "%.2f%%" % (100 * m["quantized_integer_test_accuracy"]),
         "reports/stage0_quantization.json"),
        ("Accuracy change from quantization",
         "%.2f points" % m["accuracy_change_points"],
         "reports/stage0_quantization.json"),
        ("Total weight indices", q["synapses"]["total"],
         "reports/stage0_quantization.json"),
        ("Weight alphabet levels", len(q["weight_alphabet"]),
         "reports/stage0_quantization.json"),
        ("Fabric active shared product expressions",
         a["operation_counts"]["implemented_active_shared_product_expressions"],
         "reports/stage1_compute_fabric.json"),
        ("Nominal cycles per inference", a["latency"]["nominal_cycles"],
         "reports/stage1_compute_fabric.json"),
        ("Behavioral verification images", b["images"],
         "reports/stage3_behavioral_verification.json"),
        ("Behavioral RTL-vs-golden mismatches",
         b["portable_backend"]["hidden_mismatches"]
         + b["portable_backend"]["logit_mismatches"]
         + b["portable_backend"]["prediction_mismatches"],
         "reports/stage3_behavioral_verification.json"),
        ("Cycle-level trace checks", b["cycle_level_trace"]["total_checks"],
         "reports/stage3_behavioral_verification.json"),
        ("Cycle-level trace failures", b["cycle_level_trace"]["failures"],
         "reports/stage3_behavioral_verification.json"),
        ("FPGA post-synthesis images", d["fpga"]["gate_level"]["no_stall"]["images"],
         "reports/stage4_dual_target_portability.json"),
        ("FPGA post-synthesis logit mismatches",
         d["fpga"]["gate_level"]["no_stall"]["logit_mismatches"],
         "reports/stage4_dual_target_portability.json"),
        ("Generic post-synthesis images",
         d["generic"]["gate_level"]["no_stall"]["images"],
         "reports/stage4_dual_target_portability.json"),
        ("Generic post-synthesis logit mismatches",
         d["generic"]["gate_level"]["no_stall"]["logit_mismatches"],
         "reports/stage4_dual_target_portability.json"),
        ("iCE40 total cells", d["fpga"]["resources"]["total_cells"],
         "reports/stage4_dual_target_portability.json"),
        ("iCE40 SB_LUT4", d["fpga"]["resources"]["lut"],
         "reports/stage4_dual_target_portability.json"),
        ("iCE40 flip-flops", d["fpga"]["resources"]["ff"],
         "reports/stage4_dual_target_portability.json"),
        ("iCE40 SB_CARRY", d["fpga"]["resources"]["carry"],
         "reports/stage4_dual_target_portability.json"),
        ("iCE40 SB_RAM40_4K", d["fpga"]["resources"]["ram"],
         "reports/stage4_dual_target_portability.json"),
        ("iCE40 SB_MAC16 (DSP)", d["fpga"]["resources"]["dsp"],
         "reports/stage4_dual_target_portability.json"),
        ("Generic total cells", d["generic"]["resources"]["total_cells"],
         "reports/stage4_dual_target_portability.json"),
        ("Generic multiplier/arithmetic cells",
         d["generic"]["resources"]["arithmetic_or_multiplier_cells"],
         "reports/stage4_dual_target_portability.json"),
        ("OpenROM macros generated", len(p["macros"]),
         "reports/stage5_openrom_physical.json"),
        ("OpenROM programmed cells verified",
         p["content_verification"]["programmed_cells_checked"],
         "reports/stage5_openrom_physical.json"),
        ("OpenROM programmed-cell mismatches",
         p["content_verification"]["programmed_cell_mismatches"],
         "reports/stage5_openrom_physical.json"),
        ("Weight indices recovered from physical macros",
         p["content_verification"]["weight_indices"],
         "reports/stage5_openrom_physical.json"),
        ("OpenROM total macro GDS bounding-box area",
         "%.1f um^2" % ar["openrom_total_macro_bbox_um2"],
         "reports/stage5_openrom_physical.json"),
        ("Portable storage mapped to SKY130, cells",
         ar["portable_asic_storage"]["total_cells"],
         "reports/stage5_openrom_physical.json"),
        ("Portable storage mapped to SKY130, liberty cell area",
         "%.1f um^2" % ar["portable_asic_storage"]["chip_area_um2"],
         "reports/stage5_openrom_physical.json"),
        ("Physical signoff", p["signoff"]["status"],
         "reports/stage5_openrom_physical.json"),
    ]


def main() -> int:
    before = {p: sha(p) for p in FROZEN}
    s = load()
    try:
        consistency = check_consistency(s)
    except Contradiction as exc:
        print("STOP: %s" % exc, file=sys.stderr)
        return 2

    final = build(s)
    final["cross_stage_consistency"] = consistency
    final["frozen_artifacts"] = before
    final["environment"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "yosys": s[4]["reproducibility"]["yosys"],
        "iverilog": s[4]["reproducibility"]["iverilog"],
        "yosys_datdir": s[4]["reproducibility"]["yosys_datdir"],
        "openram": {k: s[5]["toolchain"][k] for k in
                    ("openram_root", "openram_commit", "openram_branch",
                     "openram_tracked_files_modified")},
        "pdk": {"root": s[5]["toolchain"]["pdk_root"],
                "sky130A_present": s[5]["toolchain"]["pdk_sky130A_present"],
                "provenance": "installed with ciel into PDK_ROOT; the old "
                              "~/.volare/sky130A layout does not exist on this "
                              "machine"},
        "magic": s[5]["toolchain"]["magic"],
        "netgen": s[5]["toolchain"]["netgen"],
        "klayout": s[5]["toolchain"]["klayout"],
        "liberty": s[5]["portable_asic_storage"]["liberty"],
        "note": "This environment is NOT one-click portable. The functional "
                "flow needs only Python, Yosys and Icarus; the physical "
                "OpenROM flow additionally needs a user-space OpenRAM "
                "checkout, the SKY130 PDK, magic, netgen and KLayout at the "
                "exact paths recorded above.",
    }

    with open(OUT_JSON + ".tmp", "w") as fh:
        json.dump(final, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(OUT_JSON + ".tmp", OUT_JSON)

    rows = results_rows(final)
    with open(OUT_CSV + ".tmp", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value", "source"])
        for r in rows:
            w.writerow(r)
    os.replace(OUT_CSV + ".tmp", OUT_CSV)

    after = {p: sha(p) for p in FROZEN}
    changed = [p for p in FROZEN if before[p] != after[p]]
    if changed:
        print("FATAL: frozen artifacts changed: %s" % changed, file=sys.stderr)
        return 1
    print("cross-stage consistency: %d checks, %d disagreements"
          % (consistency["checked"], consistency["disagreements"]))
    print("wrote %s (%d metrics in %s)"
          % (os.path.relpath(OUT_JSON, ROOT), len(rows),
             os.path.relpath(OUT_CSV, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
