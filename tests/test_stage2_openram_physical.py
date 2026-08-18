"""OpenROM PHYSICAL macro verification.

These checks depend on the SKY130 / OpenRAM installation.  They are marked
`openram_physical` so they can be selected explicitly, and they FAIL -- never
silently skip -- when the build record exists but does not back up its claims.
Running the Stage-2 release command must include them.
"""

import json
import os

import pytest

from model2rtl.param_image import IMAGE_ORDER

pytestmark = pytest.mark.openram_physical

OPENRAM_ROOT = "/home/rithwik/OpenRAM"
PDK_ROOT = "/home/rithwik/pdk"


def test_openram_installation_is_present():
    assert os.path.isdir(OPENRAM_ROOT), "OpenRAM is not installed at %s" % OPENRAM_ROOT
    assert os.path.exists(os.path.join(OPENRAM_ROOT, "rom_compiler.py"))
    assert os.path.isdir(os.path.join(PDK_ROOT, "sky130A")), "sky130A PDK missing"
    assert os.path.isdir(os.path.join(OPENRAM_ROOT, "technology", "sky130",
                                      "gds_lib"))


def test_repo_openram_directory_does_not_shadow_the_python_package(root):
    """The empty project directory must never masquerade as `openram`."""
    import subprocess
    import sys
    code = ("import importlib.util,sys;"
            "s=importlib.util.find_spec('openram');"
            "print('' if s is None else (s.origin or ''))")
    # from a neutral cwd there must be no openram package at all
    r = subprocess.run([sys.executable, "-c", code], cwd="/tmp",
                       capture_output=True, text=True)
    assert r.stdout.strip() == "", \
        "an 'openram' package is importable from a neutral cwd: %r" % r.stdout
    # from the repo root the empty directory DOES shadow it, which is exactly
    # why every OpenROM invocation runs with cwd outside the repo root
    r2 = subprocess.run([sys.executable, "-c", code], cwd=root,
                        capture_output=True, text=True)
    if r2.stdout.strip():
        assert "model2rtl/openram" in r2.stdout, r2.stdout
        gen = open(os.path.join(root, "scripts",
                                "gen_weight_rom_openram.py")).read()
        assert "cwd=outdir" in gen, \
            "the generator must not run OpenROM from the repository root"


def test_smoke_test_was_run_and_produced_every_view(openram_build, root):
    smoke = os.path.join(root, "build", "openram", "smoke", "out")
    assert os.path.isdir(smoke), "the OpenROM smoke test was never run"
    for ext in ("gds", "sp", "lef", "v", "log"):
        p = os.path.join(smoke, "smoke_rom_1kbyte." + ext)
        assert os.path.exists(p) and os.path.getsize(p) > 0, \
            "smoke test did not produce %s" % ext


def test_every_macro_result_is_recorded(openram_build):
    for name in IMAGE_ORDER:
        assert name in openram_build["macros"], \
            "no build record for %s" % name
        assert openram_build["macros"][name]["status"] in ("PASS", "FAIL",
                                                           "BLOCKED")


def test_generated_macros_have_the_files_they_claim(openram_build, root):
    for name, r in openram_build["macros"].items():
        if r["status"] != "PASS":
            continue
        for view, info in r["views"].items():
            p = os.path.join(root, info["path"])
            assert os.path.exists(p), "%s claims %s which is missing" % (name, view)
            assert os.path.getsize(p) == info["bytes"] > 0


def test_rom_input_data_is_bit_identical_to_the_canonical_image(openram_build,
                                                                param_images):
    """Prevents building one dataset while testing another."""
    for name, r in openram_build["macros"].items():
        if r["status"] != "PASS":
            continue
        d = r["rom_data"]
        assert d["canonical_image_sha256"] == param_images[name].sha256()
        assert d["bitstream_matches_canonical_image"] is True
        raw = open(d["path"]).read().strip()
        bits = bin(int(raw, 16))[2:].zfill(len(raw) * 4)
        assert bits == param_images[name].bit_string_msb_first()


def test_generated_geometry_matches_the_request(openram_build, param_images):
    for name, r in openram_build["macros"].items():
        if r["status"] != "PASS":
            continue
        img = param_images[name]
        assert r["requested_depth"] == img.depth
        assert r["requested_width_bits"] == img.width
        assert r["physical_rows"] * r["words_per_row"] == img.depth
        assert r["physical_cols"] == img.width * r["words_per_row"]


def test_blocked_macros_state_the_exact_tool_limitation(openram_build):
    for name, r in openram_build["macros"].items():
        if r["status"] != "BLOCKED":
            continue
        assert "word_size" in r["blocked_reason"]
        assert "BYTES" in r["blocked_reason"]
        assert "proposed_fix_not_implemented" in r


def test_physical_verification_outcome_is_recorded_not_assumed(openram_build):
    for name, r in openram_build["macros"].items():
        if r["status"] != "PASS":
            continue
        pv = r["physical_verification"]
        assert "drc_status" in pv and "lvs_status" in pv
        # a clean exit code is never accepted as DRC/LVS proof
        assert pv["drc_status"] != "assumed"
        assert pv["lvs_status"] != "assumed"
