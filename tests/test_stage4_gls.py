"""Stage 4: gate-level simulation is the part that actually proves anything.

Both synthesized netlists were simulated against the Stage-0 integer golden
model.  These tests read the recorded results and additionally re-exercise the
guard that keeps production RTL out of the gate-level source list -- including
a negative case, so a broken guard cannot pass silently.
"""

import os

import pytest

from model2rtl import stage4_synth as S4

TARGETS = ("fpga", "generic")
NOMINAL_CYCLES = 864


@pytest.fixture(scope="module", params=TARGETS)
def gls(request, stage4_report):
    return (request.param,
            stage4_report["gate_level_verification"][request.param])


# -- the oracle -------------------------------------------------------------

def test_oracle_is_the_stage0_integer_model(stage4_report):
    gv = stage4_report["gate_level_verification"]
    assert "integer golden model" in gv["oracle"]
    assert "NOT used as the oracle" in gv["oracle"]
    assert "integer golden model" in gv["image_selection"]["oracle"]


def test_image_set_is_large_deterministic_and_unfiltered(stage4_report):
    m = stage4_report["gate_level_verification"]["image_selection"]
    assert m["count"] >= 200
    assert "no filtering" in m["selection_policy"]
    assert len(m["indices_sha256"]) == 64
    assert m["reused_from_stage3"] is True


def test_image_set_is_the_stage3_set(stage4_report, stage3_report):
    a = stage4_report["gate_level_verification"]["image_selection"]
    b = stage3_report["test_set"] if "test_set" in stage3_report else None
    if b is None:
        pytest.skip("stage 3 report has no test_set block")
    assert a["images_sha256"] == b["images_sha256"]
    assert a["indices_sha256"] == b["indices_sha256"]


# -- per target -------------------------------------------------------------

def test_no_stall_run_is_exact(gls):
    kind, g = gls
    r = g["no_stall"]
    assert r["images"] >= 200
    assert r["logits_compared"] == r["images"] * 10
    assert r["logit_mismatches"] == 0
    assert r["prediction_mismatches"] == 0
    assert r["testbench_self_checks_passed"] is True


def test_latency_contract_survived_synthesis(gls):
    kind, g = gls
    r = g["no_stall"]
    assert r["cycles_per_inference"] == [NOMINAL_CYCLES]
    assert r["latency_contract_held"] is True


def test_back_to_back_inferences(gls):
    kind, g = gls
    r = g["back_to_back"]
    assert r["images"] >= 10
    assert r["logit_mismatches"] == 0
    assert r["prediction_mismatches"] == 0
    assert r["cycles_per_inference"] == [NOMINAL_CYCLES]
    assert "one" in r["note"].lower()


def test_stall_pattern_changes_cycles_but_not_results(gls):
    kind, g = gls
    r = g["stalls"]
    assert r["logit_mismatches"] == 0
    assert r["prediction_mismatches"] == 0
    assert r["cycles_exceed_nominal"] is True
    assert NOMINAL_CYCLES not in r["cycles_per_inference"]


def test_reset_leaves_no_stale_state(gls):
    kind, g = gls
    assert set(g["reset"]) == {"clean_reset_before_inference",
                               "reset_mid_inference"}
    for label, r in g["reset"].items():
        assert r["stale_state_observed"] is False
        assert r["logit_mismatches"] == 0
        assert r["prediction_mismatches"] == 0
        assert r["cycles_per_inference"] == [NOMINAL_CYCLES]
    assert g["reset"]["reset_mid_inference"][
        "reset_asserted_after_activations"] > 0


def test_accuracy_is_reported_but_is_not_the_pass_criterion(gls):
    kind, g = gls
    acc = g["no_stall"]["gate_level_label_accuracy"]
    assert 0.0 <= acc <= 1.0
    # the pass criterion is zero arithmetic mismatch, which is asserted above
    assert g["no_stall"]["logit_mismatches"] == 0


# -- the netlist really was what got simulated ------------------------------

def test_simulation_used_the_synthesized_netlist(gls, root):
    kind, g = gls
    guard = g["source_list_guard"]
    assert guard["production_rtl_in_source_list"] is False
    assert guard["behavioural_implementation_in_source_list"] is False
    assert guard["top_defined_by"].startswith("build/stage4/")
    assert guard["top_defined_by"] == g["netlist_path"]
    for s in guard["sources"]:
        assert not s.startswith("rtl/"), s


def test_official_cell_library_was_used(gls):
    kind, g = gls
    lib = g["simulation_library"]
    assert os.path.isfile(lib)
    assert S4.sha256_file(lib) == g["simulation_library_sha256"]
    if kind == "fpga":
        assert lib.endswith(os.path.join("ice40", "cells_sim.v"))
    else:
        assert lib.endswith("simcells.v")


def test_guard_rejects_production_rtl(root, tmp_path):
    """Negative case: the guard must actually fire.  Without this, a guard that
    always returned OK would look exactly like a passing one."""
    net = os.path.join(root, "build", "stage4", "fpga", "fpga_netlist.v")
    lib = S4.simlib_paths()["fpga"]
    if not os.path.isfile(net):
        pytest.fail("run scripts/synth_stage4.py first")
    tb = tmp_path / "tb.v"
    tb.write_text("module tb; endmodule\n")

    ok = S4.check_gls_sources([str(tb), net, lib], net, lib, root)
    assert ok["production_rtl_in_source_list"] is False

    bad = os.path.join(root, "rtl", "mnist_mlp_fabric.v")
    with pytest.raises(S4.Stage4Error):
        S4.check_gls_sources([str(tb), net, lib, bad], net, lib, root)


def test_guard_rejects_a_netlist_outside_build_stage4(root, tmp_path):
    lib = S4.simlib_paths()["fpga"]
    fake = tmp_path / "fake_netlist.v"
    fake.write_text("module mnist_mlp_top (clk); input clk; endmodule\n")
    with pytest.raises(S4.Stage4Error):
        S4.check_gls_sources([str(fake), lib], str(fake), lib, root)


# -- both targets agree ------------------------------------------------------

def test_fpga_and_generic_agree_bit_for_bit(stage4_report):
    c = stage4_report["gate_level_verification"]["cross_target"]
    assert c["logit_mismatches"] == 0
    assert c["prediction_mismatches"] == 0
    assert c["cycle_mismatches"] == 0
    assert c["identical"] is True


def test_handshake_and_done_semantics_were_checked(gls):
    kind, g = gls
    assert g["handshake_checks_passed"] is True
    joined = " ".join(g["observable_handshake_checks"]).lower()
    for token in ("done", "prediction_valid", "busy", "in_ready"):
        assert token in joined
