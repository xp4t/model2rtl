"""Stage 5: the physical macros themselves.

Every claim here is checked against a file on disk.  An OpenROM exit code is
never treated as evidence: the views must exist with the recorded hashes, and
the programmed bit cells in the generated SPICE netlist must match the physical
image bit for bit.
"""

import os

import pytest

from model2rtl import openrom as O
from model2rtl import phys_image as P

MACROS = list(P.PHYS_ORDER)


@pytest.fixture(scope="module", params=MACROS)
def macro(request, stage5_report):
    name = request.param
    assert name in stage5_report["macros"], "%s missing from the report" % name
    return name, stage5_report["macros"][name]


def test_every_macro_generated(macro):
    name, m = macro
    assert m["generated"] is True
    assert m["status"] == "PASS"


def test_all_seven_macros_are_present(stage5_report):
    assert sorted(stage5_report["macros"]) == sorted(MACROS)
    assert len(MACROS) == 7


def test_required_views_exist_on_disk_with_the_recorded_hash(macro, root):
    name, m = macro
    for ext in ("gds", "sp", "lvs.sp", "lef", "v"):
        assert ext in m["views"], "%s: no %s view" % (name, ext)
        p = os.path.join(root, m["views"][ext]["path"])
        assert os.path.isfile(p)
        assert os.path.getsize(p) == m["views"][ext]["bytes"] > 0
        assert O.sha256_file(p) == m["views"][ext]["sha256"]


def test_data_image_on_disk_matches_the_physical_image(macro, root,
                                                       physical_images):
    """The file handed to OpenROM must be the canonical physical image."""
    name, m = macro
    p = os.path.join(root, m["data_image"]["path"])
    assert O.sha256_file(p) == m["data_image"]["sha256"]
    assert open(p).read().strip() == physical_images[name].hex_stream().strip()
    assert m["physical_image"]["sha256"] == physical_images[name].sha256()


def test_spice_contents_match_the_physical_image_exactly(macro):
    """The central Stage-5 proof: the GDS/SPICE macro was programmed with the
    same bits the logical model uses."""
    name, m = macro
    cv = m["content_verification"]
    assert cv["exact"] is True
    assert cv["bit_mismatches"] == 0
    assert cv["bits_checked"] == m["physical_image"]["physical_bits"]
    assert cv["first_mismatches"] == []


def test_spice_check_is_re_derivable_from_the_netlist(macro, root,
                                                      physical_images):
    """Re-run the check here rather than trusting the recorded number."""
    name, m = macro
    img = physical_images[name]
    sp = os.path.join(root, m["views"]["sp"]["path"])
    cv = O.verify_spice_content(sp, name, img.rows, img.width,
                                m["words_per_row"])
    assert cv["bit_mismatches"] == 0
    assert cv["bits_checked"] == img.depth * img.width


def test_non_data_cells_are_the_dummy_row(macro):
    name, m = macro
    cv = m["content_verification"]
    assert cv["non_data_cells"] > 0
    assert cv["non_data_cells_all_ones"] is True


def test_words_per_row_was_chosen_from_measured_behaviour(macro):
    """Not reused blindly: every attempt, including failures, is recorded."""
    name, m = macro
    assert m["words_per_row"] >= 2
    attempts = m["words_per_row_attempts"]
    assert attempts, "no attempt record"
    assert attempts[-1]["generated"] is True
    assert attempts[-1]["words_per_row"] == m["words_per_row"]
    for a in attempts[:-1]:
        assert a["generated"] is False


def test_array_geometry_is_consistent(macro):
    name, m = macro
    d, w = (int(x) for x in m["requested_shape"].split(" x "))
    assert m["array_cols"] == w * m["words_per_row"]
    assert m["array_rows"] == -(-d // m["words_per_row"])


def test_bbox_measured_from_the_gds(macro, root):
    name, m = macro
    b = m["bbox"]
    assert "KLayout" in b["source"]
    assert b["n_top_cells"] == 1
    assert b["top_cell"] == name
    assert b["width_um"] > 0 and b["height_um"] > 0
    assert abs(b["area_um2"] - b["width_um"] * b["height_um"]) < 1e-6
    assert b["gds_sha256"] == m["views"]["gds"]["sha256"]


def test_bbox_is_reproducible_from_the_gds_file(stage5_report, root, tmp_path):
    """Measure one macro again rather than trusting the stored number."""
    name = "bias_l1"
    m = stage5_report["macros"][name]
    again = O.gds_bbox(os.path.join(root, m["views"]["gds"]["path"]),
                       str(tmp_path))
    assert abs(again["area_um2"] - m["bbox"]["area_um2"]) < 1e-6


def test_lef_size_recorded_as_a_cross_check(macro):
    name, m = macro
    lef = m["lef_size"]
    assert lef is not None
    assert lef["area_um2"] > 0
    # the abstract outline sits inside the GDS bounding box
    assert lef["area_um2"] <= m["bbox"]["area_um2"]


def test_generated_verilog_is_recorded_but_not_used(macro):
    """OpenROM's own .v is an upstream artefact; its properties are observed,
    and it is never the model2rtl functional backend."""
    name, m = macro
    v = m["generated_verilog_properties"]
    assert "NOT used as the model2rtl functional backend" in v["verdict"]
    for k in ("uses_readmemb", "uses_readmemh", "has_delays", "has_negedge",
              "byte_oriented_interface"):
        assert k in v


def test_the_stage5_backend_does_not_include_openrom_verilog(root):
    src = open(os.path.join(root, "rtl",
                            "mnist_mlp_params_openrom_phys.v")).read()
    assert "$readmem" not in src
    assert "negedge" not in src
    assert "NOT OpenROM-generated Verilog" in src


def test_layer1_banks_all_have_the_same_geometry(stage5_report):
    banks = [stage5_report["macros"]["weights_l1_b%d" % b] for b in range(4)]
    assert len({b["requested_shape"] for b in banks}) == 1
    assert len({b["words_per_row"] for b in banks}) == 1
    assert len({b["bbox"]["area_um2"] for b in banks}) == 1


def test_layer1_banks_hold_different_data(stage5_report):
    """Same shape, four different slices: the hashes must all differ."""
    shas = {stage5_report["macros"]["weights_l1_b%d" % b]["data_image"]["sha256"]
            for b in range(4)}
    assert len(shas) == 4


def test_toolchain_is_the_frozen_installation(stage5_report):
    t = stage5_report["toolchain"]
    assert t["openram_commit"] == "b2b069ce119d1488cbe6883b2240bceb5c7ce29a"
    assert t["openram_branch"] == "stable"
    assert t["openram_tracked_files_modified"] is False
    assert t["pdk_root"] == "/home/rithwik/pdk"
    assert t["pdk_sky130A_present"] is True
