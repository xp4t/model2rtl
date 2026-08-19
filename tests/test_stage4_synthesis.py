"""Stage 4: both synthesis flows must genuinely succeed.

Exit code 0 is not evidence.  These tests read the recorded Yosys logs,
statistics and JSON netlists and require the design to be fully mapped, free of
blackboxes and latches, and structurally a cell netlist rather than a
behavioural leftover.
"""

import json
import os

import pytest

from model2rtl import stage4_synth as S4

TARGETS = ("fpga", "generic")


@pytest.fixture(scope="module", params=TARGETS)
def target(request, stage4_report):
    return request.param, stage4_report["%s_target" % request.param]


def test_status_pass(target):
    kind, t = target
    assert t["status"] == "PASS"
    assert t["exit_status"] == 0


def test_no_yosys_errors(target):
    kind, t = target
    assert t["check"]["error_lines"] == []


def test_yosys_check_reported_no_problems(target):
    kind, t = target
    assert t["check"]["check_blocks"] >= 1, "no `check` pass ran"
    assert t["check"]["problems_reported"] == 0


def test_no_unresolved_blackboxes(target):
    kind, t = target
    assert t["unresolved_blackboxes"] == []


def test_no_inferred_latches(target):
    kind, t = target
    assert t["resources"]["latches"] == 0
    assert t["check"]["latches_inferred_lines"] == 0
    assert t["check"]["latches_explicitly_not_inferred_lines"] > 0, \
        "the log should show Yosys deciding against latches, not be silent"


def test_no_multiply_driven_or_undriven_nets(target):
    kind, t = target
    assert t["check"]["multiple_driver_lines"] == 0
    assert t["check"]["undriven_net_lines"] == 0
    assert t["check"]["wire_without_driver_lines"] == 0


def test_netlist_non_empty_and_hashed(target, root):
    kind, t = target
    path = os.path.join(root, t["netlist_path"])
    assert os.path.getsize(path) > 0
    assert S4.sha256_file(path) == t["netlist_sha256"]
    assert len(t["netlist_sha256"]) == 64


def test_top_module_and_frozen_port_interface(target):
    kind, t = target
    ev = t["netlist_evidence"]
    assert S4.TOP in ev["modules_defined"]
    assert ev["top_ports"] == S4.TOP_PORTS
    assert ev["top_ports_match_frozen_interface"] is True


def test_netlist_is_structural_not_behavioural(target):
    """A netlist that still contains always/case/arithmetic was not really
    synthesized, and one with $readmemh or an initial block could be pulling
    its parameters in from outside."""
    kind, t = target
    ev = t["netlist_evidence"]
    assert ev["always_blocks"] == 0
    assert ev["case_statements"] == 0
    assert ev["arithmetic_operators"] == 0
    assert ev["contains_readmemh"] is False
    assert ev["contains_initial_block"] is False
    assert ev["cell_instances"] == t["resources"]["total_cells"]


def test_parameters_live_inside_the_netlist(target):
    """The netlist has no port and no file read through which a parameter could
    arrive, so the 102 506 bits of the canonical parameter images must be held
    inside it.  For the FPGA target they sit in block-RAM INIT data."""
    kind, t = target
    ev = t["netlist_evidence"]
    assert ev["top_ports"] == S4.TOP_PORTS
    assert ev["contains_readmemh"] is False
    assert ev["contains_initial_block"] is False
    if kind == "fpga":
        assert ev["ram_init_bits"] >= ev["parameter_image_bits_required"]
        assert ev["ram_init_one_bits"] > 0
    else:
        assert ev["parameter_storage"] == "constant combinational logic"


def test_resource_counts_are_present_and_plausible(target):
    kind, t = target
    r = t["resources"]
    assert r["total_cells"] > 1000
    assert r["other"] == 0, "uncategorised cell types: %s" % r["other_types"]
    if kind == "fpga":
        assert r["lut"] > 0 and r["ff"] > 0
    else:
        assert r["sequential"] > 0 and (r["and"] + r["or"]) > 0


def test_no_multiplier_or_dsp_cells_survived(target):
    """One operand of every product is a fixed alphabet level, so synthesis is
    expected to remove all 16 multipliers.  Verify rather than assume."""
    kind, t = target
    assert t["resources"]["arithmetic_or_multiplier_cells"] == 0
    if kind == "fpga":
        assert t["resources"]["dsp"] == 0
    assert t["constant_multiply"]["multiplier_or_dsp_cells_in_netlist"] == 0


def test_fpga_family_selected_and_justified(stage4_report):
    t = stage4_report["fpga_target"]
    assert t["family"] == "ice40"
    assert "cells_sim.v" in t["family_rationale"]


def test_synthesis_is_deterministic(stage4_report):
    rep = stage4_report["reproducibility"]["repeat_synthesis"]
    for kind in TARGETS:
        assert rep[kind]["exit_status"] == 0
        assert rep[kind]["same_cell_counts"] is True
        assert rep[kind]["identical_to_first_run"] is True


def test_the_two_netlists_are_different_artifacts(stage4_report):
    a = stage4_report["fpga_target"]["netlist_sha256"]
    b = stage4_report["generic_target"]["netlist_sha256"]
    assert a and b and a != b


def test_synthesis_scripts_are_recorded_verbatim(stage4_report):
    for kind in TARGETS:
        t = stage4_report["%s_target" % kind]
        assert t["script"].strip()
        assert S4.sha256_text(t["script"]) == t["script_sha256"]
        assert "write_verilog" in t["script"]


def test_the_two_flows_are_actually_independent(stage4_report):
    """They must share nothing but the read_verilog lines."""
    def cmds(kind):
        s = stage4_report["%s_target" % kind]["script"]
        return {l.split()[0] for l in s.splitlines()
                if l and not l.startswith("read_verilog")}
    assert "synth_ice40" in cmds("fpga")
    assert "synth_ice40" not in cmds("generic")
    assert "abc" in cmds("generic")


def test_target_block_records_the_tool_and_library(target):
    kind, t = target
    assert t["yosys_version"].startswith("Yosys")
    assert os.path.isdir(t["yosys_datdir"])
    assert os.path.isfile(t["simulation_library"])
    assert S4.sha256_file(t["simulation_library"]) \
        == t["simulation_library_sha256"]


def test_parameter_rom_mapping_is_reported(target):
    """The spec asks what the portable ROM actually became."""
    kind, t = target
    assert t["parameter_rom_mapping"]
    if kind == "fpga":
        assert t["inferred_memories"] == t["resources"]["ram"]
        assert "SB_RAM40_4K" in t["parameter_rom_mapping"]
    else:
        assert t["inferred_memories"] == 0
        assert "combinational" in t["parameter_rom_mapping"]
