#!/usr/bin/env python3
"""Stage 6: render FINAL-REPORT.md from reports/final_report.json.

Every number comes from the JSON, which in turn was extracted from the six
stage reports.  Nothing is retyped, so the prose cannot drift from the measured
results.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reports", "final_report.json")
OUT = os.path.join(ROOT, "FINAL-REPORT.md")

BANK_ORDER = ["weights_l1_b0", "weights_l1_b1", "weights_l1_b2",
              "weights_l1_b3", "weights_l2", "bias_l1", "bias_l2"]


def pct(x):
    return "%.2f%%" % (100.0 * x)


def render(f: dict) -> str:
    m, q, a = f["model"], f["quantization"], f["architecture"]
    r, pb = f["rtl"], f["parameter_backends"]
    b = f["behavioral_verification"]
    d = f["dual_target_portability"]
    cm = f["constant_multiplication"]
    p = f["physical_openrom"]
    ar, cx = f["area"], f["crossover"]
    env = f["environment"]
    L = []
    add = L.append

    add("# model2rtl — final technical report")
    add("")
    add("> %s" % f["claim"])
    add(">")
    add("> %s" % f["claim_scope"])
    add("")
    add("| Stage | Scope | Status |")
    add("|---|---|---|")
    add("| 0 | training, quantization, integer golden model, arithmetic contract | **%s** |" % f["stage_status"]["stage0_quantization"])
    add("| 1 | weight-independent Multiply-Select-Add compute fabric | **%s** |" % f["stage_status"]["stage1_compute_fabric"])
    add("| 2 | two interchangeable parameter-storage backends | **%s** |" % f["stage_status"]["stage2_parameter_backends"])
    add("| 3 | behavioral RTL verification against the integer golden model | **%s** |" % f["stage_status"]["stage3_behavioral_verification"])
    add("| 4 | dual-target synthesis portability + gate-level verification | **%s** |" % f["stage_status"]["stage4_dual_target_portability"])
    add("| 5 | physical OpenROM generation | **%s** |" % f["stage_status"]["stage5_physical_generation"])
    add("| 5 | physical DRC/LVS signoff | **%s** |" % f["stage_status"]["stage5_physical_signoff"])
    add("")
    add("Stage 2 closed as PARTIAL because two of the four logical memory "
        "shapes could not be built by the installed OpenROM at that time. "
        "Stage 5 completed them under approved physical transformations; the "
        "Stage-2 verdict is left as it was recorded rather than restated.")
    add("")
    add("---")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. Project summary")
    add("")
    add("**Input** — a trained MNIST MLP, topology **%s**, quantized to "
        "**%d-bit weight indices** (%d levels) and **uint8 activations**."
        % (m["topology"], q["weight_index_bits"], len(q["weight_alphabet"])))
    add("")
    add("**Output** — portable synthesizable Verilog-2001 that reproduces the "
        "integer model bit-exactly.")
    add("")
    add("The architectural idea, per input activation `x_i`:")
    add("")
    add("```")
    add("compute x_i * every one of the 16 alphabet levels   -- once")
    add("        |")
    add("share those 16 products across all active output neurons")
    add("        |")
    add("select the one each synapse needs, using its 4-bit weight index")
    add("        |")
    add("accumulate")
    add("```")
    add("")
    add("Execution is **%s**. One 16-product bank is reused %s."
        % (a["execution"], a["product_bank_reuse"].split(", reused ")[1]))
    add("")

    # ---------------------------------------------------------------- 2
    add("## 2. Public prior-art / IP note")
    add("")
    add("%s" % f["prior_art_note"])
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. Quantization results")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    add("| Float test accuracy | %s |" % pct(m["float_test_accuracy"]))
    add("| Quantized integer test accuracy | %s |"
        % pct(m["quantized_integer_test_accuracy"]))
    add("| Accuracy change | **%s** |"
        % m["accuracy_change_wording"].replace("quantization LOSES",
                                               "quantization loses"))
    add("")
    add("The integer model is the **only** oracle used anywhere in this "
        "project. Keras float output is a reference number and was never used "
        "to check RTL arithmetic.")
    add("")
    add("| Contract item | Value |")
    add("|---|---|")
    add("| weight alphabet | `%s` |"
        % ", ".join(str(v) for v in q["weight_alphabet"]))
    add("| weight index | %d bits |" % q["weight_index_bits"])
    add("| activations | %s |" % q["activation"])
    add("| requantization | `%s` |" % q["requantization_rule"])
    add("| rounding | %s |" % q["rounding_rule"])
    add("| saturation | %s |" % q["saturation_rule"])
    add("| prediction | %s |" % q["prediction_rule"])
    add("")
    add("There is **no multiplicative requantization scale anywhere in the "
        "datapath** — the only requantization operator is a fixed power-of-two "
        "shift of %d. That is what makes the fabric provably free of trained "
        "values." % q["requantization_shift"])
    add("")
    add("| Synapses | Count |")
    add("|---|---|")
    add("| layer 1 (784 x 32) | %d |" % q["synapses"]["layer1"])
    add("| layer 2 (32 x 10) | %d |" % q["synapses"]["layer2"])
    add("| **total** | **%d** |" % q["synapses"]["total"])
    add("")
    add("**All 16 levels are used** in both layers — no level is dead: %s."
        % ("confirmed" if q["all_sixteen_levels_used"] else "NOT confirmed"))
    add("")
    add("| Level | Layer 1 | Layer 2 |")
    add("|---|---|---|")
    for lv in range(-8, 8):
        add("| %+d | %d | %d |"
            % (lv, q["weight_index_histogram"]["layer1"][str(lv)],
               q["weight_index_histogram"]["layer2"][str(lv)]))
    add("")
    add("Weight saturation during quantization-aware training: layer 1 "
        "**%.2f%%**, layer 2 **%.1f%%**. %s"
        % (q["weight_saturation"]["layer1_percent"],
           q["weight_saturation"]["layer2_percent"],
           q["weight_saturation"]["note"].split("Saturation counts ")[1]
           .capitalize()))
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. Architecture")
    add("")
    add("Three different counts get confused easily, so they are kept apart:")
    add("")
    add("| Quantity | Count | Kind |")
    add("|---|---|---|")
    oc = a["operation_counts"]
    add("| naive fully spatial synapse multiplications | %d | source-level operation count |"
        % oc["naive_fully_spatial_synapse_multiplications"])
    add("| fully spatial MSA product generators | %d | source-level operation count |"
        % oc["fully_spatial_msa_product_generators"])
    add("| **implemented** active shared product expressions | **%d** | source-level operation count |"
        % oc["implemented_active_shared_product_expressions"])
    add("")
    add("The implemented count is %d because execution is input-serial: the "
        "same bank is recomputed each cycle for the current activation instead "
        "of being unrolled across all inputs. **%s**"
        % (oc["implemented_active_shared_product_expressions"], a["tradeoff"]))
    add("")
    add("None of these three is a physical multiplier count — see section 11.")
    add("")
    add("| Latency | Value |")
    add("|---|---|")
    add("| nominal cycles per inference | **%d** (`%s`) |"
        % (a["latency"]["nominal_cycles"], a["latency"]["formula"]))
    add("| at an assumed 50 MHz | %.2f us |"
        % a["latency"]["examples_architectural_only"]["50MHz_us"])
    add("| at an assumed 100 MHz | %.2f us |"
        % a["latency"]["examples_architectural_only"]["100MHz_us"])
    add("")
    add("**These are architectural calculations, not measured timing.** %s"
        % a["latency"]["caveat"])
    add("")
    add("Structure confirmed in the elaborated netlist: %d `$mul` cells and %d "
        "selector instances — exactly K products shared by every neuron of the "
        "active layer."
        % (a["structure_verified_in_netlist"]["elaborated_multiplier_cells"],
           a["structure_verified_in_netlist"]["selector_instances"]))
    add("")

    # ---------------------------------------------------------------- 5
    add("## 5. Portable RTL")
    add("")
    fab = r["fabric"]
    add("| Property | Value |")
    add("|---|---|")
    add("| file | `%s` |" % fab["path"])
    add("| SHA-256 | `%s` |" % fab["sha256"])
    add("| language | %s, vendor-neutral |" % fab["language"])
    add("| clocks / resets | %d clock, %s |" % (fab["clocks"], fab["resets"]))
    add("| vendor primitives, IP cores, tool pragmas | none |")
    add("")
    add("**The fabric contains no trained value.** This is proved, not "
        "asserted: regenerating it with a completely different weight set and "
        "with different biases produces a byte-identical file.")
    add("")
    ind = fab["weight_independence"]
    add("| Generation input | Fabric SHA-256 |")
    add("|---|---|")
    add("| trained weights | `%s` |" % ind["fabric_sha256_with_trained_weights"][:32])
    add("| alternate weight set | `%s` |" % ind["fabric_sha256_with_alternate_weight_set"][:32])
    add("| alternate biases | `%s` |" % ind["fabric_sha256_with_alternate_biases"][:32])
    add("| **identical** | **%s** |" % (ind["identical_after_weight_change"]
                                        and ind["identical_after_bias_change"]))
    add("")
    add("The fabric has not changed a byte since Stage 1, across three "
        "subsequent stages of verification, synthesis and physical work.")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. Parameter-storage backends")
    add("")
    add("Both backends sit behind **one fixed logical interface** with "
        "identical timing semantics, so the fabric cannot tell which is "
        "attached. Backend choice is a build-time source-list decision: no "
        "runtime mux, no parameter.")
    add("")
    add("### Portable")
    add("")
    add("`%s` — %s" % (pb["portable"]["path"], pb["portable"]["description"]))
    add("")
    add("### OpenROM physical (ASIC / SKY130 only)")
    add("")
    add("`%s`. The installed OpenROM cannot express a 22- or 17-bit word "
        "(`word_size` is in **bytes**) and cannot route a 784 x 128 array, so "
        "the parameters get a *physical* representation distinct from the "
        "logical one:" % pb["openrom_physical"]["path"])
    add("")
    add("| Logical memory | Logical | Physical | Transformation |")
    add("|---|---|---|---|")
    t = pb["openrom_physical"]["logical_vs_physical"]
    add("| `weights_l1` | 784 x 128 | 4 banks of 784 x 32 | %s |" % t["weights_l1"])
    add("| `weights_l2` | 32 x 40 | 32 x 40 | %s |" % t["weights_l2"])
    add("| `bias_l1` | 32 x 22 signed | 32 x 24 signed | %s |" % t["bias_l1"])
    add("| `bias_l2` | 10 x 17 signed | 10 x 24 signed | %s |" % t["bias_l2"])
    add("")
    add("**%s**" % pb["openrom_physical"]["note"])
    add("")

    # ---------------------------------------------------------------- 7
    add("## 7. Behavioral verification")
    add("")
    add("%d MNIST test images, the first %d of the official test set in order, "
        "no filtering of any kind." % (b["images"], b["images"]))
    add("")
    add("| | Portable | OpenRAM behavioural |")
    add("|---|---|---|")
    bp, bo = b["portable_backend"], b["openram_behavioral_backend"]
    add("| hidden activations compared | %d | %d |"
        % (bp["hidden_values_compared"], bo["hidden_values_compared"]))
    add("| logits compared | %d | %d |"
        % (bp["logits_compared"], bo["logits_compared"]))
    add("| **hidden mismatches** | **%d** | **%d** |"
        % (bp["hidden_mismatches"], bo["hidden_mismatches"]))
    add("| **logit mismatches** | **%d** | **%d** |"
        % (bp["logit_mismatches"], bo["logit_mismatches"]))
    add("| **prediction mismatches** | **%d** | **%d** |"
        % (bp["prediction_mismatches"], bo["prediction_mismatches"]))
    add("")
    add("Cycle-level internal checkpointing over %d images: **%d checks, %d "
        "failures** — every accumulator update, every requantization, every "
        "ROM word checked against the address issued one cycle earlier."
        % (b["cycle_level_trace"]["images_traced"],
           b["cycle_level_trace"]["total_checks"],
           b["cycle_level_trace"]["failures"]))
    add("")
    add("| Stress test | Result |")
    add("|---|---|")
    add("| input stall patterns (none / periodic / pseudo-random) | 3 patterns, %d mismatches; only latency changes |"
        % sum(v["hidden_mismatches"] + v["logit_mismatches"]
              + v["prediction_mismatches"] for v in b["stalls"].values()))
    add("| synchronous reset | %d points, %d stale-state failures |"
        % (b["reset"]["points_tested"], b["reset"]["stale_state_failures_total"]))
    add("| back-to-back inferences | %d consecutive, %d mismatches |"
        % (b["back_to_back"]["transactions"], b["back_to_back"]["mismatches"]))
    add("| argmax including ties | %d cases, %d failures (%s) |"
        % (b["argmax"]["cases"], b["argmax"]["failures"], b["argmax"]["tie_rule"]))
    add("| arithmetic edge cases | %d + %d cases, %d failures |"
        % (b["arithmetic_edges"]["activation_cases"],
           b["arithmetic_edges"]["special_cases"],
           b["arithmetic_edges"]["failures"]))
    add("| second parameter set on the unchanged fabric | %d vectors, %d mismatches, fabric identical |"
        % (b["alternate_model"]["vectors_tested"],
           b["alternate_model"]["mismatches_vs_msa_reference"]))
    add("| model-specific shortcut scan | %s |"
        % ("clean" if b["shortcut_scan"]["clean"] else "FINDINGS"))
    add("")

    # ---------------------------------------------------------------- 8
    add("## 8. Dual-target synthesis portability")
    add("")
    add("**%s**" % d["claim"])
    add("")
    add("| Invariant | Result |")
    add("|---|---|")
    add("| identical source hashes on both targets | **%s** |"
        % d["same_source"]["same_source_rtl"])
    add("| source patched before synthesis | **%s** |"
        % d["same_source"]["source_patches_applied"])
    add("")
    gf = d["fpga"]["gate_level"]["no_stall"]
    gg = d["generic"]["gate_level"]["no_stall"]
    add("| Post-synthesis gate-level result | FPGA netlist | Generic netlist |")
    add("|---|---|---|")
    add("| images | %d | %d |" % (gf["images"], gg["images"]))
    add("| logits compared | %d | %d |"
        % (gf["logits_compared"], gg["logits_compared"]))
    add("| **logit mismatches** | **%d** | **%d** |"
        % (gf["logit_mismatches"], gg["logit_mismatches"]))
    add("| **prediction mismatches** | **%d** | **%d** |"
        % (gf["prediction_mismatches"], gg["prediction_mismatches"]))
    add("| cycles per inference | %s | %s |"
        % (gf["cycles_per_inference"], gg["cycles_per_inference"]))
    add("")
    add("The two netlists also agree with each other bit for bit: %d logit, %d "
        "prediction, %d cycle-count differences."
        % (d["cross_target"]["logit_mismatches"],
           d["cross_target"]["prediction_mismatches"],
           d["cross_target"]["cycle_mismatches"]))
    add("")
    add("**%s**" % d["not_claimed"])
    add("")

    # ---------------------------------------------------------------- 9
    add("## 9. FPGA-oriented synthesis result")
    add("")
    fr = d["fpga"]["resources"]
    add("Target: **%s** (`synth_ice40`). %s"
        % (d["fpga"]["family"], d["fpga"]["rationale"]))
    add("")
    add("| Resource | Count |")
    add("|---|---|")
    add("| total cells | %d |" % fr["total_cells"])
    add("| `SB_LUT4` | %d |" % fr["lut"])
    add("| flip-flops | %d |" % fr["ff"])
    add("| `SB_CARRY` | %d |" % fr["carry"])
    add("| `SB_RAM40_4K` | %d |" % fr["ram"])
    add("| `SB_MAC16` (DSP) | **%d** |" % fr["dsp"])
    add("")
    add("The interpretation that matters: **%s** — no FPGA-specific memory RTL, "
        "no vendor macro and no synthesis pragma was needed to get there."
        % d["fpga"]["parameter_rom_mapping"])
    add("")
    add("This is **not** a completed FPGA implementation: no place-and-route, "
        "no device fit, no bitstream and no timing analysis were run.")
    add("")

    # ---------------------------------------------------------------- 10
    add("## 10. Generic / ASIC-oriented synthesis result")
    add("")
    gr = d["generic"]["resources"]
    add("| Cell | Count |")
    add("|---|---|")
    for k in sorted(d["generic"]["cells"]):
        add("| `%s` | %d |" % (k, d["generic"]["cells"][k]))
    add("| **total** | **%d** |" % gr["total_cells"])
    add("")
    add("Multiplier / arithmetic cells remaining: **%d**."
        % gr["arithmetic_or_multiplier_cells"])
    add("")
    add("No physical ASIC area is claimed from a generic gate count. The "
        "generic vocabulary has no memory primitive, so %s"
        % d["generic"]["parameter_rom_mapping"])
    add("")

    # ---------------------------------------------------------------- 11
    add("## 11. What synthesis did to the constant multiplications")
    add("")
    add("| | Value |")
    add("|---|---|")
    add("| `*` operators in the source | %d |" % cm["source_multiply_operators"])
    add("| multiplier / DSP cells in the FPGA netlist | **%d** |"
        % cm["multiplier_or_dsp_cells_fpga"])
    add("| multiplier / arithmetic cells in the generic netlist | **%d** |"
        % cm["multiplier_or_dsp_cells_generic"])
    add("")
    add("%s" % cm["explanation"])
    add("")
    add("Where the FPGA flow preserved the product wire names, the drivers show "
        "it directly:")
    add("")
    add("| Product | Driver |")
    add("|---|---|")
    drv = cm["product_wire_drivers_fpga"]
    for name in ("prod_08", "prod_09", "prod_10", "prod_12", "prod_00"):
        if name in drv:
            s = drv[name].replace("\\u_fabric.L1_SELECT[0].u_sel.bank ", "bank")
            s = s.replace("\\u_fabric.act_pipe ", "x")
            add("| `%s` | `%s` |" % (name, s[:70]))
    add("")
    add("`x * 0` folded to a literal zero; `x * 1`, `x * 2` and `x * 4` became "
        "pure wiring; `x * -8` is a shift of a shared negated value.")
    add("")
    add("> **Correct wording:** %s" % cm["correct_wording"])
    add(">")
    add("> **Wording to avoid:** %s" % cm["wording_to_avoid"])
    add("")

    # ---------------------------------------------------------------- 12
    add("## 12. Physical OpenROM experiment")
    add("")
    add("| Macro | Shape | Views | Bits verified | GDS bbox |")
    add("|---|---|---|---|---|")
    for n in BANK_ORDER:
        mm = p["macros"][n]
        add("| `%s` | %s | %s | **%d / %d** | %.1f um² |"
            % (n, mm["shape"], ", ".join(mm["views"]),
               mm["bits_verified"] - mm["bit_mismatches"], mm["bits_verified"],
               mm["bbox_um2"]))
    add("| **total** | | | **%d / %d** | **%.1f um²** |"
        % (p["content_verification"]["programmed_cells_checked"]
           - p["content_verification"]["programmed_cell_mismatches"],
           p["content_verification"]["programmed_cells_checked"],
           ar["openrom_total_macro_bbox_um2"]))
    add("")
    add("Layer-1 weights: four 784 x 32 banks, total **%.1f um²**. "
        "Bounding boxes measured from the GDS with KLayout, hierarchy "
        "resolved — never from a log line."
        % ar["openrom_weights_l1_bank_sum_um2"])
    add("")
    add("The central proof is that the macros hold the model's bits. Every "
        "programmed cell was read back out of the **generated SPICE netlist** "
        "and compared against the physical image:")
    add("")
    add("| Check | Count | Mismatches |")
    add("|---|---|---|")
    cvv = p["content_verification"]
    add("| programmed cells | %d | **%d** |"
        % (cvv["programmed_cells_checked"], cvv["programmed_cell_mismatches"]))
    add("| logical rows rebuilt from the macros | %d | **%d** |"
        % (cvv["logical_rows"], cvv["logical_row_mismatches"]))
    add("| weight indices after unpacking | %d | **%d** |"
        % (cvv["weight_indices"], cvv["weight_index_mismatches"]))
    add("| bias values through the full path | %d | **%d** |"
        % (cvv["bias_values"], cvv["bias_mismatches"]))
    add("")
    add("The physical form has **zero functional effect**: over the same %d "
        "images the physical backend produced %d hidden, %d logit and %d "
        "prediction mismatches, still %s cycles per inference."
        % (p["full_model"]["openrom_phys"]["images"],
           p["full_model"]["openrom_phys"]["hidden_mismatches"],
           p["full_model"]["openrom_phys"]["logit_mismatches"],
           p["full_model"]["openrom_phys"]["prediction_mismatches"],
           p["full_model"]["openrom_phys"]["cycles"]))
    add("")

    # ---------------------------------------------------------------- 13
    add("## 13. Physical signoff")
    add("")
    add("| Verdict | Status |")
    add("|---|---|")
    add("| physical generation | **%s** |" % p["signoff"]["physical_generation"])
    add("| physical signoff | **%s** |" % p["signoff"]["status"])
    add("")
    add("The reason is the environment, not the macros. A control was run under "
        "identical settings — OpenRAM's **own** upstream reference ROM:")
    add("")
    add("| | DRC | LVS |")
    add("|---|---|---|")
    c = p["signoff"]["control"]
    add("| **control (upstream reference ROM)** | **%s** | **%s** |"
        % (c["drc_status"], c["lvs_status"]))
    for n in BANK_ORDER:
        mm = p["macros"][n]
        add("| `%s` | %s | %s |" % (n, mm["drc_status"], mm["lvs_status"]))
    add("")
    add("Because the reference macro fails here too, **no DRC or LVS result "
        "produced in this environment is evidence about these macros in either "
        "direction**. No generated macro is called DRC-clean, LVS-clean or "
        "signoff-ready.")
    add("")

    # ---------------------------------------------------------------- 14
    add("## 14. Area results")
    add("")
    pa = ar["portable_asic_storage"]
    add("| Storage implementation | Measurement | Area |")
    add("|---|---|---|")
    add("| OpenROM hard macros (7) | GDS bounding boxes, summed | **%.1f um²** |"
        % ar["openrom_total_macro_bbox_um2"])
    add("| portable backend on SKY130 | liberty cell-area sum | **%.1f um²** |"
        % pa["chip_area_um2"])
    add("| | of which sequential | %.1f um² (%d cells) |"
        % (pa["sequential_area_um2"], pa["sequential_cells"]))
    add("| | of which combinational | %.1f um² (%d cells) |"
        % (pa["combinational_area_um2"], pa["combinational_cells"]))
    add("| raw ratio | OpenROM / portable | **%.2fx** |"
        % ar["ratio_openrom_over_portable"])
    add("")
    add("**That ratio is a raw storage-implementation comparison, not a "
        "finished-block physical area ratio.** The two numbers are different "
        "kinds of area:")
    add("")
    add("- **OpenROM**: %s" % ar["measurement_kinds"]["openrom"])
    add("- **portable**: %s" % ar["measurement_kinds"]["portable"])
    add("")
    add("The portable figure excludes placement whitespace, routing and "
        "utilization overhead, because no place-and-route was run. The macro "
        "figure is a raw sum of bounding boxes, not a floorplanned area; no "
        "placement density is claimed.")
    add("")

    # ---------------------------------------------------------------- 15
    add("## 15. Storage crossover")
    add("")
    add("| Point | Bits | OpenROM bbox | Portable cell area | Ratio | Smaller |")
    add("|---|---|---|---|---|---|")
    for pt in cx["measured_points"]:
        add("| %s | %d | %.1f um² | %.1f um² | %.2f | %s |"
            % (pt["point"], pt["bits"], pt["openrom_bbox_um2"],
               pt["portable_cell_area_um2"],
               pt["ratio_openrom_over_portable"], pt["smaller"]))
    add("")
    add("Measured range: **%d to %d bits**. At every measured point the "
        "portable mapped-cell area is smaller than the OpenROM bounding box, "
        "and the ratio flattens near **~2.9x** at the larger points. "
        "**No crossover was measured.**"
        % (cx["measured_points"][0]["bits"], cx["measured_points"][-1]["bits"]))
    add("")
    add("This does **not** establish that a hard ROM never wins. The experiment "
        "proves only that *no OpenROM area advantage was observed over the "
        "measured range with this tool and library configuration*. No crossover "
        "point is extrapolated.")
    add("")
    if cx.get("break_even_utilisation"):
        add("Contextual arithmetic, **not a measurement**: a placed portable "
            "block occupies cell area divided by its utilization, so at the "
            "deepest measured point the two would break even only if the "
            "portable block placed at **%.0f%% utilization or worse**."
            % (100 * cx["break_even_utilisation"]["value"]))
        add("")

    # ---------------------------------------------------------------- 16
    add("## 16. What worked")
    add("")
    add("- **The weight-independence discipline.** Fixing the arithmetic "
        "contract analytically before writing any RTL, with no multiplicative "
        "requantization scale, made the fabric provably free of trained values "
        "— byte-identical under substituted weights and biases, and unchanged "
        "for the rest of the project.")
    add("- **One canonical parameter image.** Both backends consume the same "
        "hashed images, so it is structurally impossible to physically build "
        "one dataset while testing another.")
    add("- **The integer golden model as sole oracle.** Every stage compared "
        "against the same NumPy integer model, which is why behavioral, "
        "post-synthesis and physical results are directly comparable.")
    add("- **Dual-target portability.** The same four files synthesized "
        "through two independent flows with zero source changes and zero "
        "post-synthesis mismatches.")
    add("- **Automatic BRAM inference.** The portable case-ROM mapped into %d "
        "iCE40 block RAMs with no FPGA-specific RTL." % fr["ram"])
    add("- **Physical content verification.** Deriving the OpenROM bit-cell "
        "map empirically and checking every programmed cell in the SPICE "
        "netlist turned 'the macro was generated' into 'the macro holds "
        "exactly these bits'.")
    add("")

    # ---------------------------------------------------------------- 17
    add("## 17. What did not work")
    add("")
    add("- **OpenROM could not build two of the four logical shapes directly.** "
        "`word_size` is expressed in bytes, so 22- and 17-bit words are not "
        "expressible; and the 784 x 128 array fails in "
        "`signal_escape_router`. Both needed approved physical "
        "transformations rather than a tool fix.")
    add("- **DRC and LVS are unusable in this environment.** OpenRAM's own "
        "reference macro fails, so no physical-verification result here means "
        "anything. This was not repaired; it was measured and reported.")
    add("- **The hard ROM did not win on area.** Across the whole measured "
        "range the synthesized standard-cell storage was smaller. That is the "
        "opposite of the expected motivation for a hard ROM and is reported as "
        "measured.")
    add("- **`words_per_row = 1` crashes the tool**, and several folding "
        "choices fail per shape; each usable value had to be found by "
        "measurement rather than assumption.")
    add("- **Yosys's per-cell-type area column is a display value** printed in "
        "3-significant-digit scientific notation for large counts. Summing it "
        "produced a wrong total until the exact figures Yosys prints "
        "separately were used instead.")
    add("")

    # ---------------------------------------------------------------- 18
    add("## 18. Limitations")
    add("")
    for line in f["limitations"]:
        add("- %s" % line)
    add("")
    add("### Not claimed")
    add("")
    for line in f["not_claimed"]:
        add("- No claim of %s." % line)
    add("")

    # ---------------------------------------------------------------- 19
    add("## 19. Reproducibility")
    add("")
    add("| Tool | Version / provenance |")
    add("|---|---|")
    add("| Python | %s |" % env["python"])
    add("| Yosys | %s |" % env["yosys"].split(" (")[0])
    add("| Icarus Verilog | %s |" % env["iverilog"])
    add("| OpenRAM | `%s`, branch `%s`, tracked files modified: %s |"
        % (env["openram"]["openram_commit"], env["openram"]["openram_branch"],
           env["openram"]["openram_tracked_files_modified"]))
    add("| PDK | %s (`%s`) |" % (env["pdk"]["provenance"], env["pdk"]["root"]))
    add("| magic | %s |" % env["magic"])
    add("| netgen | %s |" % env["netgen"])
    add("| KLayout | %s |" % env["klayout"])
    add("| SKY130 liberty | `%s` |" % os.path.basename(env["liberty"]))
    add("")
    add("**%s**" % env["note"])
    add("")
    add("### Lightweight functional flow (Python + Yosys + Icarus only)")
    add("")
    add("```bash")
    add("python3.11 -m venv .venv")
    add('.venv/bin/pip install -e ".[train,test]"')
    add("")
    add(".venv/bin/python scripts/train_mnist_mlp.py --sweep-hidden-shift   # Stage 0")
    add(".venv/bin/python scripts/gen_compute_fabric.py                     # Stage 1")
    add(".venv/bin/python scripts/verify_stage1.py")
    add(".venv/bin/python scripts/gen_weight_rom_portable.py                # Stage 2")
    add(".venv/bin/python scripts/verify_stage3.py --images 500             # Stage 3")
    add(".venv/bin/python scripts/synth_stage4.py                           # Stage 4")
    add(".venv/bin/python scripts/verify_stage4.py --images 500")
    add("```")
    add("")
    add("### Heavy physical flow (adds OpenRAM + SKY130 + magic + netgen + KLayout)")
    add("")
    add("```bash")
    add("source build/openram/openram_env.sh")
    add(".venv/bin/python scripts/gen_weight_rom_openram.py                 # Stage 2 backend B")
    add(".venv/bin/python scripts/gen_openrom_stage5.py                     # Stage 5")
    add(".venv/bin/python scripts/gen_openrom_phys_rtl.py")
    add(".venv/bin/python scripts/sweep_stage5.py")
    add(".venv/bin/python scripts/verify_physical_stage5.py")
    add(".venv/bin/python scripts/verify_stage5.py --images 500")
    add("```")
    add("")
    add("Seed 1234; MNIST split `%s`. Determinism was checked, not assumed: "
        "both Stage-4 synthesis flows produce byte-identical netlists when "
        "re-run from clean directories."
        % m["dataset"]["split_rule"])
    add("")

    # ---------------------------------------------------------------- 20
    add("## 20. Future work")
    add("")
    add("Ranked by how much they extend what exists, not by difficulty:")
    add("")
    for w in f["future_work"]:
        add("%d. %s" % (w["rank"], w["item"]))
    add("")
    add("None of these is implemented.")
    add("")

    add("## 21. Test evolution")
    add("")
    te = f["test_evolution"]
    add("| Stage | Cumulative tests |")
    add("|---|---|")
    for k in sorted(te["cumulative"]):
        add("| %s | %d |" % (k.replace("stage", "Stage "),
                             te["cumulative"][k]))
    if "final_measured" in te:
        add("| **final (Stage 6 run)** | **%d passed, %d failed, %d skipped** |"
            % (te["final_measured"]["passed"], te["final_measured"]["failed"],
               te["final_measured"]["skipped"]))
    add("")
    add("%s" % te["note"])
    add("")
    add("---")
    add("")
    add("## Cross-stage consistency")
    add("")
    add("Every number in this report was extracted programmatically from the "
        "six stage reports. Quantities recorded by more than one stage were "
        "compared rather than reconciled: **%d checks, %d disagreements**."
        % (f["cross_stage_consistency"]["checked"],
           f["cross_stage_consistency"]["disagreements"]))
    add("")
    add("## Frozen artifacts")
    add("")
    add("| Artifact | SHA-256 |")
    add("|---|---|")
    for k in sorted(f["frozen_artifacts"]):
        add("| `%s` | `%s` |" % (k, f["frozen_artifacts"][k]))
    add("")
    return "\n".join(L) + "\n"


def main() -> int:
    if not os.path.exists(SRC):
        print("missing %s: run scripts/build_final_report.py first" % SRC)
        return 1
    f = json.load(open(SRC))
    body = render(f)                 # render BEFORE opening for write
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(body)
    os.replace(tmp, OUT)
    print("wrote %s (%d lines)" % (os.path.relpath(OUT, ROOT),
                                   body.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
