#!/usr/bin/env python3
"""Regenerate the 'Stage 3 results' block of README.md from the saved report."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- STAGE3_RESULTS_START -->"
END = "<!-- STAGE3_RESULTS_END -->"


def render(rep: dict) -> str:
    ts = rep["test_set"]
    p = rep["portable_backend"]
    o = rep["openram_behavioral_backend"]
    b2b = rep["backend_to_backend"]
    tr = rep["internal_checkpointing"]
    st = rep["stalls"]
    rs = rep["reset"]
    mp = rep["memory_pipeline"]
    am = rep["argmax"]
    ae = rep["arithmetic_edges"]
    alt = rep["alternate_model"]
    L = []
    add = L.append
    add("")
    add("Stage 3 runs the frozen production RTL against the Stage-0 NumPy integer")
    add("golden model. **Keras float output is never used as an oracle.**")
    add("")
    add("### Three metrics, kept separate")
    add("")
    add("These are not the same thing, and Stage 3 only gates on the first:")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    add("| **1. RTL vs integer golden model (the PASS criterion)** | **0 mismatches** out of %d logit, %d hidden and %d prediction comparisons |"
        % (p["logits_compared"], p["hidden_values_compared"],
           p["prediction_comparisons"]))
    add("| 2. Quantized integer model MNIST accuracy | 96.45%% over the full "
        "10,000-image test set (Stage 0); %.2f%% on this %d-image subset |"
        % (100.0 * rep["integer_golden_accuracy_on_subset"], ts["count"]))
    add("| 3. RTL MNIST accuracy | %.2f%% on the same subset |"
        % (100.0 * p["rtl_label_accuracy"]))
    add("")
    add("Metrics 2 and 3 are identical *because* metric 1 is zero. An image the")
    add("integer model gets wrong is still a perfect RTL implementation.")
    add("")
    add("### Test set")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| selection | %s |" % ts["selection_policy"])
    add("| images | %d |" % ts["count"])
    add("| label histogram (0-9) | %s |" % ts["label_histogram"])
    add("| indices SHA-256 | `%s` |" % ts["indices_sha256"][:32])
    add("| images SHA-256 | `%s` |" % ts["images_sha256"][:32])
    add("| labels SHA-256 | `%s` |" % ts["labels_sha256"][:32])
    add("")
    add("### Backend results")
    add("")
    add("| | Portable | OpenRAM behavioural |")
    add("|---|---|---|")
    add("| images | %d | %d |" % (p["images"], o["images"]))
    add("| hidden values compared | %d | %d |"
        % (p["hidden_values_compared"], o["hidden_values_compared"]))
    add("| logits compared | %d | %d |" % (p["logits_compared"], o["logits_compared"]))
    add("| prediction comparisons | %d | %d |"
        % (p["prediction_comparisons"], o["prediction_comparisons"]))
    add("| **hidden mismatches** | **%d** | **%d** |"
        % (p["hidden_mismatches"], o["hidden_mismatches"]))
    add("| **logit mismatches** | **%d** | **%d** |"
        % (p["logit_mismatches"], o["logit_mismatches"]))
    add("| **prediction mismatches** | **%d** | **%d** |"
        % (p["prediction_mismatches"], o["prediction_mismatches"]))
    add("| label accuracy | %.4f | %.4f |"
        % (p["rtl_label_accuracy"], o["rtl_label_accuracy"]))
    add("| cycles per inference | %s | %s |"
        % (p["cycles_per_inference"], o["cycles_per_inference"]))
    add("")
    add("Backend-to-backend: %d hidden, %d logit, %d prediction and %d cycle-count"
        % (b2b["hidden_mismatches"], b2b["logit_mismatches"],
           b2b["prediction_mismatches"], b2b["cycle_mismatches"]))
    add("mismatches. The OpenRAM figure is a **behavioural representation of the")
    add("canonical OpenROM contents** — it is not physical OpenROM verification.")
    add("")
    add("### Cycle-level internal checkpointing")
    add("")
    add("For %d images every cycle of the fabric was captured and replayed against"
        % tr["images_traced"])
    add("the golden model, so a mismatch would be localised to a specific")
    add("(image, cycle, signal) rather than only showing up at the top level.")
    add("")
    add("| Checkpoint | Comparisons |")
    add("|---|---|")
    labels = {
        "mac_l1": "layer-1 multiply-select-add cycles",
        "mac_l2": "layer-2 multiply-select-add cycles",
        "fin_l1": "layer-1 finalisation cycles",
        "fin_l2": "layer-2 finalisation cycles",
        "weight_word": "weight ROM word vs address issued one cycle earlier",
        "bias_word": "bias ROM word vs address issued one cycle earlier",
        "product": "shared product-bank entries and selected products",
        "accumulator": "accumulator state before each update",
        "requant": "biased accumulator and requantised hidden value",
        "logit": "final signed logits",
    }
    for k, v in tr["checks"].items():
        add("| %s | %d |" % (labels.get(k, k), v))
    add("| **total** | **%d** |" % tr["total_checks"])
    add("| **failures** | **%d** |" % tr["failures"])
    add("")
    add("Traced neurons: layer 1 %s, layer 2 %s. Signals: %s."
        % (tr["traced_neurons_layer1"], tr["traced_neurons_layer2"],
           ", ".join("`%s`" % s for s in tr["signals"])))
    add("")
    add("### Memory pipeline (no off-by-one)")
    add("")
    add("The fabric pipelines its parameter reads, so every cycle in which it")
    add("consumes `wmem_data` or `bmem_data` was checked against the address it")
    add("issued exactly one cycle earlier: **%d weight-word and %d bias-word"
        % (mp["weight_word_alignment_checks"], mp["bias_word_alignment_checks"]))
    add("alignment checks, %d failures.** Cases covered:" % mp["off_by_one_failures"])
    add("")
    for c in mp["cases_covered"]:
        add("- %s" % c)
    add("")
    add("### Input handshake under different legal timings")
    add("")
    add("| Pattern | Images | Cycles | Mismatches |")
    add("|---|---|---|---|")
    for name, v in st.items():
        add("| %s | %d | %d–%d | %d |"
            % (v["pattern"], v["images"], v["cycles_min"], v["cycles_max"],
               v["hidden_mismatches"] + v["logit_mismatches"]
               + v["prediction_mismatches"]))
    add("")
    add("Results are bit-identical regardless of input timing; only latency")
    add("changes. No activation was lost or duplicated.")
    add("")
    add("### Synchronous reset")
    add("")
    add("| Reset point | Cycles after start | Stale-state failures | Fresh inference exact |")
    add("|---|---|---|---|")
    for label, v in rs["results"].items():
        add("| %s | %s | %d | logits %s, hidden %s |"
            % (label,
               "n/a (idle)" if v["reset_at_cycles_after_start"] < 0
               else v["reset_at_cycles_after_start"],
               v["stale_state_failures"], v["post_reset_logits_exact"],
               v["post_reset_hidden_exact"]))
    add("")
    add("After every reset, `busy`, `done`, `prediction_valid` and `in_ready` are")
    add("low and all accumulators, hidden registers and logit registers read zero.")
    add("")
    add("### Back-to-back transactions")
    add("")
    add("%d inferences ran consecutively in one simulator process with no reset"
        % rep["back_to_back"]["transactions"])
    add("between them: %d mismatches. `done` is a single-cycle pulse every time,"
        % rep["back_to_back"]["mismatches"])
    add("and `prediction_valid` holds until the next `start`.")
    add("")
    add("### Argmax")
    add("")
    add("%d cases, %d failures. Tie rule: **%s**."
        % (len(am["cases"]), am["failures"], am["tie_rule"]))
    add("Covered: a unique maximum at every class 0-9, a two-way tie, a")
    add("three-way tie, a ten-way tie, all-negative logits, and logits at the")
    add("representable extrema.")
    add("")
    add("### Arithmetic edge cases at the top level")
    add("")
    add("%d activation cases and %d special cases, %d failures."
        % (len(ae["activation_cases"]), len(ae["special_cases"]), ae["failures"]))
    add("Covered: x = 0, 1 and 255 against every alphabet level (including -8,")
    add("-1, 0, +1, +7); a strongly negative layer-1 accumulator forced through")
    add("ReLU to hidden = 0; hidden saturating to 255; the round-half-up")
    add("boundaries; and all-negative and all-positive logits. No wraparound.")
    add("")
    add("### A second parameter set on the unchanged fabric")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| fabric SHA-256 before | `%s` |" % alt["fabric_sha256_before"][:32])
    add("| fabric SHA-256 after | `%s` |" % alt["fabric_sha256_after"][:32])
    add("| **identical** | **%s** |" % alt["fabric_unchanged"])
    add("| vectors tested | %d |" % alt["vectors_tested"])
    add("| mismatches vs the MSA integer reference | **%d** |"
        % alt["mismatches_vs_msa_reference"])
    add("| alternate `weights_l1` image SHA-256 | `%s` |"
        % alt["parameter_image_sha256"]["weights_l1"][:32])
    add("")
    add("Only the parameter backend was regenerated. %s" % alt["note"])
    add("")
    add("### Lint and elaboration of both production variants")
    add("")
    add("| Build | Yosys `check -assert` | Latches | Multi-driven | Undriven | Icarus `-g2001 -Wall` |")
    add("|---|---|---|---|---|---|")
    for name, v in rep["lint"].items():
        add("| top + %s | %s | %d | %s | %s | %s |"
            % (name, v["yosys_check_assert"], v["yosys_inferred_latches"],
               v["yosys_multiple_drivers"], v["yosys_undriven_nets"],
               v["icarus_verilog2001"]))
    add("")
    add("### No model-specific shortcuts")
    add("")
    add("`mnist_mlp_fabric.v` and `mnist_mlp_top.v` were scanned for MNIST labels,")
    add("embedded test images, expected logits and hard-coded predictions: **%s**."
        % ("clean" if rep["shortcut_scan"]["clean"]
           else rep["shortcut_scan"]["findings"]))
    add("The only model-dependent production RTL is the parameter backend.")
    add("")
    add("### OpenROM physical status as of Stage 3: PARTIAL")
    add("")
    add("*Superseded by Stage 5, which generated all seven macros. Kept here as")
    add("the Stage-3 record.*")
    add("")
    ops = rep["openrom_physical_status"]
    add("- `weights_l2`: %s" % ops["weights_l2"])
    add("- `weights_l1`: %s" % ops["weights_l1"])
    add("- bias macros: %s" % ops["bias_l1_l2"])
    add("- DRC/LVS: %s" % ops["drc_lvs"])
    add("- Banking: %s" % ops["banking"])
    add("")
    add("### Not claimed")
    add("")
    for c in rep["not_claimed"]:
        add("- %s" % c)
    add("")
    add("These four statements were written at Stage 3. Stage 4 has since")
    add("verified FPGA-oriented and generic/ASIC-oriented synthesis portability")
    add("and gate-level simulated both netlists against the Stage-0 integer")
    add("golden model — see section 14. Formal gate-level *equivalence")
    add("checking* and physical OpenROM signoff are still not claimed, and")
    add("neither is place-and-route or timing closure on either target.")
    add("")
    return "\n".join(L)


def main() -> int:
    rep_path = os.path.join(ROOT, "reports", "stage3_behavioral_verification.json")
    if not os.path.exists(rep_path):
        print("missing %s: run scripts/verify_stage3.py first" % rep_path)
        return 1
    rep = json.load(open(rep_path))
    if rep.get("status") != "PASS":
        print("refusing to render a README block for a failing Stage-3 report")
        return 1
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
    print("README.md Stage-3 results block updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
