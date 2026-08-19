#!/usr/bin/env python3
"""Regenerate the 'Stage 5 results' block of README.md from the saved report."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- STAGE5_RESULTS_START -->"
END = "<!-- STAGE5_RESULTS_END -->"

BANK_ORDER = ["weights_l1_b0", "weights_l1_b1", "weights_l1_b2",
              "weights_l1_b3", "weights_l2", "bias_l1", "bias_l2"]


def render(rep: dict) -> str:
    mac = rep["macros"]
    pr = rep["physical_representation"]
    rb = rep["logical_equivalence"]["readback"]
    eq = rep["logical_equivalence"]["backend_bus"]
    fm = rep["full_model"]
    pa = rep["portable_asic_storage"]
    ar = rep["area"]
    cx = rep["crossover"]
    sg = rep["physical_signoff"]
    tc = rep["toolchain"]
    L = []
    add = L.append
    add("")
    add("Stage 5 completes the physical OpenROM parameter backend: every macro")
    add("now exists on disk as GDS, and every bit in it is proved to be the bit")
    add("the Stage-0 integer model uses.")
    add("")
    add("**Physical generation: PASS. Physical signoff: UNVERIFIED.** Those are")
    add("two different claims and this section keeps them apart — see the DRC/LVS")
    add("subsection for why the second one cannot be made here.")
    add("")

    add("### Two representations, one source of truth")
    add("")
    add("The canonical Stage-2 *logical* images stay authoritative and were not")
    add("redefined. Stage 5 adds a *physical* representation derived from them by")
    add("two transformations, both approved and both exactly reversible:")
    add("")
    add("| Logical memory | Logical shape | Physical form | Transformation |")
    add("|---|---|---|---|")
    add("| `weights_l1` | 784 x 128 | 4 macros of 784 x 32 | %s |"
        % pr["transformations"]["weights_l1"])
    add("| `weights_l2` | 32 x 40 | 32 x 40 | %s |"
        % pr["transformations"]["weights_l2"])
    add("| `bias_l1` | 32 x 22 signed | 32 x 24 signed | %s |"
        % pr["transformations"]["bias_l1"])
    add("| `bias_l2` | 10 x 17 signed | 10 x 24 signed | %s |"
        % pr["transformations"]["bias_l2"])
    add("")
    add("Why each one is needed: this OpenROM revision expresses `word_size` in")
    add("**bytes**, so 22-bit and 17-bit words cannot be requested at all, and it")
    add("cannot route the direct 784 x 128 array — `signal_escape_router` fails on")
    add("`clk0`. Neither the logical memories, the bit packing, nor the Stage-1")
    add("fabric interface changed.")
    add("")
    add("| Physical macro | Shape | Logical slice | Image SHA-256 |")
    add("|---|---|---|---|")
    for n in BANK_ORDER:
        p = pr["physical_images"][n]
        add("| `%s` | %d x %d | `%s` `%s` | `%s` |"
            % (n, p["physical_depth"], p["physical_width"],
               p["logical_memory"], p["logical_bit_slice"],
               p["sha256"][:24]))
    add("")
    add("The reverse map is an automated invariant: `decode(physical) ==")
    add("canonical logical image` for **%d / %d rows**, %d mismatches."
        % (pr["roundtrip"]["rows_checked"] - pr["roundtrip"]["mismatches"],
           pr["roundtrip"]["rows_checked"], pr["roundtrip"]["mismatches"]))
    add("")

    add("### The macros")
    add("")
    add("| Macro | Shape | words/row | Array | Runtime | Views | Bits verified | GDS bbox |")
    add("|---|---|---|---|---|---|---|---|")
    for n in BANK_ORDER:
        m = mac[n]
        cv = m["content_verification"]
        add("| `%s` | %s | %d | %d x %d | %.1f s | %s | **%d / %d** | %.2f x %.2f um = **%.1f um²** |"
            % (n, m["requested_shape"], m["words_per_row"], m["array_rows"],
               m["array_cols"], m["runtime_seconds"],
               ", ".join(m["views_generated"]),
               cv["bits_checked"] - cv["bit_mismatches"], cv["bits_checked"],
               m["bbox"]["width_um"], m["bbox"]["height_um"],
               m["bbox"]["area_um2"]))
    add("| **total** | | | | | | **%d / %d** | **%.1f um²** |"
        % (sum(mac[n]["content_verification"]["bits_checked"]
               - mac[n]["content_verification"]["bit_mismatches"]
               for n in BANK_ORDER),
           sum(mac[n]["content_verification"]["bits_checked"]
               for n in BANK_ORDER),
           ar["openrom_total_macro_bbox_um2"]))
    add("")
    add("`words_per_row` is an internal folding choice and was picked from")
    add("measured behaviour, not reused: every attempt is recorded, including")
    add("the failures. For the 784 x 32 banks `words_per_row = 2` fails in")
    add("`signal_escape_router`; 4 and 8 both generate and 4 measured smaller")
    add("(53,669 um² against 56,817 um²). `bias_l2` needed 5 because 2 failed.")
    add("")
    add("Bounding boxes are measured **from the GDS** with KLayout, hierarchy")
    add("resolved — not taken from a log line. The LEF abstract outline is")
    add("recorded alongside as a cross-check and is smaller, because the GDS also")
    add("contains the supply ring and labels.")
    add("")

    add("### The central proof: the GDS holds the model's bits")
    add("")
    add("For every macro, the programmed cells were read back out of the")
    add("**generated SPICE netlist** and compared against the physical image.")
    add("The cell map was derived empirically from the Stage-2 macro, whose")
    add("contents are known, and confirmed on all 1,280 of its bits:")
    add("")
    add("```")
    add("row = addr // words_per_row")
    add("col = bit * words_per_row + addr %% words_per_row   (bit numbered MSB first)")
    add("rom_base_one_cell = 1, rom_base_zero_cell = 0")
    add("```")
    add("")
    add("| Check | Count | Mismatches |")
    add("|---|---|---|")
    add("| programmed bit cells vs the physical image | %d | **%d** |"
        % (sum(mac[n]["content_verification"]["bits_checked"]
               for n in BANK_ORDER),
           sum(mac[n]["content_verification"]["bit_mismatches"]
               for n in BANK_ORDER)))
    add("| logical rows rebuilt from the physical macros | %d | **%d** |"
        % (rb["logical_rows_checked"], rb["logical_row_mismatches"]))
    add("| weight indices after unpacking | %d | **%d** |"
        % (rb["weight_indices_checked"], rb["weight_index_mismatches"]))
    add("| bias values through the full path | %d | **%d** |"
        % (rb["bias_values_checked"], rb["bias_mismatches"]))
    add("| bias special values (0, +1, -1, both extremes, min/max present) | %d | **%d** |"
        % (sum(len(v) for v in rb["bias_special_value_roundtrip"].values()),
           rb["bias_special_value_failures"]))
    add("")
    add("All 784 layer-1 rows reassemble from the four banks, and all")
    add("**25,408 / 25,408** weight indices survive banking unchanged.")
    add("")

    add("### Functional equivalence: the physical form changes nothing")
    add("")
    add("| Comparison | Result |")
    add("|---|---|")
    add("| portable vs canonical image | %d weight + %d bias mismatches |"
        % (eq["vs_canonical_image"]["portable"]["weight_vs_image"],
           eq["vs_canonical_image"]["portable"]["bias_vs_image"]))
    add("| OpenRAM behavioural vs canonical image | %d + %d |"
        % (eq["vs_canonical_image"]["openram"]["weight_vs_image"],
           eq["vs_canonical_image"]["openram"]["bias_vs_image"]))
    add("| **physical wrapper vs canonical image** | **%d + %d** |"
        % (eq["vs_canonical_image"]["openrom_phys"]["weight_vs_image"],
           eq["vs_canonical_image"]["openrom_phys"]["bias_vs_image"]))
    add("| backend to backend, all three pairs | %d |"
        % sum(v["weight"] + v["bias"]
              for v in eq["backend_to_backend"].values()))
    add("")
    add("%d stimulus cycles, %d weight and %d bias comparisons, covering %s."
        % (eq["stimulus_cycles"], eq["weight_comparisons"],
           eq["bias_comparisons"], eq["stimulus_coverage"]))
    add("")
    add("Full model, the same %d MNIST images Stages 3 and 4 used:"
        % fm["openrom_phys"]["images"])
    add("")
    add("| | Physical backend | Portable backend |")
    add("|---|---|---|")
    add("| hidden mismatches | **%d** / %d | **%d** / %d |"
        % (fm["openrom_phys"]["hidden_mismatches"],
           fm["openrom_phys"]["hidden_compared"],
           fm["portable"]["hidden_mismatches"],
           fm["portable"]["hidden_compared"]))
    add("| logit mismatches | **%d** / %d | **%d** / %d |"
        % (fm["openrom_phys"]["logit_mismatches"],
           fm["openrom_phys"]["logits_compared"],
           fm["portable"]["logit_mismatches"],
           fm["portable"]["logits_compared"]))
    add("| prediction mismatches | **%d** | **%d** |"
        % (fm["openrom_phys"]["prediction_mismatches"],
           fm["portable"]["prediction_mismatches"]))
    add("| cycles per inference | %s | %s |"
        % (fm["openrom_phys"]["cycles"], fm["portable"]["cycles"]))
    add("| label accuracy | %.2f%% | %.2f%% |"
        % (100 * fm["openrom_phys"]["label_accuracy"],
           100 * fm["portable"]["label_accuracy"]))
    add("")
    add("Backend to backend: %d hidden, %d logit, %d prediction mismatches. The"
        % (fm["backend_to_backend"]["hidden_mismatches"],
           fm["backend_to_backend"]["logit_mismatches"],
           fm["backend_to_backend"]["prediction_mismatches"]))
    add("four banks share one address and are read in parallel, so the external")
    add("read latency is still one cycle and the inference is still 864 cycles.")
    add("")

    add("### Area")
    add("")
    add("| Storage | Measurement | Area |")
    add("|---|---|---|")
    add("| OpenROM hard macros (7 total) | GDS bounding boxes, summed | **%.1f um²** |"
        % ar["openrom_total_macro_bbox_um2"])
    add("| of which the four `weights_l1` banks | | %.1f um² |"
        % ar["openrom_weights_l1_bank_sum_um2"])
    add("| `mnist_mlp_params_portable.v` on SKY130 | liberty cell area | **%.1f um²** |"
        % pa["chip_area_um2"])
    add("| | of which sequential | %.1f um² (%d cells) |"
        % (pa["sequential_area_um2"], pa["sequential_cells"]))
    add("| | of which combinational | %.1f um² (%d cells) |"
        % (pa["combinational_area_um2"], pa["combinational_cells"]))
    add("")
    add("Library: `%s`, corner %s. %d mapped cells, no blackboxes."
        % (os.path.basename(pa["liberty"]), pa["liberty_corner"],
           pa["total_cells"]))
    add("")
    add("**These are not the same kind of area.** The macro figure is a hard")
    add("block's bounding box, already containing its decoders, column mux,")
    add("precharge and supply ring. The portable figure is a standard-cell area")
    add("sum with no placement utilisation and no routing overhead, because no")
    add("place-and-route was run. The raw macro sum is also not a floorplanned")
    add("area: there is no floorplan, and no placement density is claimed.")
    add("")

    add("### Storage crossover — none was measured")
    add("")
    add("| Point | Bits | OpenROM bbox | Portable cells | Portable cell area | Ratio | Smaller |")
    add("|---|---|---|---|---|---|---|")
    for p in cx["measured_points"]:
        add("| %s | %d | %.1f um² | %d | %.1f um² | %.2f | %s |"
            % (p["point"], p["bits"], p["openrom_bbox_um2"],
               p["portable_cells"], p["portable_cell_area_um2"],
               p["ratio_openrom_over_portable"], p["smaller"]))
    add("")
    add("Both implementations at each point hold **identical deterministic")
    add("contents**, and the OpenROM side of every sweep point had its bits")
    add("verified against the generated netlist the same way the real macros did.")
    add("")
    if cx["smallest_openrom_winning_point"] is None:
        add("%s" % cx["conclusion"])
        add("")
        if cx["break_even_utilisation"]:
            add("For scale rather than as a claim: a placed portable block occupies")
            add("cell area divided by its utilisation, so at the deepest measured")
            add("point the two would only break even if the portable block placed at")
            add("**%.0f%% utilisation or worse**. That is a derived sensitivity, not"
                % (100 * cx["break_even_utilisation"]["value"]))
            add("a measurement.")
    else:
        add("Smallest measured point where the OpenROM macro wins: **%s**."
            % cx["smallest_openrom_winning_point"]["point"])
        add("")
        add("%s" % cx["measured_crossover_interval"])
    add("")

    add("### DRC / LVS: signoff is UNVERIFIED")
    add("")
    add("The local physical-verification environment is not trustworthy for this")
    add("OpenROM revision, and Stage 5 did not try to repair it. A control was")
    add("run under identical settings: %s" % sg["control_description"])
    add("")
    add("| Macro | DRC | LVS |")
    add("|---|---|---|")
    c = sg["control"]
    add("| **control — OpenRAM's own reference ROM** | **%s** | **%s** |"
        % (c.get("drc_status"), c.get("lvs_status")))
    for n in BANK_ORDER:
        r = sg["macro_results"].get(n, {})
        add("| `%s` | %s | %s |" % (n, r.get("drc_status"),
                                    r.get("lvs_status")))
    add("")
    add("The upstream reference macro fails here too, so **no DRC or LVS result")
    add("produced in this environment is evidence about model2rtl's macros** —")
    add("in either direction. Therefore:")
    add("")
    add("| Verdict | Status |")
    add("|---|---|")
    add("| physical generation | **%s** |" % sg["physical_generation"])
    add("| physical signoff | **%s** |" % sg["status"])
    add("")

    add("### Toolchain (unchanged from Stage 2)")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| OpenRAM | `%s` branch `%s` |" % (tc["openram_commit"],
                                            tc["openram_branch"]))
    add("| OpenRAM tracked files modified | %s |"
        % tc["openram_tracked_files_modified"])
    add("| PDK | `%s`, sky130A present: %s |" % (tc["pdk_root"],
                                                 tc["pdk_sky130A_present"]))
    add("| magic | %s |" % tc["magic"])
    add("| netgen | %s |" % tc["netgen"])
    add("| KLayout (area measurement) | %s |" % tc["klayout"])
    add("")

    add("### Not claimed by Stage 5")
    add("")
    for line in rep["not_claimed"]:
        add("- %s" % line)
    add("- No full-chip flow of any kind: the fabric was not placed, nothing was")
    add("  routed, no hard macro was integrated into a floorplan, and")
    add("  `rtl2gdsagi` was not used.")
    add("")
    return "\n".join(L)


def main() -> int:
    rep_path = os.path.join(ROOT, "reports", "stage5_openrom_physical.json")
    if not os.path.exists(rep_path):
        print("missing %s: run scripts/verify_stage5.py first" % rep_path)
        return 1
    rep = json.load(open(rep_path))
    if rep.get("status") != "PASS":
        print("refusing to render a README block for a failing Stage-5 report")
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
    print("README.md Stage-5 results block updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
