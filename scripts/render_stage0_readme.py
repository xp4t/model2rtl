#!/usr/bin/env python3
"""Regenerate the 'Stage 0 results' block of README.md from the saved report.

Keeps the README numbers mechanically derived from
reports/stage0_quantization.json rather than hand-copied.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- STAGE0_RESULTS_START -->"
END = "<!-- STAGE0_RESULTS_END -->"


def render(rep: dict) -> str:
    f = rep["float_model"]
    q = rep["quantized_integer_model"]
    a = rep["activations"]
    s = rep["model_size"]
    m = rep["meta"]
    lines = []
    add = lines.append
    add("")
    add("### Accuracy")
    add("")
    add("| Model | Train | Test |")
    add("|-------|-------|------|")
    add("| float32 baseline (reference only) | %.4f | %.4f |"
        % (f["train_accuracy"], f["test_accuracy"]))
    add("| **quantized integer golden model** | %.4f | **%.4f** |"
        % (q["train_accuracy"], q["test_accuracy"]))
    add("")
    add("Accuracy drop from float on the test set (float minus integer): "
        "**%+.4f** (%+.2f percentage points). Target was > 0.90 for the "
        "integer model."
        % (q["accuracy_drop_from_float"], 100.0 * q["accuracy_drop_from_float"]))
    add("")
    add("The exported integer model was cross-checked against the TensorFlow QAT "
        "graph over all %d test images: max |logit difference| = %g."
        % (m["dataset"]["test_images"], m["tf_graph_vs_golden_max_logit_diff"]))
    add("")
    add("### Weight index distribution")
    add("")
    add("| Level (`alphabet[i]`) | " + " | ".join(
        str(v) for v in rep["arithmetic_contract"]["weight_alphabet_values"]) + " |")
    add("|---|" + "---|" * 16)
    for name in ("layer1", "layer2"):
        L = rep[name]
        add("| %s (%d synapses) | " % (name, L["synapse_count"])
            + " | ".join(str(c) for c in L["weight_index_histogram"]) + " |")
    add("")
    for name in ("layer1", "layer2"):
        L = rep[name]
        add("- **%s** %s: quantized weight range [%d, %d], unused levels: %s, "
            "weight saturation during export: %d (%.4f%%), bias range [%d, %d] "
            "(needs %d of the declared %d signed bits)."
            % (name, L["shape"], L["min_quantized_weight"], L["max_quantized_weight"],
               L["unused_weight_level_values"] or "none",
               L["weight_saturation_count"], L["weight_saturation_percentage"],
               L["bias_min"], L["bias_max"], L["bias_bits_required"],
               L["bias_bits_declared"]))
    add("")
    add("### Observed integer ranges on the 10,000-image test set")
    add("")
    add("| Signal | Declared | Observed |")
    add("|--------|----------|----------|")
    add("| input activation | [%d, %d] | [%d, %d] |"
        % (*a["input_range_declared"], *a["input_range_observed_test"]))
    add("| layer 1 accumulator | [%d, %d] | [%d, %d] |"
        % (rep["widths"]["layer1"]["accumulator_min"],
           rep["widths"]["layer1"]["accumulator_max"],
           *a["layer1_accumulator_range_observed"]))
    add("| hidden activation | [%d, %d] | [%d, %d] |"
        % (*a["hidden_range_declared"], *a["hidden_range_observed_test"]))
    add("| logits | [%d, %d] | [%d, %d] |"
        % (rep["widths"]["layer2"]["accumulator_min"],
           rep["widths"]["layer2"]["accumulator_max"],
           *a["logit_range_observed"]))
    add("")
    add("Hidden saturation: **%d of %d hidden activations (%.4f%%)** hit the "
        "uint8 clamp; the largest pre-saturation value observed was %d. "
        "%.2f%% of hidden activations are exactly 0 (ReLU)."
        % (a["hidden_saturation_count"], a["hidden_elements_evaluated"],
           a["hidden_saturation_percentage"],
           a["hidden_pre_saturation_max_observed"], a["hidden_zero_percentage"]))
    add("")
    add("### Weight storage")
    add("")
    add("%d synapses (%d + %d) x 4 bits = **%d bits = %d bytes** of weight index "
        "storage. Biases add %d + %d integers stored as int32."
        % (s["total_synapses"], s["layer1_synapses"], s["layer2_synapses"],
           s["total_index_bits"], s["total_index_bytes"], 32, 10))
    add("")
    add("### Provenance")
    add("")
    add("| Item | Value |")
    add("|------|-------|")
    add("| seed | %d |" % m["seed"])
    add("| quantization method | %s |" % m["quantization_method"])
    add("| QAT epochs / float epochs | %d / %d |" % (m["epochs_qat"], m["epochs_float"]))
    add("| Python | %s |" % m["versions"]["python"])
    add("| NumPy | %s |" % m["versions"]["numpy"])
    add("| TensorFlow / Keras | %s / %s |"
        % (m["versions"]["tensorflow"], m["versions"]["keras"]))
    add("| dataset split | %s |" % m["dataset"]["split_rule"])
    add("| `x_test` SHA-256 | `%s` |" % m["dataset"]["x_test_sha256"][:32])
    add("| `mnist_weights_indices.npz` SHA-256 | `%s` |"
        % m["artifact_hashes"]["mnist_weights_indices.npz"][:32])
    add("| `quant_params.json` SHA-256 | `%s` |"
        % m["artifact_hashes"]["quant_params.json"][:32])
    add("| model parameter SHA-256 | `%s` |"
        % m["artifact_hashes"]["model_parameter_sha256"][:32])
    if m.get("hidden_shift_sweep"):
        add("")
        add("### Hidden requantization shift sweep (diagnostic, %d epochs each)"
            % m["epochs_qat"] if False else
            "### Hidden requantization shift sweep (diagnostic)")
        add("")
        add("| shift | " + " | ".join(str(e["hidden_shift"])
                                      for e in m["hidden_shift_sweep"]) + " |")
        add("|---|" + "---|" * len(m["hidden_shift_sweep"]))
        add("| val accuracy | " + " | ".join("%.4f" % e["val_accuracy"]
                                             for e in m["hidden_shift_sweep"]) + " |")
        add("")
        add("Shift **%d** was frozen into the contract." % rep["arithmetic_contract"]["requantization_shift"])
    add("")
    return "\n".join(lines)


def main() -> int:
    rep_path = os.path.join(ROOT, "reports", "stage0_quantization.json")
    if not os.path.exists(rep_path):
        print("missing %s: run scripts/train_mnist_mlp.py first" % rep_path)
        return 1
    with open(rep_path) as fh:
        rep = json.load(fh)
    readme = os.path.join(ROOT, "README.md")
    text = open(readme).read()
    if START not in text or END not in text:
        print("README markers missing")
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    # render BEFORE opening for write: a failure here must never truncate the
    # README that is already on disk
    body = render(rep)
    new_text = head + START + body + END + tail
    tmp = readme + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(new_text)
    os.replace(tmp, readme)
    print("README.md Stage-0 results block updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
