"""Stage 5: the physical transformations must have ZERO functional effect.

Three backends, one canonical image, one fabric.  If banking or byte padding
changed a single value the full-model comparison would not be zero.
"""

import pytest

from model2rtl import phys_image as P


# -- complete readback ------------------------------------------------------

def test_every_logical_row_reconstructed(stage5_report):
    rb = stage5_report["logical_equivalence"]["readback"]
    assert rb["logical_rows_checked"] == 784 + 32 + 32 + 10
    assert rb["logical_row_mismatches"] == 0
    assert rb["per_memory"]["weights_l1"]["rows_checked"] == 784
    assert rb["per_memory"]["weights_l1"]["row_mismatches"] == 0


def test_every_weight_index_survives_banking(stage5_report):
    rb = stage5_report["logical_equivalence"]["readback"]
    assert rb["per_memory"]["weights_l1"]["weight_indices_checked"] == 25088
    assert rb["per_memory"]["weights_l2"]["weight_indices_checked"] == 320
    assert rb["weight_indices_checked"] == 25408
    assert rb["weight_index_mismatches"] == 0


def test_every_bias_survives_padding(stage5_report):
    rb = stage5_report["logical_equivalence"]["readback"]
    assert rb["bias_values_checked"] == 42
    assert rb["bias_mismatches"] == 0
    assert rb["bias_special_value_failures"] == 0


def test_required_special_bias_values_were_tested(stage5_report):
    rb = stage5_report["logical_equivalence"]["readback"]
    for name, bits in (("bias_l1", 22), ("bias_l2", 17)):
        vals = [r["logical"] for r in rb["bias_special_value_roundtrip"][name]]
        for required in (0, 1, -1, (1 << (bits - 1)) - 1, -(1 << (bits - 1))):
            assert required in vals
        edge = rb["bias_edge_values_present"][name]
        assert edge["max_present"] in vals
        assert edge["min_present"] in vals
        assert all(r["exact"] for r in
                   rb["bias_special_value_roundtrip"][name])


def test_readback_has_no_mismatch_of_any_kind(stage5_report):
    assert stage5_report["logical_equivalence"]["readback"]["mismatches"] == 0


# -- three-way bus equivalence ----------------------------------------------

def test_all_three_backends_agree_with_the_canonical_image(stage5_report):
    eq = stage5_report["logical_equivalence"]["backend_bus"]
    assert set(eq["backends"]) == {"portable", "openram", "openrom_phys"}
    for backend, d in eq["vs_canonical_image"].items():
        assert d["weight_vs_image"] == 0, backend
        assert d["bias_vs_image"] == 0, backend


def test_all_three_backends_agree_with_each_other(stage5_report):
    eq = stage5_report["logical_equivalence"]["backend_bus"]
    assert len(eq["backend_to_backend"]) == 3
    for pair, d in eq["backend_to_backend"].items():
        assert d["weight"] == 0, pair
        assert d["bias"] == 0, pair
    assert eq["mismatches"] == 0


def test_bus_comparison_covered_every_address_and_timing_case(stage5_report):
    eq = stage5_report["logical_equivalence"]["backend_bus"]
    assert eq["stimulus_cycles"] >= 784 + 32 + 32 + 10
    assert eq["weight_comparisons"] >= 3 * 784
    assert eq["bias_comparisons"] >= 3 * 42
    assert eq["undriven_cycles_before_first_read"] == 0
    for phrase in ("holds", "layer switches", "invalid addresses",
                   "first/last address"):
        assert phrase in eq["stimulus_coverage"]


# -- full model -------------------------------------------------------------

@pytest.mark.parametrize("backend", ["openrom_phys", "portable"])
def test_full_model_is_exact(stage5_report, backend):
    fm = stage5_report["full_model"][backend]
    assert fm["images"] >= 500
    assert fm["hidden_compared"] == fm["images"] * 32
    assert fm["logits_compared"] == fm["images"] * 10
    assert fm["hidden_mismatches"] == 0
    assert fm["logit_mismatches"] == 0
    assert fm["prediction_mismatches"] == 0
    assert fm["cycles"] == [864]


def test_full_model_backends_agree(stage5_report):
    b = stage5_report["full_model"]["backend_to_backend"]
    assert b["hidden_mismatches"] == 0
    assert b["logit_mismatches"] == 0
    assert b["prediction_mismatches"] == 0


def test_full_model_used_the_stage3_image_set(stage5_report, stage3_report):
    a = stage5_report["full_model"]["test_set"]
    b = stage3_report["test_set"]
    assert a["images_sha256"] == b["images_sha256"]
    assert a["count"] >= 500


# -- the fabric never moved --------------------------------------------------

def test_fabric_is_byte_identical(stage5_report):
    assert (stage5_report["source_freeze"]["after"]["rtl/mnist_mlp_fabric.v"]
            == "7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c")


def test_no_frozen_artifact_changed(stage5_report, root):
    import hashlib
    import os
    fz = stage5_report["source_freeze"]
    assert fz["unchanged"] is True
    assert fz["before"] == fz["after"]
    for rel, want in fz["after"].items():
        with open(os.path.join(root, rel), "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == want, rel


def test_stage2_openram_backend_was_not_edited(stage5_report):
    """The physical organisation went into a NEW file, by design."""
    assert "rtl/mnist_mlp_params_openram.v" in stage5_report["source_freeze"]["after"]
    assert set(stage5_report["stage5_new_rtl"]) == {
        "rtl/mnist_mlp_params_openrom_phys.v",
        "rtl/mnist_mlp_params_sel_openrom_phys.v"}
    assert "frozen" in stage5_report["stage5_new_rtl_note"]


def test_the_new_backend_presents_the_frozen_interface(root):
    """Byte-for-byte the same port list the fabric declares."""
    import re
    from model2rtl import memif
    from model2rtl.fabric import FabricConfig
    memif.verify_against_rtl(os.path.join(root, "rtl", "mnist_mlp_fabric.v"),
                             FabricConfig())
    src = open(os.path.join(root, "rtl",
                            "mnist_mlp_params_openrom_phys.v")).read()
    m = re.search(r"module mnist_mlp_params_openrom_phys \((.*?)\);", src,
                  re.S)
    ports = []
    for line in m.group(1).splitlines():
        line = line.split("//")[0].strip().rstrip(",").strip()
        if line:
            ports.append(line.split()[-1])
    assert ports == ["clk", "wmem_en", "wmem_layer", "wmem_addr", "wmem_data",
                     "bmem_en", "bmem_layer", "bmem_addr", "bmem_data"]


def test_all_banks_read_in_parallel_on_one_address(root):
    """The latency contract: four macros, one address, no serialisation."""
    src = open(os.path.join(root, "rtl",
                            "mnist_mlp_params_openrom_phys.v")).read()
    for b in range(P.L1_BANKS):
        assert "rom_phys_weights_l1_b%d u_wl1_b%d" % (b, b) in src
    # every bank is strobed by the same signal and fed the same address slice
    assert src.count(".cs0(wsel_l1)") == P.L1_BANKS
    assert src.count(".addr0(wmem_addr[9:0])") >= P.L1_BANKS


import os  # noqa: E402  (used by the tests above)
