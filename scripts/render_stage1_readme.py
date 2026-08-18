#!/usr/bin/env python3
"""Regenerate the 'Stage 1 results' block of README.md from the saved report.

Every number in the README block is read from reports/stage1_compute_fabric.json
so nothing can be hand-inflated.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- STAGE1_RESULTS_START -->"
END = "<!-- STAGE1_RESULTS_END -->"


def render(rep: dict) -> str:
    a, ar, v, st, ind = (rep["architecture"], rep["arithmetic"],
                         rep["verification"], rep["structure"],
                         rep["independence"])
    L = []
    add = L.append
    add("")
    add("### Architecture: input-serial / output-parallel Multiply-Select-Add")
    add("")
    add("```")
    add("                      x_i  (one activation at a time)")
    add("                       |")
    add("        +--------------+--------------+")
    add("        |              |              |")
    add("    x_i*a[0]       x_i*a[1]  ...  x_i*a[15]      <- K = 16 SHARED products")
    add("        +--------------+--------------+")
    add("                       |")
    add("      +----------------+----------------+")
    add("      |                |                |")
    add("  16:1 select      16:1 select      16:1 select   <- one per output neuron")
    add("      |                |                |")
    add("   acc[0]           acc[1]     ...   acc[N-1]")
    add("```")
    add("")
    add("One product bank exists in the entire design. It is shared across every")
    add("output neuron of the active layer, reused across input cycles, and reused")
    add("by **both** layers. Yosys elaborates the fabric to exactly")
    add("**%d `$mul` cells** and **%d selector instances** (%d layer-1 + %d layer-2)."
        % (st["elaborated_multiplier_cells"], st["selector_instances"],
           a["selectors"]["layer1"], a["selectors"]["layer2"]))
    add("")
    add("### Three resource baselines — the same arithmetic, three organisations")
    add("")
    add("| Organisation | Product generators | What it costs |")
    add("|---|---|---|")
    add("| 1. Naive fully spatial (one multiplier per synapse) | %d | 1 cycle, largest area |"
        % st["naive_fully_spatial_multipliers"])
    add("| 2. MSA fully spatial (K per input line) | %d | 1 cycle, smaller than naive |"
        % st["msa_fully_spatial_product_generators"])
    add("| 3. **Stage-1 input-serial MSA (implemented)** | **%d** | %d cycles per inference |"
        % (st["stage1_input_serial_product_generators"], a["total_cycles_measured"]))
    add("")
    add("**This is not a free win.** Baseline 3 trades latency for area: one")
    add("inference takes %d cycles instead of one. The Stage-0 operator analysis"
        % a["total_cycles_measured"])
    add("counts a fully *unrolled* design and remains valid as an analytical")
    add("fully-spatial count; it is not superseded by this table. And because every")
    add("product has a constant 4-bit operand, none of these source-level counts is")
    add("a physical multiplier or DSP count. Stage 4 measures synthesized resources.")
    add("")
    add("### Latency (architectural only — no clock frequency is claimed)")
    add("")
    add("| Phase | Cycles |")
    add("|---|---|")
    add("| start accepted | 1 |")
    add("| layer-1 activation streaming | %d |" % a["layer1_input_cycles"])
    add("| layer-1 pipeline drain | 1 |")
    add("| layer-1 finalisation (bias, ReLU, requantise, saturate) | %d |"
        % a["layer1_finalisation_cycles"])
    add("| layer-2 activation streaming | %d |" % a["layer2_input_cycles"])
    add("| layer-2 pipeline drain | 1 |")
    add("| layer-2 finalisation (bias, argmax) | %d |" % a["layer2_finalisation_cycles"])
    add("| done / prediction_valid | 1 |")
    add("| **total, measured in simulation** | **%d** |" % a["total_cycles_measured"])
    add("")
    add("Formula: `%s`. The cycle count is data independent (verified: every image "
        "took the same %d cycles)."
        % (a["total_cycles_formula"], a["total_cycles_measured"]))
    add("")
    add("| Clock | Latency | Inferences/s |")
    add("|---|---|---|")
    add("| 50 MHz | %.2f us | %.0f |"
        % (a["expected_latency_50mhz_us"], a["inferences_per_second_50mhz"]))
    add("| 100 MHz | %.2f us | %.0f |"
        % (a["expected_latency_100mhz_us"], a["inferences_per_second_100mhz"]))
    add("")
    add("These are cycle counts divided by an assumed clock. **No maximum clock")
    add("frequency has been established** — that needs synthesis and timing")
    add("analysis, which is Stage 4.")
    add("")
    add("### Interface")
    add("")
    add("| Port group | Semantics |")
    add("|---|---|")
    add("| `clk`, `rst`, `start` | one clock; `rst` synchronous active high; `start` a one-cycle pulse while idle |")
    add("| `in_ready` / `in_valid` / `in_data[7:0]` | activation stream handshake, exactly 784 transfers in index order |")
    add("| `wmem_en` / `wmem_layer` / `wmem_addr[9:0]` / `wmem_data[127:0]` | weight-index memory, synchronous read, 1-cycle latency |")
    add("| `bmem_en` / `bmem_layer` / `bmem_addr[5:0]` / `bmem_data[21:0]` | bias memory, synchronous read, 1-cycle latency |")
    add("| `busy`, `done`, `prediction_valid`, `prediction[3:0]`, `logits[179:0]` | status and results |")
    add("")
    add("**Memory read semantics (identical for both Stage-2 backends):** an address")
    add("driven during cycle *T* is captured on the posedge ending cycle *T*; the data")
    add("must be presented during cycle *T+1*.")
    add("")
    add("**Weight-word packing:** `weight_index[i][j] = wmem_data[j*4 +: 4]`, where")
    add("`wmem_addr = i` is the input-feature index. This preserves the Stage-0")
    add("orientation `[in_features, out_features]`; neuron 0 occupies the least")
    add("significant nibble. Layer 1 uses bits [127:0], layer 2 uses bits [39:0].")
    add("")
    add("**Bias interface:** option B, indexed read. Chosen over a wide packed port")
    add("because finalisation is already one neuron per cycle, so an indexed read")
    add("costs no extra cycles and keeps the Stage-2 ROM shape identical to the")
    add("weight interface. Biases are model parameters and are **not** compiled into")
    add("the fabric.")
    add("")
    add("### Arithmetic — unchanged from the frozen Stage-0 contract")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| product | signed %d-bit, range [%d, %d] |"
        % (ar["product_bits"], *ar["product_range"]))
    add("| layer-1 accumulator | signed %d-bit (dot %d + bias %d) |"
        % (ar["layer1_accumulator_bits"], ar["layer1_dot_bits"], ar["layer1_bias_bits"]))
    add("| layer-2 accumulator | signed %d-bit (dot %d + bias %d) |"
        % (ar["layer2_accumulator_bits"], ar["layer2_dot_bits"], ar["layer2_bias_bits"]))
    add("| requantisation | `%s` |" % ar["requantization_rule"])
    add("| rounding | %s |" % ar["rounding_rule"])
    add("| saturation | %s |" % ar["saturation_rule"])
    add("| argmax ties | %s |" % ar["argmax_tie_rule"])
    add("")
    add("Signedness is explicit everywhere: the unsigned activation is zero extended")
    add("and `$signed(...)` before the multiply, and each alphabet level is a signed")
    add("12-bit constant, so no implicit unsigned conversion is possible. The ReLU")
    add("result is carried in an unsigned 24-bit temporary purely so the")
    add("requantisation shift is unambiguously logical; the architectural accumulator")
    add("stays signed 23-bit.")
    add("")
    add("### Verification performed")
    add("")
    add("| Check | Result |")
    add("|---|---|")
    add("| Yosys `read_verilog` | %s |" % v["yosys_read_verilog"])
    add("| Yosys `hierarchy -check -top mnist_mlp_fabric` | %s |" % v["yosys_hierarchy_check"])
    add("| Yosys `proc` + `check -assert` | %s |" % v["yosys_check_assert"])
    add("| Yosys inferred latches | %d |" % v["yosys_latches_inferred"])
    add("| Yosys multiply-driven nets | %s |" % v["yosys_multiple_drivers"])
    add("| Yosys undriven nets | %s |" % v["yosys_undriven_nets"])
    add("| Icarus compile, strict `-g2001 -Wall` | %s |" % v["icarus_compile_verilog2001"])
    add("| MNIST images simulated vs the integer golden model | %d |" % v["mnist_images_simulated"])
    add("| logit mismatches | **%d** |" % v["logit_mismatches"])
    add("| prediction mismatches | **%d** |" % v["prediction_mismatches"])
    add("| layer-1 dot products and hidden activations checked | %s |"
        % v["layer1_dot_products_checked"])
    add("| second, unrelated weight set through the same fabric | %d mismatches over %d images |"
        % (v["alternate_weight_set_mismatches"], v["alternate_weight_set_images"]))
    add("| stalled input handshake | %d mismatches, %d cycles (vs %d back-to-back) |"
        % (v["stalled_handshake_mismatches"], v["stalled_handshake_cycles"],
           a["total_cycles_measured"]))
    add("")
    add("The oracle is the **Stage-0 NumPy integer golden model**, never Keras.")
    add("")
    add("### Weight independence (mandatory Stage-1 proof)")
    add("")
    add("The generator reads only topology, K and the frozen arithmetic contract.")
    add("Regenerating the fabric after substituting the trained parameters gives a")
    add("byte-identical file:")
    add("")
    add("| Model parameters present | Fabric SHA-256 | Identical |")
    add("|---|---|---|")
    add("| trained weight indices | `%s` | — |" % ind["fabric_sha256_with_trained_weights"][:32])
    add("| **different random weight set** | `%s` | **%s** |"
        % (ind["fabric_sha256_with_alternate_weight_set"][:32],
           "YES" if ind["identical_after_weight_change"] else "NO"))
    add("| **different biases** | `%s` | **%s** |"
        % (ind["fabric_sha256_with_alternate_biases"][:32],
           "YES" if ind["identical_after_bias_change"] else "NO"))
    add("")
    add("Additionally: the generator is instrumented in tests to prove it never")
    add("opens an `.npz` or anything under `model/`, and every numeric literal in")
    add("the emitted Verilog is checked against the set of architecturally")
    add("explainable constants, so no trained value can hide in it.")
    add("")
    add("### Reproducing Stage 1")
    add("")
    add("```bash")
    add(".venv/bin/python scripts/gen_compute_fabric.py")
    add(".venv/bin/python scripts/verify_stage1.py")
    add(".venv/bin/python scripts/render_stage1_readme.py")
    add(".venv/bin/python -m pytest tests -q")
    add("```")
    add("")
    add("Tool versions used: %s; %s."
        % (rep["meta"].get("iverilog", "iverilog ?"),
           rep["meta"].get("yosys", "Yosys ?")))
    add("")
    return "\n".join(L)


def main() -> int:
    rep_path = os.path.join(ROOT, "reports", "stage1_compute_fabric.json")
    if not os.path.exists(rep_path):
        print("missing %s: run scripts/verify_stage1.py first" % rep_path)
        return 1
    with open(rep_path) as fh:
        rep = json.load(fh)
    if rep.get("status") != "PASS":
        print("refusing to render a README block for a failing Stage-1 report")
        return 1
    readme = os.path.join(ROOT, "README.md")
    text = open(readme).read()
    if START not in text or END not in text:
        print("README markers missing")
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    open(readme, "w").write(head + START + render(rep) + END + tail)
    print("README.md Stage-1 results block updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
