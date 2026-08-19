"""Stage 4 must not change one byte of the production RTL or the model.

Stage 4 is a portability *claim*, not a porting *effort*: if any target had
needed a source tweak the claim would be void.  These tests re-hash the working
tree and compare against what the synthesis flows actually read.
"""

import hashlib
import os

import pytest

from model2rtl import stage4_synth as S4


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def test_report_records_unchanged_sources(stage4_report):
    fz = stage4_report["source_freeze"]
    assert fz["unchanged"] is True
    assert fz["before"] == fz["after"]


def test_frozen_files_still_match_the_working_tree(stage4_report, root):
    for rel, sha in stage4_report["source_freeze"]["after"].items():
        path = os.path.join(root, rel)
        assert os.path.isfile(path), rel
        assert _sha(path) == sha, "%s changed after Stage 4" % rel


def test_production_rtl_is_in_the_freeze(stage4_report):
    frozen = stage4_report["source_freeze"]["after"]
    for rel in S4.PRODUCTION_SOURCES:
        assert rel in frozen


def test_fabric_hash_is_the_stage1_hash(stage4_report):
    """The compute fabric has not moved since Stage 1 and must not move now."""
    assert (stage4_report["source_freeze"]["after"]["rtl/mnist_mlp_fabric.v"]
            == "7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c")


def test_stage0_to_stage3_reports_are_frozen(stage4_report, root):
    frozen = stage4_report["source_freeze"]["after"]
    for n in ("stage0_quantization", "stage1_compute_fabric",
              "stage2_parameter_backends", "stage3_behavioral_verification"):
        rel = "reports/%s.json" % n
        assert rel in frozen
        assert _sha(os.path.join(root, rel)) == frozen[rel]


def test_synthesis_read_the_same_bytes_the_tree_holds(stage4_report):
    assert stage4_report["portability"]["matches_working_tree"] is True


def test_no_source_patch_was_applied(stage4_report):
    assert stage4_report["portability"]["source_patches_applied"] is False
