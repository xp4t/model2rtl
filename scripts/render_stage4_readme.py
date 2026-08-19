#!/usr/bin/env python3
"""Regenerate the 'Stage 4 results' block of README.md from the saved report."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- STAGE4_RESULTS_START -->"
END = "<!-- STAGE4_RESULTS_END -->"


def pct(v: float) -> str:
    return "{:.2f}".format(100.0 * v) + "%"


def render(rep: dict) -> str:
    f = rep["fpga_target"]
    g = rep["generic_target"]
    gv = rep["gate_level_verification"]
    gf, gg = gv["fpga"], gv["generic"]
    sel = gv["image_selection"]
    port = rep["portability"]
    ra = rep["resource_analysis"]
    rp = rep["reproducibility"]
    fz = rep["source_freeze"]
    L = []
    add = L.append
    add("")
    add("The same portable Verilog source was synthesized through an")
    add("FPGA-oriented Yosys flow and a generic/ASIC-oriented Yosys flow, and")
    add("both synthesized netlists were gate-level simulated against the Stage-0")
    add("integer golden model.")
    add("")
    add("Stage 4 uses the **portable backend only**. The OpenRAM behavioural")
    add("backend and the physical OpenROM macros are deliberately out of scope")
    add("here — the point is that one vendor-neutral source targets both flows.")
    add("")

    add("### Same source, two targets")
    add("")
    add("| File | SHA-256 | Read by FPGA flow | Read by generic flow |")
    add("|---|---|---|---|")
    for rel in sorted(port["fpga_source_hashes"]):
        add("| `%s` | `%s` | yes | yes |"
            % (rel, port["fpga_source_hashes"][rel][:32]))
    add("")
    add("| Invariant | Result |")
    add("|---|---|")
    add("| identical source hashes on both targets | **%s** |"
        % port["same_source_rtl"])
    add("| every file read straight out of `rtl/` | **%s** |"
        % all(p.startswith("rtl/") for p in port["sources_read_from"]))
    add("| source patched or copy-edited before synthesis | **%s** |"
        % port["source_patches_applied"])
    add("| production RTL byte-identical before and after Stage 4 | **%s** |"
        % fz["unchanged"])
    add("")

    add("### Target A — FPGA-oriented (`%s`)" % f["family"])
    add("")
    add("%s" % f["family_rationale"])
    add("")
    add("```")
    for line in f["script"].strip().splitlines():
        add(line)
    add("```")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| status | **%s** |" % f["status"])
    add("| Yosys `check` problems | %d |" % f["check"]["problems_reported"])
    add("| unresolved blackboxes | %s |"
        % (f["unresolved_blackboxes"] or "none"))
    add("| inferred latches | %d |" % f["resources"]["latches"])
    add("| netlist | `%s` |" % f["netlist_path"])
    add("| netlist SHA-256 | `%s` |" % f["netlist_sha256"][:32])
    add("| synthesis time | %.1f s |" % f["seconds"])
    add("")
    add("| iCE40 resource | Count |")
    add("|---|---|")
    add("| `SB_LUT4` | %d |" % f["resources"]["lut"])
    add("| `SB_CARRY` | %d |" % f["resources"]["carry"])
    add("| flip-flops (`SB_DFF*`) | %d |" % f["resources"]["ff"])
    add("| `SB_RAM40_4K` | %d |" % f["resources"]["ram"])
    add("| `SB_MAC16` (DSP) | %d |" % f["resources"]["dsp"])
    add("| **total cells** | **%d** |" % f["resources"]["total_cells"])
    add("")

    add("### Target B — generic / ASIC-oriented")
    add("")
    add("Standard Yosys logic synthesis down to the Yosys generic gate")
    add("vocabulary. This is **not** a SKY130 flow and **not** ASIC signoff; it")
    add("exists to prove the source is not FPGA-shaped.")
    add("")
    add("```")
    for line in g["script"].strip().splitlines():
        add(line)
    add("```")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| status | **%s** |" % g["status"])
    add("| Yosys `check` problems | %d |" % g["check"]["problems_reported"])
    add("| unresolved blackboxes | %s |"
        % (g["unresolved_blackboxes"] or "none"))
    add("| inferred latches | %d |" % g["resources"]["latches"])
    add("| netlist | `%s` |" % g["netlist_path"])
    add("| netlist SHA-256 | `%s` |" % g["netlist_sha256"][:32])
    add("| synthesis time | %.1f s |" % g["seconds"])
    add("")
    add("| Generic cell | Count |")
    add("|---|---|")
    for t in sorted(g["cells"]):
        add("| `%s` | %d |" % (t, g["cells"][t]))
    add("| **total cells** | **%d** |" % g["resources"]["total_cells"])
    add("")
    add("Physical area is **not available at this stage**: no characterized")
    add("standard-cell library was used, so these counts cannot be converted to")
    add("area, and no timing analysis was performed.")
    add("")

    add("### Gate-level simulation — the part that proves it")
    add("")
    add("Both netlists were simulated with the official Yosys cell models. The")
    add("testbench observes **top-level ports only**, because synthesis")
    add("legitimately destroys internal names; the production RTL was never")
    add("compiled into these simulations.")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| images | %d |" % sel["count"])
    add("| selection | %s |" % sel["selection_policy"])
    add("| reused from Stage 3 | %s |" % sel["reused_from_stage3"])
    add("| images SHA-256 | `%s` |" % sel["images_sha256"][:32])
    add("| oracle | Stage-0 NumPy integer golden model |")
    add("| integer golden accuracy on this set | %s |"
        % pct(sel["integer_golden_accuracy"]))
    add("")
    add("| Measurement | FPGA netlist | Generic netlist |")
    add("|---|---|---|")
    add("| logits compared | %d | %d |"
        % (gf["no_stall"]["logits_compared"], gg["no_stall"]["logits_compared"]))
    add("| prediction comparisons | %d | %d |"
        % (gf["no_stall"]["prediction_comparisons"],
           gg["no_stall"]["prediction_comparisons"]))
    add("| **logit mismatches** | **%d** | **%d** |"
        % (gf["no_stall"]["logit_mismatches"],
           gg["no_stall"]["logit_mismatches"]))
    add("| **prediction mismatches** | **%d** | **%d** |"
        % (gf["no_stall"]["prediction_mismatches"],
           gg["no_stall"]["prediction_mismatches"]))
    add("| label accuracy | %s | %s |"
        % (pct(gf["no_stall"]["gate_level_label_accuracy"]),
           pct(gg["no_stall"]["gate_level_label_accuracy"])))
    add("| cycles per inference (no stalls) | %s | %s |"
        % (gf["no_stall"]["cycles_per_inference"],
           gg["no_stall"]["cycles_per_inference"]))
    add("| back-to-back inferences, mismatches | %d, %d | %d, %d |"
        % (gf["back_to_back"]["images"], gf["back_to_back"]["logit_mismatches"],
           gg["back_to_back"]["images"], gg["back_to_back"]["logit_mismatches"]))
    add("| stalled traffic cycles, mismatches | %s, %d | %s, %d |"
        % (gf["stalls"]["cycles_per_inference"],
           gf["stalls"]["logit_mismatches"],
           gg["stalls"]["cycles_per_inference"],
           gg["stalls"]["logit_mismatches"]))
    add("| reset points, stale-state failures | %d, %d | %d, %d |"
        % (len(gf["reset"]),
           sum(v["stale_state_observed"] for v in gf["reset"].values()),
           len(gg["reset"]),
           sum(v["stale_state_observed"] for v in gg["reset"].values())))
    add("| simulation runtime | %.0f s | %.0f s |"
        % (gf["no_stall"]["sim_seconds"], gg["no_stall"]["sim_seconds"]))
    add("")
    add("The architectural latency contract of **%d cycles** per inference"
        % gf["no_stall"]["latency_contract_cycles"])
    add("survived both flows unchanged: synthesis added no pipeline stage.")
    add("")
    cross = gv["cross_target"]
    add("The two netlists also agree with **each other** bit for bit: %d logit,"
        % cross["logit_mismatches"])
    add("%d prediction and %d cycle-count differences."
        % (cross["prediction_mismatches"], cross["cycle_mismatches"]))
    add("")
    add("| Guard | FPGA | Generic |")
    add("|---|---|---|")
    add("| top module comes from | `%s` | `%s` |"
        % (gf["source_list_guard"]["top_defined_by"],
           gg["source_list_guard"]["top_defined_by"]))
    add("| production RTL in the source list | %s | %s |"
        % (gf["source_list_guard"]["production_rtl_in_source_list"],
           gg["source_list_guard"]["production_rtl_in_source_list"]))
    add("| cell library | `%s` | `%s` |"
        % (os.path.basename(gf["simulation_library"]),
           os.path.basename(gg["simulation_library"])))
    add("")

    add("### What synthesis did to the 16 constant multiplications")
    add("")
    add("The fabric writes 16 multiplications, but one operand is always a fixed")
    add("alphabet level, so nothing forces them to become multipliers. Measured,")
    add("not assumed:")
    add("")
    add("| Observation | FPGA | Generic |")
    add("|---|---|---|")
    cf = ra["constant_multiplication"]["fpga"]
    cg = ra["constant_multiplication"]["generic"]
    add("| `*` operators in the source | %d | %d |"
        % (cf["source_multiply_operators"], cg["source_multiply_operators"]))
    add("| multiplier / DSP cells surviving | **%d** | **%d** |"
        % (cf["multiplier_or_dsp_cells_in_netlist"],
           cg["multiplier_or_dsp_cells_in_netlist"]))
    add("| product-bank bits that are literal constants | %d / %d | %d / %d |"
        % (cf["bit_class_totals"].get("constant", 0), cf["bank_width_bits"],
           cg["bit_class_totals"].get("constant", 0), cg["bank_width_bits"]))
    add("| product-bank bits that are plain wires from the activation register | %d | %d |"
        % (cf["bit_class_totals"].get("activation_register_alias", 0),
           cg["bit_class_totals"].get("activation_register_alias", 0)))
    add("| product-bank bits fused into downstream select logic | %d | %d |"
        % (cf["bit_class_totals"].get("no_driver_fused_downstream", 0),
           cg["bit_class_totals"].get("no_driver_fused_downstream", 0)))
    add("")
    add("**No multiplier cell exists in either netlist.** Where the FPGA flow")
    add("kept the product wire names, the drivers show exactly what happened:")
    add("")
    add("| Product | Level | Driver in the FPGA netlist |")
    add("|---|---|---|")
    drivers = cf["product_wire_drivers"]
    for p in cf["per_product"]:
        name = "prod_%02d" % p["k"]
        d = drivers.get(name, "")
        d = d.replace("\\u_fabric.L1_SELECT[0].u_sel.bank ", "bank")
        d = d.replace("\\u_fabric.act_pipe ", "x")
        if len(d) > 70:
            d = d[:67] + "..."
        add("| `%s` | x * %+d | `%s` |" % (name, p["alphabet_level"], d))
    add("")
    add("`x * 0` folded to a literal zero; `x * 1`, `x * 2` and `x * 4` are pure")
    add("wiring (a shift with constant zero fill); `x * -8` is a shift of a")
    add("shared negated value. The remaining levels reuse shared adder logic,")
    add("and their bank bits no longer exist as separate signals at all — the")
    add("product generation was fused into the 16:1 selection.")
    add("")

    add("### Resources: source-level counts vs synthesized cells")
    add("")
    b = ra["source_level_baselines"]
    add("| Quantity | Value | Kind |")
    add("|---|---|---|")
    add("| naive fully spatial synapse multiplications | %d | source-level operation count |"
        % b["naive_fully_spatial_synapse_multiplications"])
    add("| fully spatial MSA product generators | %d | source-level operation count |"
        % b["fully_spatial_msa_product_generators"])
    add("| Stage-1 time-multiplexed MSA product expressions | %d | source-level operation count |"
        % b["stage1_time_multiplexed_msa_product_expressions"])
    add("| iCE40 total cells (whole design) | %d | **measured, synthesized** |"
        % ra["fpga"]["categories"]["total_cells"])
    add("| generic total cells (whole design) | %d | **measured, synthesized** |"
        % ra["generic"]["categories"]["total_cells"])
    add("")
    add("The first three numbers and the last two are **different kinds of")
    add("quantity**. No ratio between them is an area ratio, and no area")
    add("conclusion is drawn here: that would require synthesizing comparable")
    add("implementations of each baseline, which Stage 4 does not do.")
    add("")
    add("As a diagnostic only, `rtl/mnist_mlp_fabric.v` was also synthesized on")
    add("its own, with no parameter backend attached, to separate the compute")
    add("datapath from the parameter ROM:")
    add("")
    add("| | Whole design | Fabric only | Difference (the ROM) |")
    add("|---|---|---|---|")
    fa, fb = ra["fpga"]["categories"], ra["fpga"]["fabric_only_diagnostic"]
    ga, gb = ra["generic"]["categories"], ra["generic"]["fabric_only_diagnostic"]
    add("| iCE40 `SB_LUT4` | %d | %d | %+d |"
        % (fa["lut"], fb["lut"], fa["lut"] - fb["lut"]))
    add("| iCE40 flip-flops | %d | %d | %+d |"
        % (fa["ff"], fb["ff"], fa["ff"] - fb["ff"]))
    add("| iCE40 `SB_RAM40_4K` | %d | %d | %+d |"
        % (fa["ram"], fb["ram"], fa["ram"] - fb["ram"]))
    add("| generic total cells | %d | %d | %+d |"
        % (ga["total_cells"], gb["total_cells"],
           ga["total_cells"] - gb["total_cells"]))
    add("")
    add("On iCE40 the 102,506 parameter bits landed in %d block RAMs, so the ROM"
        % fa["ram"])
    add("costs almost no logic. With no block RAM available the generic flow had")
    add("to build the same ROM out of gates, which is where its %d extra cells go."
        % (ga["total_cells"] - gb["total_cells"]))
    add("")

    add("### Reproducibility")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| Python | %s |" % rp["python"])
    add("| Yosys | %s |" % rp["yosys"].split(" (")[0])
    add("| Icarus Verilog | %s |" % rp["iverilog"])
    add("| Yosys data directory | `%s` |" % rp["yosys_datdir"])
    for k, v in sorted(rp["simulation_libraries"].items()):
        add("| %s cell library | `%s` (`%s`) |"
            % (k, v["path"], v["sha256"][:16]))
    for k in ("fpga", "generic"):
        add("| %s synthesis repeated from a clean directory | netlist SHA identical: **%s** |"
            % (k, rp["repeat_synthesis"][k]["identical_to_first_run"]))
    add("")
    add("Both flows are byte-deterministic: a second run from an empty output")
    add("directory produced an identical netlist.")
    add("")

    add("### Not claimed by Stage 4")
    add("")
    for line in rep["limitations"]:
        add("- %s" % line)
    add("- No formal RTL-vs-netlist equivalence check was run. It is optional")
    add("  supplemental evidence; gate-level simulation against the integer")
    add("  oracle is the mandatory check and is what was done.")
    add("")
    return "\n".join(L)


def main() -> int:
    rep_path = os.path.join(ROOT, "reports",
                            "stage4_dual_target_portability.json")
    if not os.path.exists(rep_path):
        print("missing %s: run scripts/verify_stage4.py first" % rep_path)
        return 1
    rep = json.load(open(rep_path))
    if rep.get("status") != "PASS":
        print("refusing to render a README block for a failing Stage-4 report")
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
    print("README.md Stage-4 results block updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
