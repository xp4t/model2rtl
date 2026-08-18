"""Both backends, one stimulus stream, cycle-by-cycle comparison."""

import re

import pytest

from model2rtl import sim as SIM
from model2rtl.param_verilog import OPENROM_CONVENTION, emit_openram_backend
from model2rtl.stage2_sim import build_stimulus, expected_outputs
from conftest import require_tool


def test_zero_mismatches_between_backends(equivalence_run):
    r = equivalence_run
    assert r["backend_mismatches"] == 0, r["backend_mismatch_detail"]


def test_zero_mismatches_against_the_canonical_images(equivalence_run):
    r = equivalence_run
    assert r["golden_mismatches"] == 0, r["golden_mismatch_detail"]


def test_no_data_bus_is_ever_undriven_after_the_first_read(equivalence_run):
    assert equivalence_run["undriven_cycles_before_first_read"] == 0


def test_full_address_coverage(equivalence_run, param_images):
    r = equivalence_run
    assert r["logged_cycles"] == r["stimulus_cycles"]
    assert r["weight_comparisons"] == r["stimulus_cycles"]
    assert r["bias_comparisons"] == r["stimulus_cycles"]


def test_stimulus_actually_covers_every_required_case(param_images):
    stim = build_stimulus(param_images)
    seen_w = {(s.wlayer, s.waddr) for s in stim if s.wen}
    seen_b = {(s.blayer, s.baddr) for s in stim if s.ben}
    assert all((0, a) in seen_w for a in range(784))
    assert all((1, a) in seen_w for a in range(32))
    assert all((0, a) in seen_b for a in range(32))
    assert all((1, a) in seen_b for a in range(10))
    # invalid addresses
    assert (0, 1023) in seen_w or (1, 1023) in seen_w
    assert (1, 32) in seen_w and (0, 784) in seen_w
    assert (0, 32) in seen_b and (1, 10) in seen_b
    # enable-deasserted cycles
    assert any(s.wen == 0 and s.ben == 0 for s in stim)
    # layer switching on consecutive cycles
    assert any(stim[i].wlayer != stim[i + 1].wlayer
               and stim[i].wen and stim[i + 1].wen
               for i in range(len(stim) - 1))


def test_hold_semantics_are_modelled_and_checked(param_images):
    stim = build_stimulus(param_images)
    exp_w, _ = expected_outputs(stim, param_images)
    idx = next(i for i in range(1, len(stim))
               if stim[i].wen == 0 and stim[i - 1].wen == 0)
    assert exp_w[idx] == exp_w[idx - 1], "hold semantics not modelled"


def test_openram_wrapper_is_generated_from_the_same_images(param_images,
                                                           openram_rtl):
    assert emit_openram_backend(param_images) == emit_openram_backend(param_images)
    src = open(openram_rtl).read()
    for name in ("weights_l1", "weights_l2", "bias_l1", "bias_l2"):
        assert param_images[name].sha256() in src, \
            "the wrapper does not record the canonical %s hash" % name


def test_openram_wrapper_does_not_claim_openrom_authorship(openram_rtl):
    src = open(openram_rtl).read()
    assert "model2rtl behavioural model" in src
    assert "NOT OpenROM-generated Verilog" in src
    assert not re.search(r"OpenROM[- ]generated Verilog model", src)


def test_openram_wrapper_documents_the_proven_bit_order(openram_rtl):
    src = open(openram_rtl).read()
    assert "BIT REVERSED" in src
    assert "proven empirically" in src


def test_openram_backend_compiles_and_elaborates(openram_rtl, tmp_path):
    require_tool("iverilog")
    require_tool("yosys")
    r = SIM.iverilog_compile([openram_rtl], str(tmp_path / "a.out"),
                             str(tmp_path), std="2001")
    assert r.returncode == 0, r.output
    assert "warning" not in r.output.lower(), r.output
    res = SIM.yosys_check(openram_rtl, "mnist_mlp_params_openram")
    assert res["ok"], res["log"][-3000:]
    assert res["latch_lines"] == []
    assert "Found and reported 0 problems." in res["log"]
