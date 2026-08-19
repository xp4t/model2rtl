#!/usr/bin/env python3
"""Stage 6: regenerate the README entry point from reports/final_report.json.

Everything above the first appendix is generated here.  The appendices, and the
marker-delimited results blocks inside them, are left exactly as the per-stage
renderers wrote them.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reports", "final_report.json")
README = os.path.join(ROOT, "README.md")
SPLIT = "## Appendix A —"


def n(x):
    """Thousands separators: these tables are read by humans."""
    return "{:,}".format(x)


def render(f: dict) -> str:
    m, q, a = f["model"], f["quantization"], f["architecture"]
    d = f["dual_target_portability"]
    b = f["behavioral_verification"]
    p = f["physical_openrom"]
    ar, cx = f["area"], f["crossover"]
    fr, gr = d["fpga"]["resources"], d["generic"]["resources"]
    gf = d["fpga"]["gate_level"]["no_stall"]
    gg = d["generic"]["gate_level"]["no_stall"]
    oc = a["operation_counts"]
    L = []
    add = L.append

    add("# model2rtl")
    add("")
    add("**Compile a quantized neural network into portable synthesizable "
        "RTL.**")
    add("")
    add("```")
    add("MNIST  %s" % m["topology"])
    add("       %d-bit weight indices, %d fixed levels"
        % (q["weight_index_bits"], len(q["weight_alphabet"])))
    add("       uint8 activations")
    add("       %d shared constant-weight products per activation"
        % oc["implemented_active_shared_product_expressions"])
    add("       Verilog-2001, no vendor primitives")
    add("       FPGA-oriented and generic/ASIC-oriented synthesis, same source")
    add("       %d-image post-synthesis verification on both, zero mismatches"
        % gf["images"])
    add("```")
    add("")
    add("%s" % f["claim"])
    add("")
    add("> **Scope.** %s" % f["claim_scope"])
    add("")

    add("## Results")
    add("")
    add("| Metric | Result |")
    add("|---|---|")
    add("| Float MNIST test accuracy | %.2f%% |"
        % (100 * m["float_test_accuracy"]))
    add("| Quantized integer test accuracy | %.2f%% |"
        % (100 * m["quantized_integer_test_accuracy"]))
    add("| Behavioral RTL vs integer golden model | **%d mismatches** |"
        % (b["portable_backend"]["hidden_mismatches"]
           + b["portable_backend"]["logit_mismatches"]
           + b["portable_backend"]["prediction_mismatches"]))
    add("| Behavioral verification images | %d |" % b["images"])
    add("| Cycle-level internal trace checks | %s, %d failures |"
        % (n(b["cycle_level_trace"]["total_checks"]),
           b["cycle_level_trace"]["failures"]))
    add("| FPGA post-synthesis gate-level | %d images, **%d mismatches** |"
        % (gf["images"], gf["logit_mismatches"] + gf["prediction_mismatches"]))
    add("| Generic post-synthesis gate-level | %d images, **%d mismatches** |"
        % (gg["images"], gg["logit_mismatches"] + gg["prediction_mismatches"]))
    add("| Nominal cycles per inference | %d |" % a["latency"]["nominal_cycles"])
    add("| Fabric active shared product alternatives | %d |"
        % oc["implemented_active_shared_product_expressions"])
    add("| iCE40 `SB_MAC16` (DSP) | **%d** |" % fr["dsp"])
    add("| iCE40 `SB_LUT4` | %s |" % n(fr["lut"]))
    add("| iCE40 flip-flops | %s |" % n(fr["ff"]))
    add("| iCE40 `SB_RAM40_4K` | %d |" % fr["ram"])
    add("| Generic-gate cells | %s |" % n(gr["total_cells"]))
    add("| Generic multiplier/arithmetic cells | **%d** |"
        % gr["arithmetic_or_multiplier_cells"])
    add("| OpenROM physical macro contents | **bit-exact** (%s / %s cells) |"
        % (n(p["content_verification"]["programmed_cells_checked"]
             - p["content_verification"]["programmed_cell_mismatches"]),
           n(p["content_verification"]["programmed_cells_checked"])))
    add("| OpenROM total macro GDS bounding box | %s um² |"
        % n(round(ar["openrom_total_macro_bbox_um2"], 1)))
    add("| Same storage as SKY130 standard cells | %s cells, %s um² |"
        % (n(ar["portable_asic_storage"]["total_cells"]),
           n(round(ar["portable_asic_storage"]["chip_area_um2"], 1))))
    add("| Physical DRC/LVS signoff | **%s** |" % p["signoff"]["status"])
    add("")
    add("Full detail: **[FINAL-REPORT.md](FINAL-REPORT.md)**. Machine-readable: "
        "[`reports/final_report.json`](reports/final_report.json) and "
        "[`reports/results.csv`](reports/results.csv). Every number above was "
        "extracted from the six per-stage reports, not retyped.")
    add("")

    add("## The architecture")
    add("")
    add("Weights are quantized to exactly **K = %d** levels, so every synapse "
        "stores only a %d-bit index. For a given activation `x_i` there are "
        "therefore only %d distinct products it can ever take part in, however "
        "many neurons it feeds."
        % (a["K"], q["weight_index_bits"], a["K"]))
    add("")
    add("```")
    add("                          activation x_i")
    add("                                |")
    add("        +-----------+-----------+-----------+-----------+")
    add("        |           |           |           |           |")
    add("     x_i*-8      x_i*-7       .....       x_i*+6      x_i*+7")
    add("        |           |           |           |           |")
    add("        +-----------+--- 16 shared products -+-----------+")
    add("                                |")
    add("              +-----------+------+------+-----------+")
    add("              |           |             |           |")
    add("           mux j0      mux j1   .....  mux jN    (4-bit weight index")
    add("              |           |             |          selects per synapse)")
    add("            acc0        acc1          accN")
    add("              |           |             |")
    add("              +-----------+-------------+")
    add("                                |")
    add("                          next activation")
    add("```")
    add("")
    add("Execution is **%s**: one activation enters per cycle, every neuron of "
        "the active layer accumulates in parallel, and the same %d-product bank "
        "is reused across all neurons, across input cycles and across both "
        "layers." % (a["execution"], a["K"]))
    add("")
    add("Three counts are easy to conflate, so they are kept apart — **all "
        "three are source-level operation counts, none is a physical "
        "multiplier count**:")
    add("")
    add("| | Count |")
    add("|---|---|")
    add("| naive fully spatial synapse multiplications | %s |"
        % n(oc["naive_fully_spatial_synapse_multiplications"]))
    add("| fully spatial MSA product generators | %s |"
        % n(oc["fully_spatial_msa_product_generators"]))
    add("| **implemented** active shared product expressions | **%d** |"
        % oc["implemented_active_shared_product_expressions"])
    add("")
    add("Area and parallelism are traded for latency: **%d cycles** per "
        "inference instead of one." % a["latency"]["nominal_cycles"])
    add("")
    add("After synthesis there are **%d multiplier or DSP cells left in either "
        "netlist**. Each product has a fixed small constant operand, so "
        "synthesis turns them into wiring, shifts, negation and LUT/carry "
        "logic. The honest statement is: *%s*"
        % (d["fpga"]["resources"]["dsp"], f["constant_multiplication"]
           ["correct_wording"]))
    add("")

    add("## Parameter flow")
    add("")
    add("```")
    add("   trained model  (Stage 0, quantization-aware training)")
    add("        |")
    add("   4-bit weight-index image + integer biases")
    add("        |")
    add("   canonical parameter images        <- one hashed source of truth")
    add("        |")
    add("   +----+-----------------------+")
    add("   |                            |")
    add("   portable Verilog ROM      OpenROM physical macros (SKY130)")
    add("   (FPGA + ASIC)             (ASIC only; banked + byte-padded)")
    add("   |                            |")
    add("   +----+-----------------------+")
    add("        |")
    add("   ONE fixed logical parameter interface")
    add("        |")
    add("   the SAME unchanged compute fabric")
    add("```")
    add("")
    add("The fabric contains **no trained value**. Regenerating it with a "
        "different weight set and different biases produces a byte-identical "
        "file, so the compute architecture and the model are genuinely "
        "separable. The fabric has not changed a byte since Stage 1:")
    add("")
    add("```")
    add("rtl/mnist_mlp_fabric.v  %s" % f["rtl"]["fabric"]["sha256"])
    add("```")
    add("")
    add("Backend choice is a build-time source-list decision — no runtime mux, "
        "no parameter. Compile exactly one selector file:")
    add("")
    add("```bash")
    add("# portable (FPGA or ASIC)")
    add("rtl/mnist_mlp_top.v rtl/mnist_mlp_fabric.v \\")
    add("  rtl/mnist_mlp_params_portable.v rtl/mnist_mlp_params_sel_portable.v")
    add("")
    add("# physical OpenROM organisation (ASIC / SKY130)")
    add("rtl/mnist_mlp_top.v rtl/mnist_mlp_fabric.v \\")
    add("  rtl/mnist_mlp_params_openrom_phys.v \\")
    add("  rtl/mnist_mlp_params_sel_openrom_phys.v")
    add("```")
    add("")

    add("## Status")
    add("")
    add("| Stage | Scope | Status |")
    add("|---|---|---|")
    ss = f["stage_status"]
    add("| 0 | training, quantization, integer golden model, arithmetic contract | **%s** |" % ss["stage0_quantization"])
    add("| 1 | weight-independent Multiply-Select-Add compute fabric | **%s** |" % ss["stage1_compute_fabric"])
    add("| 2 | two interchangeable parameter-storage backends | **%s** |" % ss["stage2_parameter_backends"])
    add("| 3 | behavioral RTL verification | **%s** |" % ss["stage3_behavioral_verification"])
    add("| 4 | dual-target synthesis portability + gate-level verification | **%s** |" % ss["stage4_dual_target_portability"])
    add("| 5 | physical OpenROM generation | **%s** |" % ss["stage5_physical_generation"])
    add("| 5 | physical DRC/LVS signoff | **%s** |" % ss["stage5_physical_signoff"])
    add("| 6 | final report and consolidation | **PASS** |")
    add("")
    add("Stage 2 closed as PARTIAL because two of the four logical memory "
        "shapes could not be built by the installed OpenROM at the time; "
        "Stage 5 completed them. The Stage-2 verdict is left as recorded.")
    add("")
    add("### What does not exist")
    add("")
    add("- **No DRC or LVS signoff.** OpenRAM's *own* upstream reference ROM "
        "fails in this environment (%s, LVS %s), so no physical-verification "
        "result here is evidence about these macros in either direction. No "
        "macro is called clean."
        % (p["signoff"]["control"]["drc_status"],
           p["signoff"]["control"]["lvs_status"]))
    add("- **No place-and-route**, on either target: no device fit, no "
        "bitstream, no floorplan, no routing, no full-chip flow.")
    add("- **No timing analysis** anywhere, and no maximum clock frequency. The "
        "50/100 MHz figures in the appendices are cycle counts divided by an "
        "assumed clock.")
    add("- **No floorplanned area and no placement density.** The macro figure "
        "is a raw sum of bounding boxes.")
    add("- **No general model compiler.** MNIST %s only; no convolution, no "
        "ONNX or TFLite ingestion." % m["topology"])
    add("")

    add("## Public prior-art / IP note")
    add("")
    add("%s" % f["prior_art_note"])
    add("")

    add("## The arithmetic contract")
    add("")
    add("The integer specification was fixed **analytically, before any RTL "
        "existed**, and never moved. A pure-NumPy integer model implementing it "
        "is the sole oracle for every stage; Keras float output is a reference "
        "number and was never used to check RTL arithmetic.")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| weight alphabet | `alphabet[i] = i - 8`, i.e. %s |"
        % ", ".join(str(v) for v in q["weight_alphabet"]))
    add("| weight index | %d bits |" % q["weight_index_bits"])
    add("| activations | %s |" % q["activation"])
    add("| product | %s, %d bits |"
        % (q["arithmetic_contract"]["product_signedness"],
           q["widths"]["layer1"]["product_bits"]))
    for ln in ("layer1", "layer2"):
        w = q["widths"][ln]
        add("| %s dot / bias / accumulator | %d / %d / %d bits |"
            % (ln, w["dot_bits"], w["bias_bits"], w["accumulator_bits"]))
    add("| requantization | `%s` |" % q["requantization_rule"])
    add("| rounding | %s |" % q["rounding_rule"])
    add("| prediction | %s |" % q["prediction_rule"])
    add("")
    add("There is **no multiplicative requantization scale anywhere in the "
        "datapath** — the only requantization operator is a fixed power-of-two "
        "shift of %d. That is precisely why no trained value can leak into the "
        "fabric." % q["requantization_shift"])
    add("")

    add("## Repository layout")
    add("")
    add("```")
    add("model2rtl/")
    add("├── FINAL-REPORT.md            the technical report")
    add("├── README.md                  this file")
    add("├── model/                     trained 4-bit indices + integer biases")
    add("├── rtl/                       all GENERATED, all Verilog-2001")
    add("│   ├── mnist_mlp_fabric.v             weight-independent MSA fabric")
    add("│   ├── mnist_mlp_params_portable.v    portable parameter ROM")
    add("│   ├── mnist_mlp_params_openram.v     OpenRAM behavioural backend")
    add("│   ├── mnist_mlp_params_openrom_phys.v physical OpenROM backend")
    add("│   ├── mnist_mlp_params_sel_*.v       build-time backend selectors")
    add("│   └── mnist_mlp_top.v                fabric + selected backend")
    add("├── src/model2rtl/             the compiler and its verification model")
    add("├── scripts/                   one driver per stage, plus renderers")
    add("├── tests/                     the whole verification suite")
    add("├── reports/                   per-stage JSON + final_report.json")
    add("└── build/                     generated artifacts per stage")
    add("    ├── param_images/          canonical parameter images")
    add("    ├── openram/               Stage-2 OpenROM attempts")
    add("    ├── stage4/                synthesized netlists and logs")
    add("    └── stage5/                physical macros, sweep, DRC/LVS")
    add("```")
    add("")
    add("This project is **standalone**. It does not import from, depend on, "
        "reuse code from, or modify `rtl2gdsagi`.")
    add("")

    add("## Reproducing")
    add("")
    add("The functional flow needs only Python, Yosys and Icarus. The physical "
        "flow additionally needs a user-space OpenRAM checkout, the SKY130 PDK, "
        "magic, netgen and KLayout. **The environment is not one-click "
        "portable**; exact versions and paths are in "
        "[FINAL-REPORT.md](FINAL-REPORT.md) section 19.")
    add("")
    add("```bash")
    add("python3.11 -m venv .venv")
    add('.venv/bin/pip install -e ".[train,test]"')
    add("")
    add("# functional flow")
    add(".venv/bin/python scripts/train_mnist_mlp.py --sweep-hidden-shift")
    add(".venv/bin/python scripts/gen_compute_fabric.py")
    add(".venv/bin/python scripts/verify_stage1.py")
    add(".venv/bin/python scripts/gen_weight_rom_portable.py")
    add(".venv/bin/python scripts/verify_stage2.py")
    add(".venv/bin/python scripts/verify_stage3.py --images 500")
    add(".venv/bin/python scripts/synth_stage4.py")
    add(".venv/bin/python scripts/verify_stage4.py --images 500")
    add("")
    add("# physical flow (optional; needs the OpenRAM + SKY130 environment)")
    add("source build/openram/openram_env.sh")
    add(".venv/bin/python scripts/gen_weight_rom_openram.py")
    add(".venv/bin/python scripts/gen_openrom_stage5.py")
    add(".venv/bin/python scripts/gen_openrom_phys_rtl.py")
    add(".venv/bin/python scripts/sweep_stage5.py")
    add(".venv/bin/python scripts/verify_physical_stage5.py")
    add(".venv/bin/python scripts/verify_stage5.py --images 500")
    add("")
    add("# consolidate and test")
    add(".venv/bin/python scripts/build_final_report.py")
    add(".venv/bin/python scripts/render_final_report.py")
    add(".venv/bin/python -m pytest tests -q")
    add("```")
    add("")
    add("Seed 1234; MNIST split `%s`. TensorFlow is a **training-time "
        "dependency only** — the compiler, the integer golden model and every "
        "verification path depend on NumPy alone."
        % m["dataset"]["split_rule"])
    add("")

    add("---")
    add("")
    add("The appendices below are the per-stage results, regenerated from the "
        "stage reports. They are the detailed evidence behind the summary "
        "above; start with [FINAL-REPORT.md](FINAL-REPORT.md) if you want the "
        "narrative.")
    add("")
    return "\n".join(L)


def main() -> int:
    if not os.path.exists(SRC):
        print("missing %s: run scripts/build_final_report.py first" % SRC)
        return 1
    f = json.load(open(SRC))
    text = open(README).read()
    if SPLIT not in text:
        print("README appendix marker %r missing" % SPLIT)
        return 1
    tail = text[text.index(SPLIT):]
    head = render(f)                      # render BEFORE opening for write
    tmp = README + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(head + tail)
    os.replace(tmp, README)
    print("README.md entry point regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
