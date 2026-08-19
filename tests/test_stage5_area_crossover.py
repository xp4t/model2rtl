"""Stage 5: measured area, the storage sweep, and honest physical signoff."""

import os

import pytest


# -- macro area -------------------------------------------------------------

def test_total_macro_area_is_the_sum_of_the_measured_boxes(stage5_report):
    a = stage5_report["area"]
    per = a["openrom_per_macro_um2"]
    assert len(per) == 7
    assert abs(sum(per.values()) - a["openrom_total_macro_bbox_um2"]) < 1e-3


def test_layer1_bank_sum_is_reported_separately(stage5_report):
    a = stage5_report["area"]
    per = a["openrom_per_macro_um2"]
    banks = sum(per["weights_l1_b%d" % b] for b in range(4))
    assert abs(banks - a["openrom_weights_l1_bank_sum_um2"]) < 1e-3
    assert banks < a["openrom_total_macro_bbox_um2"]


def test_raw_macro_sum_is_kept_separate_from_floorplan(stage5_report):
    a = stage5_report["area"]
    assert "not available" in a["floorplanned_area"]
    assert "no floorplan" in a["caveat"]
    assert "no placement density is claimed" in a["caveat"]


def test_area_kinds_are_labelled(stage5_report):
    k = stage5_report["area"]["measurement_kinds"]
    assert "bounding box" in k["openrom"]
    assert "liberty cell areas" in k["portable"]
    assert "excludes placement" in k["portable"]
    assert "NOT the same kind of area" in stage5_report["area"]["caveat"]


# -- portable ASIC mapping --------------------------------------------------

def test_portable_storage_mapped_cleanly(stage5_report):
    p = stage5_report["portable_asic_storage"]
    assert p["blackboxes"] == []
    assert p["total_cells"] > 0
    assert p["chip_area_um2"] > 0
    assert p["sequential_cells"] > 0
    # both figures come from the exact lines Yosys prints, never from summing
    # the display values in the stat table
    assert abs(p["sequential_area_um2"] + p["combinational_area_um2"]
               - p["chip_area_um2"]) < 1e-6


def test_portable_mapping_used_the_real_sky130_liberty(stage5_report):
    p = stage5_report["portable_asic_storage"]
    assert os.path.isfile(p["liberty"])
    assert "sky130_fd_sc_hd" in p["liberty"]
    assert "tt" in p["liberty_corner"]
    assert p["top"] == "mnist_mlp_params_portable"


def test_portable_area_carries_its_qualifications(stage5_report):
    q = " ".join(stage5_report["portable_asic_storage"]["qualifications"])
    assert "place and route" in q
    assert "cell-area sum" in q


# -- crossover ---------------------------------------------------------------

def test_sweep_has_several_measured_points(stage5_report):
    pts = stage5_report["crossover"]["measured_points"]
    assert len(pts) >= 5
    bits = [p["bits"] for p in pts]
    assert bits == sorted(bits)
    assert len(set(bits)) == len(bits)


def test_every_sweep_point_measured_both_implementations(stage5_report):
    for p in stage5_report["crossover"]["measured_points"]:
        assert p["openrom_bbox_um2"] > 0, p["point"]
        assert p["portable_cell_area_um2"] > 0, p["point"]
        assert p["portable_cells"] > 0
        assert p["smaller"] in ("openrom", "portable")
        assert abs(p["ratio_openrom_over_portable"]
                   - p["openrom_bbox_um2"] / p["portable_cell_area_um2"]) < 1e-3


def test_sweep_contents_are_deterministic_and_shared(stage5_sweep):
    for key, p in stage5_sweep["points"].items():
        assert "deterministic" in p["contents"]
        assert "identical for both implementations" in p["contents"]
        assert len(p["contents_sha256"]) == 64


def test_sweep_openrom_contents_were_verified_too(stage5_sweep):
    for key, p in stage5_sweep["points"].items():
        if p["openrom"]["generated"]:
            cv = p["openrom"]["content_verification"]
            assert cv["bit_mismatches"] == 0, key


def test_crossover_conclusion_matches_the_measured_data(stage5_report):
    c = stage5_report["crossover"]
    winners = [p for p in c["measured_points"] if p["smaller"] == "openrom"]
    if winners:
        assert c["smallest_openrom_winning_point"] is not None
        assert (c["smallest_openrom_winning_point"]["bits"]
                == min(w["bits"] for w in winners))
    else:
        assert c["smallest_openrom_winning_point"] is None
        assert "none" in c["measured_crossover_interval"]
        assert "extrapolation" in c["conclusion"]


def test_no_extrapolated_crossover_is_asserted(stage5_report):
    c = stage5_report["crossover"]
    assert c["measured_crossover_interval"]
    if c["smallest_openrom_winning_point"] is None:
        assert c["break_even_utilisation"] is not None
        assert "not a measurement" in \
            c["break_even_utilisation"]["meaning"]


# -- physical signoff --------------------------------------------------------

def test_a_control_was_run(stage5_report):
    s = stage5_report["physical_signoff"]
    assert s["control"], "no control result"
    assert "upstream reference" in s["control_description"]
    assert s["control"]["drc_errors"] is not None


def test_signoff_status_follows_the_control(stage5_report):
    s = stage5_report["physical_signoff"]
    clean = (s["control"].get("drc_errors") == 0
             and s["control"].get("lvs_status") == "clean")
    assert s["control_is_clean"] is clean
    assert s["status"] == ("VERIFIED" if clean else "UNVERIFIED")


def test_generation_and_signoff_are_separate_verdicts(stage5_report):
    s = stage5_report["physical_signoff"]
    assert s["physical_generation"] in ("PASS", "FAIL")
    assert s["status"] in ("VERIFIED", "UNVERIFIED")
    # generation passing must not silently imply signoff
    if s["physical_generation"] == "PASS" and not s["control_is_clean"]:
        assert s["status"] == "UNVERIFIED"


def test_every_macro_has_a_recorded_drc_and_lvs_result(stage5_report):
    res = stage5_report["physical_signoff"]["macro_results"]
    assert len(res) == 7
    for name, r in res.items():
        assert r["drc_status"] is not None, name
        assert r["lvs_status"] is not None, name


def test_no_macro_is_claimed_clean(stage5_report):
    s = stage5_report["physical_signoff"]
    if not s["control_is_clean"]:
        joined = " ".join(stage5_report["not_claimed"]).lower()
        assert "drc-clean or lvs-clean" in joined


def test_out_of_scope_things_are_declared(stage5_report):
    assert stage5_report["full_chip_gds"] == "NOT ATTEMPTED"
    assert stage5_report["rtl2gdsagi_used"] is False
    joined = " ".join(stage5_report["not_claimed"]).lower()
    for phrase in ("no full-chip gds", "no timing analysis"):
        assert phrase in joined
