"""Stage 4: the portability invariant itself.

The claim is that ONE source tree feeds both targets.  The proof is that the
SHA-256 of every file the FPGA flow read equals the SHA-256 of every file the
generic flow read, and equals the working tree.
"""

import os

import pytest

from model2rtl import stage4_synth as S4


def test_same_source_rtl_on_both_targets(stage4_report):
    p = stage4_report["portability"]
    assert p["same_source_rtl"] is True
    assert p["fpga_source_hashes"] == p["generic_source_hashes"]


def test_every_source_was_read_straight_out_of_rtl(stage4_report):
    """A copy-and-patch flow would show a build-directory path here."""
    for rel in stage4_report["portability"]["sources_read_from"]:
        assert rel.startswith("rtl/"), rel


def test_the_four_production_files_and_only_those(stage4_report):
    assert (sorted(stage4_report["portability"]["sources_read_from"])
            == sorted(S4.PRODUCTION_SOURCES))


def test_both_gate_level_flows_passed(stage4_report):
    p = stage4_report["portability"]
    assert p["fpga_gls"] == "PASS"
    assert p["generic_gls"] == "PASS"


def test_stage4_overall_status(stage4_report):
    assert stage4_report["failures"] == []
    assert stage4_report["status"] == "PASS"


def test_no_unsupported_claims_are_recorded(stage4_report):
    """Stage 4 is synthesis + GLS.  Nothing here may imply P&R or timing."""
    limits = " ".join(stage4_report["limitations"]).lower()
    for phrase in ("no fpga place-and-route", "no fpga timing",
                   "no asic physical implementation", "no asic timing"):
        assert phrase in limits
    assert stage4_report["openrom_physical_backend"].startswith("PARTIAL")
    assert stage4_report["stage5_implemented"] is False
    assert stage4_report["rtl2gdsagi_modified"] is False


def test_area_is_not_claimed_without_a_characterized_library(stage4_report):
    ra = stage4_report["resource_analysis"]
    assert "not available" in ra["physical_area"]
    assert "not synthesized areas" in \
        ra["source_level_baselines"]["caveat"].replace("  ", " ")
