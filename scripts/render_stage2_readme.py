#!/usr/bin/env python3
"""Regenerate the 'Stage 2 results' block of README.md from the saved report."""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = "<!-- STAGE2_RESULTS_START -->"
END = "<!-- STAGE2_RESULTS_END -->"


def render(rep: dict) -> str:
    iface = rep["interface"]
    imgs = rep["canonical_images"]
    por = rep["portable_backend"]
    env = rep["openram_environment"]
    macros = rep["openrom_macros"]
    summ = rep["openrom_macro_summary"]
    beh = rep["openram_behavioral_model"]
    eq = rep["equivalence"]
    fm = rep["full_model"]
    top = rep["top_level"]
    L = []
    add = L.append
    add("")
    add("Stage 2 supplies the trained parameters to the **unchanged** Stage-1")
    add("fabric through two interchangeable storage backends.")
    add("")
    add("| | Portable backend | OpenRAM/OpenROM backend |")
    add("|---|---|---|")
    add("| RTL | `rtl/mnist_mlp_params_portable.v` | `rtl/mnist_mlp_params_openram.v` |")
    add("| Implementation | pure synthesizable Verilog-2001, `case`/constant lookup | wrapper over four OpenROM-shaped macros |")
    add("| Targets | **FPGA and ASIC** | **ASIC / SKY130 only** — no FPGA portability claimed |")
    add("| Physical macros | not applicable | see the macro table below |")
    add("")
    add("`rtl/mnist_mlp_fabric.v` was **not modified**: its SHA-256 still matches")
    add("the Stage-1 report (`%s`)." % iface["fabric_sha256"][:32])
    add("")
    add("### Memory interface (transcribed from the frozen fabric, not invented)")
    add("")
    add("| Signal | Backend direction | Width | Role |")
    add("|---|---|---|---|")
    add("| `clk` | input | 1 | single clock, shared with the fabric |")
    add("| `wmem_en` / `wmem_layer` / `wmem_addr` / `wmem_data` | in/in/in/out | 1/1/10/128 | weight-index memory |")
    add("| `bmem_en` / `bmem_layer` / `bmem_addr` / `bmem_data` | in/in/in/out | 1/1/6/22 | bias memory |")
    add("")
    add("**Timing (identical for both backends):** %s" % iface["timing_contract"])
    add("")
    add("```verilog")
    for line in iface["capture_model"].splitlines():
        add(line)
    add("```")
    add("")
    add("`src/model2rtl/memif.py` re-parses the fabric's port list and fails")
    add("closed if this description ever drifts from the RTL.")
    add("")
    add("### Canonical parameter images — one source of truth")
    add("")
    add("Both backends are generated from these images and proved against the")
    add("same hashes, so it is impossible to physically build one dataset and")
    add("test another.")
    add("")
    add("| Image | Depth | Width | Bits | SHA-256 |")
    add("|---|---|---|---|---|")
    for n in ("weights_l1", "weights_l2", "bias_l1", "bias_l2"):
        i = imgs[n]
        add("| `%s` | %d | %d | %d | `%s` |"
            % (n, i["depth"], i["width"], i["total_bits"], i["sha256"][:32]))
    add("")
    add("Packing is the Stage-0 orientation `[in_features, out_features]`, not")
    add("transposed: `weight_index[i][j] = wmem_data[j*4 +: 4]`, neuron 0 in the")
    add("least significant nibble. Layer-2 weight words leave `wmem_data[127:40]`")
    add("at zero. Layer-2 biases are **sign extended** from 17 to 22 bits.")
    add("Invalid addresses return all zeros and never alias a valid row.")
    add("")
    add("Full readback: **%s weight indices exact**, layer-1 bias exact: %s,"
        % (por["complete_readback"]["weight_indices_exact"],
           por["complete_readback"]["layer1_bias_exact"]))
    add("layer-2 bias exact: %s, rows %s / %s / %s / %s."
        % (por["complete_readback"]["layer2_bias_exact"],
           por["complete_readback"]["layer1_weight_rows"],
           por["complete_readback"]["layer2_weight_rows"],
           por["complete_readback"]["layer1_bias_rows"],
           por["complete_readback"]["layer2_bias_rows"]))
    add("")
    add("### Backend equivalence")
    add("")
    add("Both backends were instantiated side by side and driven with one")
    add("identical stimulus stream covering every valid address of all four")
    add("memories, plus enable-deasserted holds, layer switching on consecutive")
    add("cycles, first/last addresses, invalid addresses, and an address change")
    add("every cycle.")
    add("")
    add("| Metric | Value |")
    add("|---|---|")
    add("| stimulus cycles | %d |" % eq["stimulus_cycles"])
    add("| weight-bus comparisons | %d |" % eq["weight_comparisons"])
    add("| bias-bus comparisons | %d |" % eq["bias_comparisons"])
    add("| **portable vs OpenRAM mismatches** | **%d** |" % eq["backend_mismatches"])
    add("| **mismatches vs the canonical images** | **%d** |" % eq["golden_mismatches"])
    add("")
    add("### Top level and backend selection")
    add("")
    add("`rtl/mnist_mlp_top.v` instantiates the unchanged fabric plus the abstract")
    add("module `mnist_mlp_params`. **Backend selection is build time only** — no")
    add("runtime mux exists. Compile exactly one selector file:")
    add("")
    add("```")
    add("portable : " + " ".join(top["portable_sources"]))
    add("openram  : " + " ".join(top["openram_sources"]))
    add("```")
    add("")
    add("### Full-model inference (oracle: the Stage-0 integer golden model)")
    add("")
    add("| Backend | Images | Logit mismatches | Hidden mismatches | Prediction mismatches | Accuracy | Cycles |")
    add("|---|---|---|---|---|---|---|")
    for key, label in (("portable", "portable"),
                       ("openram_behavioral", "OpenRAM behavioural")):
        r = fm[key]
        add("| %s | %d | **%d** | **%d** | **%d** | %.4f | %s |"
            % (label, r["images"], r["logit_mismatches"], r["hidden_mismatches"],
               r["prediction_mismatches"], r["accuracy"],
               r["cycles_per_inference"]))
    add("")
    add("Backend-to-backend logit mismatches: **%d**. Inference latency is"
        % fm["backend_to_backend_logit_mismatches"])
    add("unchanged from Stage 1 at 864 cycles for both builds.")
    add("")
    add("### Lint and elaboration")
    add("")
    add("| Target | Yosys `check -assert` | Latches | Multi-driven | Undriven | Icarus `-g2001 -Wall` |")
    add("|---|---|---|---|---|---|")
    for name, lintd in (("portable backend", por["lint"]),
                        ("OpenRAM behavioural backend", beh["lint"]),
                        ("top + portable", top["lint_portable"]),
                        ("top + OpenRAM", top["lint_openram"])):
        add("| %s | %s | %d | %s | %s | %s |"
            % (name, lintd["yosys_check_assert"], lintd["yosys_inferred_latches"],
               lintd["yosys_multiple_drivers"], lintd["yosys_undriven_nets"],
               lintd["icarus_verilog2001"]))
    add("")
    add("### OpenRAM / OpenROM environment (exact paths actually used)")
    add("")
    add("| Item | Value |")
    add("|---|---|")
    add("| source | %s |" % env["openram_source_url"])
    add("| branch | `%s` |" % env["openram_branch"])
    add("| commit | `%s` |" % env["openram_commit"])
    add("| `OPENRAM_HOME` | `%s` |" % env["openram_home"])
    add("| `OPENRAM_TECH` | `%s` |" % env["openram_tech"])
    add("| `PDK_ROOT` | `%s` |" % env["pdk_root"])
    add("| PDK variant | %s |" % env["pdk_variant"])
    add("| PDK provenance | %s |" % env["pdk_provenance"])
    add("| Python | %s |" % env["python"])
    add("| DRC tool | %s |" % env["drc_tool"])
    add("| LVS tool | %s |" % env["lvs_tool"])
    add("| Nix bootstrap | %s |" % env["nix_bootstrap"])
    add("| environment script | `%s` |" % env["env_script"])
    add("")
    add("Nothing was installed system wide, no system Python was modified, and no")
    add("`sudo` was used. OpenRAM is upstream and unmodified.")
    add("")
    sm = env["smoke_test"]
    add("**Smoke test** (%s): generation %s in %ds, views `%s`. "
        % (sm["design"], sm["generation"], sm["elapsed_seconds"],
           ", ".join(sm["views_generated"])))
    add("DRC: **%s**. LVS: **%s**. %s" % (sm["drc_result"], sm["lvs_result"],
                                          sm["note"]))
    add("")
    add("### Proven OpenROM data convention")
    add("")
    add("%s" % summ["data_convention_proven"])
    add("")
    add("Evidence: %s" % summ["convention_evidence"])
    add("")
    add("### OpenROM physical macros")
    add("")
    add("| Macro | Requested | Status | words/row | Physical array | Views generated | DRC | LVS | Runtime |")
    add("|---|---|---|---|---|---|---|---|---|")
    for n in ("weights_l1", "weights_l2", "bias_l1", "bias_l2"):
        m = macros.get(n)
        if not m:
            add("| `%s` | — | not attempted | — | — | — | — | — | — |" % n)
            continue
        req = "%d x %d" % (m["requested_depth"], m["requested_width_bits"])
        if m["status"] != "PASS":
            add("| `%s` | %s | **%s** | — | — | — | — | — | — |"
                % (n, req, m["status"]))
            continue
        pv = m["physical_verification"]
        add("| `%s` | %s | **%s** | %d | %d rows x %d cols | %s | %s | %s | %.1fs |"
            % (n, req, m["status"], m["words_per_row"], m["physical_rows"],
               m["physical_cols"], ", ".join(m["views_generated"]),
               pv.get("drc_status", "?"), pv.get("lvs_status", "?"),
               m["elapsed_seconds"]))
    add("")
    for n in ("weights_l1", "weights_l2", "bias_l1", "bias_l2"):
        m = macros.get(n, {})
        if m.get("status") == "BLOCKED":
            add("- **`%s` is BLOCKED.** %s" % (n, m["blocked_reason"]))
            add("  Proposed fix, *not implemented without approval*: %s."
                % m["proposed_fix_not_implemented"])
        elif m.get("status") == "FAIL":
            add("- **`%s` FAILED to generate.** Last lines of the tool output:"
                % n)
            add("  ```")
            for line in m.get("failure_tail", [])[-4:]:
                add("  " + line)
            add("  ```")
    add("")
    add("### What OpenROM actually generated")
    add("")
    add("For the macros that built, this OpenROM version emits `.gds`, `.sp`,")
    add("`.lvs.sp`, `.lef`, `.v` and a reproduced config `.py`. **It does emit a")
    add("Verilog file**, contrary to its own documentation — but %s"
        % beh["openrom_verilog_note"][beh["openrom_verilog_note"].find("it is a"):])
    add("")
    add("`rtl/mnist_mlp_params_openram.v` therefore contains **our own**")
    add("behavioural read models, labelled in the file as a *model2rtl")
    add("behavioural model of the generated OpenROM contents* — **not** as")
    add("OpenROM-generated Verilog. Their contents are generated from the same")
    add("canonical images that the physical ROM data files carry, and the tests")
    add("check the ROM input data bit-for-bit against those images.")
    add("")
    add("### Limitations")
    add("")
    for lim in rep["limitations"]:
        add("- %s" % lim)
    add("")
    return "\n".join(L)


def main() -> int:
    rep_path = os.path.join(ROOT, "reports", "stage2_parameter_backends.json")
    if not os.path.exists(rep_path):
        print("missing %s: run scripts/verify_stage2.py first" % rep_path)
        return 1
    rep = json.load(open(rep_path))
    if rep.get("status") not in ("PASS", "PARTIAL"):
        print("refusing to render a README block for a failing Stage-2 report")
        return 1
    readme = os.path.join(ROOT, "README.md")
    text = open(readme).read()
    if START not in text or END not in text:
        print("README markers missing")
        return 1
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    open(readme, "w").write(head + START + render(rep) + END + tail)
    print("README.md Stage-2 results block updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
