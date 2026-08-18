"""Stage-0 report assembly."""

from __future__ import annotations

from typing import Dict

import numpy as np

from . import contract as C
from .golden import IntegerModel, accuracy


def index_histogram(indices: np.ndarray) -> list:
    return [int(v) for v in np.bincount(np.asarray(indices).ravel().astype(np.int64),
                                        minlength=C.K)]


def layer_report(name: str, indices: np.ndarray, bias: np.ndarray,
                 widths, sat: Dict[str, float]) -> dict:
    hist = index_histogram(indices)
    unused = [i for i, c in enumerate(hist) if c == 0]
    q = C.ALPHABET[np.asarray(indices).astype(np.int64)]
    return {
        "shape": list(np.asarray(indices).shape),
        "orientation": "[in_features, out_features]",
        "synapse_count": int(np.asarray(indices).size),
        "weight_index_histogram": hist,
        "weight_index_histogram_by_level": {
            str(int(C.ALPHABET[i])): hist[i] for i in range(C.K)},
        "unused_weight_levels": unused,
        "unused_weight_level_values": [int(C.ALPHABET[i]) for i in unused],
        "min_quantized_weight": int(q.min()),
        "max_quantized_weight": int(q.max()),
        "weight_saturation_count": sat["weight_saturation_count"],
        "weight_saturation_percentage": sat["weight_saturation_percentage"],
        "pre_clip_min": sat["pre_clip_min"],
        "pre_clip_max": sat["pre_clip_max"],
        "bias_min": int(np.min(bias)),
        "bias_max": int(np.max(bias)),
        "bias_bits_declared": C.BIAS_BITS[name],
        "bias_bits_required": C.bits_for_signed_range(int(np.min(bias)),
                                                      int(np.max(bias))),
        "product_bits": widths.product_bits,
        "accumulator_bits": widths.accumulator_bits,
        "dot_product_bits": widths.dot_bits,
        "worst_case_accumulator_min": widths.accumulator_min,
        "worst_case_accumulator_max": widths.accumulator_max,
    }


def activation_report(x_test: np.ndarray, collect: dict) -> dict:
    hidden_elems = sum(collect["hidden_elems"])
    hidden_sat = sum(collect["hidden_sat_count"])
    return {
        "input_signedness": "unsigned",
        "input_width_bits": C.ACT_BITS,
        "input_range_declared": [C.ACT_MIN, C.ACT_MAX],
        "input_range_observed_test": [int(x_test.min()), int(x_test.max())],
        "hidden_range_declared": [C.ACT_MIN, C.ACT_MAX],
        "hidden_range_observed_test": [min(collect["hidden_min"]),
                                       max(collect["hidden_max"])],
        "hidden_pre_saturation_max_observed": max(collect["hidden_presat_max"]),
        "hidden_saturation_count": hidden_sat,
        "hidden_saturation_percentage": 100.0 * hidden_sat / hidden_elems,
        "hidden_elements_evaluated": hidden_elems,
        "hidden_zero_count": sum(collect["hidden_zero_count"]),
        "hidden_zero_percentage": 100.0 * sum(collect["hidden_zero_count"]) / hidden_elems,
        "layer1_accumulator_range_observed": [min(collect["acc1_min"]),
                                              max(collect["acc1_max"])],
        "logit_range_observed": [min(collect["logit_min"]),
                                 max(collect["logit_max"])],
    }


def arithmetic_contract_report() -> dict:
    l1, l2 = C.layer1_widths(), C.layer2_widths()
    return {
        "input_signedness": "unsigned",
        "input_width_bits": C.ACT_BITS,
        "input_zero_point": 0,
        "weight_index_width_bits": C.WEIGHT_INDEX_BITS,
        "weight_alphabet_values": [int(v) for v in C.ALPHABET],
        "weight_alphabet_rule": "alphabet[i] = i - 8",
        "weight_value_signedness": "signed",
        "weight_value_width_bits": C.WEIGHT_VALUE_BITS,
        "product_width_bits": {"layer1": l1.product_bits, "layer2": l2.product_bits},
        "product_signedness": "signed",
        "accumulator_width_bits": {"layer1": l1.accumulator_bits,
                                   "layer2": l2.accumulator_bits},
        "accumulator_signedness": "signed",
        "bias_width_bits": dict(C.BIAS_BITS),
        "bias_format": "signed integer in the layer accumulator domain, added "
                       "directly to the dot product",
        "requantization_rule": (
            "hidden: h = clamp((max(acc1, 0) + %d) >> %d, 0, 255); "
            "output: none (raw signed logits)"
            % (1 << (C.HIDDEN_REQUANT_SHIFT - 1), C.HIDDEN_REQUANT_SHIFT)),
        "requantization_shift": C.HIDDEN_REQUANT_SHIFT,
        "rounding_rule": C.ROUNDING_RULE,
        "saturation_rule": C.SATURATION_RULE,
        "relu_semantics": "ReLU applied to the signed accumulator BEFORE the "
                          "shift, so the shifted operand is never negative and "
                          "the shift direction is unambiguous",
        "output_logit_width_bits": l2.output_bits,
        "output_logit_signedness": "signed",
        "prediction_rule": "argmax over the 10 signed logits; lowest index wins ties",
        "scale_note": (
            "No multiplicative requantisation scale exists anywhere in the "
            "datapath. The only requantisation operator is a fixed power-of-two "
            "shift that is an architectural constant, so no trained-model scale "
            "constant can leak into the fixed compute fabric."),
    }


def build_stage0_report(model: IntegerModel, data: dict, float_acc: dict,
                        sat_stats: dict, meta: dict) -> dict:
    collect = {}
    int_test_acc = accuracy(model, data["x_test"], data["y_test"], collect=collect)
    int_train_acc = accuracy(model, data["x_train"], data["y_train"])
    l1w, l2w = C.layer1_widths(), C.layer2_widths()
    return {
        "stage": 0,
        "rtl_generated": False,
        "meta": meta,
        "float_model": {
            "train_accuracy": float_acc["train"],
            "val_accuracy": float_acc["val"],
            "test_accuracy": float_acc["test"],
            "note": "reference only; the NumPy integer golden model is the RTL oracle",
        },
        "quantized_integer_model": {
            "train_accuracy": int_train_acc,
            "test_accuracy": int_test_acc,
            "accuracy_drop_from_float": float_acc["test"] - int_test_acc,
        },
        "layer1": layer_report("layer1", model.layer1_weight_indices,
                               model.layer1_bias, l1w, sat_stats["layer1"]),
        "layer2": layer_report("layer2", model.layer2_weight_indices,
                               model.layer2_bias, l2w, sat_stats["layer2"]),
        "activations": activation_report(data["x_test"], collect),
        "arithmetic_contract": arithmetic_contract_report(),
        "model_size": C.storage_report(),
        "multiply_select_add": C.msa_report(),
        "widths": {"layer1": l1w.to_dict(), "layer2": l2w.to_dict()},
    }
