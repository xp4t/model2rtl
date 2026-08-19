"""Stage 6: the documentation must not drift from the measured results.

The final report is generated, not written by hand, so these tests guard the
generation: every headline number must still equal the stage report it came
from, the frozen artifacts must still hash the same, and the claim language
must stay inside what was actually demonstrated.
"""

import csv
import hashlib
import json
import os

import pytest

STAGE_FILES = {
    0: "stage0_quantization.json",
    1: "stage1_compute_fabric.json",
    2: "stage2_parameter_backends.json",
    3: "stage3_behavioral_verification.json",
    4: "stage4_dual_target_portability.json",
    5: "stage5_openrom_physical.json",
}

FORBIDDEN = [
    "asic signoff complete",
    "signoff complete",
    "timing closed",
    "production ready",
    "production-ready",
    "drc-clean",
    "lvs-clean",
    "taalas architecture implemented",
    "converted directly into a production chip",
]


@pytest.fixture(scope="session")
def final(root):
    p = os.path.join(root, "reports", "final_report.json")
    if not os.path.exists(p):
        pytest.fail("reports/final_report.json missing: run "
                    "scripts/build_final_report.py")
    with open(p) as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def stages(root):
    out = {}
    for n, f in STAGE_FILES.items():
        with open(os.path.join(root, "reports", f)) as fh:
            out[n] = json.load(fh)
    return out


# -- the artifacts exist ----------------------------------------------------

@pytest.mark.parametrize("rel", ["FINAL-REPORT.md", "README.md",
                                 "reports/final_report.json",
                                 "reports/results.csv"])
def test_final_artifacts_exist(root, rel):
    p = os.path.join(root, rel)
    assert os.path.isfile(p)
    assert os.path.getsize(p) > 0


# -- nothing drifted --------------------------------------------------------

def test_frozen_artifacts_still_match(final, root):
    for rel, want in final["frozen_artifacts"].items():
        with open(os.path.join(root, rel), "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == want, rel


def test_frozen_set_covers_model_rtl_and_every_stage_report(final):
    keys = set(final["frozen_artifacts"])
    assert "model/mnist_weights_indices.npz" in keys
    assert "model/quant_params.json" in keys
    for f in STAGE_FILES.values():
        assert "reports/" + f in keys
    rtl = {k for k in keys if k.startswith("rtl/")}
    assert len(rtl) >= 5


def test_fabric_hash_is_still_the_stage1_hash(final):
    assert (final["rtl"]["fabric"]["sha256"]
            == "7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c")


def test_cross_stage_consistency_had_no_disagreements(final):
    c = final["cross_stage_consistency"]
    assert c["checked"] >= 10
    assert c["disagreements"] == 0
    assert all(x["agree"] for x in c["checks"])


# -- the numbers were extracted, not retyped --------------------------------

def test_accuracies_match_stage0(final, stages):
    s0 = stages[0]
    assert (final["model"]["float_test_accuracy"]
            == s0["float_model"]["test_accuracy"])
    assert (final["model"]["quantized_integer_test_accuracy"]
            == s0["quantized_integer_model"]["test_accuracy"])


def test_accuracy_change_sign_is_stated_as_a_loss(final):
    m = final["model"]
    assert m["accuracy_change_points"] < 0
    assert "loses" in m["accuracy_change_wording"].lower()


def test_behavioral_numbers_match_stage3(final, stages):
    a = final["behavioral_verification"]
    b = stages[3]
    assert a["images"] == b["test_set"]["count"]
    assert a["portable_backend"] == b["portable_backend"]
    assert (a["cycle_level_trace"]["total_checks"]
            == b["internal_checkpointing"]["total_checks"])


def test_synthesis_numbers_match_stage4(final, stages):
    a, b = final["dual_target_portability"], stages[4]
    assert a["fpga"]["resources"] == b["fpga_target"]["resources"]
    assert a["generic"]["resources"] == b["generic_target"]["resources"]
    assert a["fpga"]["netlist_sha256"] == b["fpga_target"]["netlist_sha256"]


def test_physical_numbers_match_stage5(final, stages):
    a, b = final["physical_openrom"], stages[5]
    assert set(a["macros"]) == set(b["macros"])
    assert a["signoff"]["status"] == b["physical_signoff"]["status"]
    assert final["area"]["openrom_total_macro_bbox_um2"] == \
        b["area"]["openrom_total_macro_bbox_um2"]


def test_results_csv_agrees_with_the_json(final, root):
    with open(os.path.join(root, "reports", "results.csv")) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) >= 25
    by = {r["metric"]: r for r in rows}
    assert by["Quantized integer MNIST test accuracy"]["value"] == \
        "%.2f%%" % (100 * final["model"]["quantized_integer_test_accuracy"])
    assert by["iCE40 SB_MAC16 (DSP)"]["value"] == \
        str(final["dual_target_portability"]["fpga"]["resources"]["dsp"])
    assert by["Physical signoff"]["value"] == \
        final["physical_openrom"]["signoff"]["status"]
    for r in rows:
        assert r["source"].startswith("reports/stage")


# -- the claim stays inside what was demonstrated ---------------------------

@pytest.mark.parametrize("rel", ["FINAL-REPORT.md", "README.md"])
def test_documents_avoid_forbidden_claims(root, rel):
    text = open(os.path.join(root, rel)).read().lower()
    for phrase in FORBIDDEN:
        # the phrase may appear only inside an explicit disclaimer
        for line in text.splitlines():
            if phrase in line:
                assert any(neg in line for neg in
                           ("not ", "no ", "never", "avoid", "cannot",
                            "unverified", "is not")), \
                    "%s: unguarded claim %r in: %s" % (rel, phrase, line[:120])


@pytest.mark.parametrize("rel", ["FINAL-REPORT.md", "README.md"])
def test_documents_state_the_signoff_status(root, rel, final):
    text = open(os.path.join(root, rel)).read()
    assert "UNVERIFIED" in text
    assert final["physical_openrom"]["signoff"]["status"] == "UNVERIFIED"


def test_scope_and_not_claimed_are_explicit(final):
    scope = final["claim_scope"].lower()
    for phrase in ("production asic readiness", "timing closure",
                   "arbitrary-model", "proprietary"):
        assert phrase in scope
    nc = " ".join(final["not_claimed"]).lower()
    for phrase in ("drc-clean", "lvs-clean", "timing closure",
                   "full-chip physical implementation"):
        assert phrase in nc


def test_prior_art_note_is_careful(final):
    n = final["prior_art_note"].lower()
    assert "publicly disclosed" in n
    assert "no taalas source code" in n
    assert "nothing here is claimed to be equivalent" in n


def test_operation_counts_are_labelled_source_level(final):
    oc = final["architecture"]["operation_counts"]
    assert "SOURCE-LEVEL" in oc["kind"]
    assert "not physical multiplier counts" in oc["kind"]
    assert oc["implemented_active_shared_product_expressions"] == 16


def test_constant_multiply_wording_guardrail(final):
    cm = final["constant_multiplication"]
    assert cm["multiplier_or_dsp_cells_fpga"] == 0
    assert cm["multiplier_or_dsp_cells_generic"] == 0
    assert "sixteen constant-weight product alternatives" in \
        cm["correct_wording"]
    assert "that is NOT what synthesis showed" in cm["wording_to_avoid"]


def test_area_comparison_is_qualified(final):
    a = final["area"]
    assert "NOT the same kind of area" in a["caveat"]
    assert "not available" in a["floorplanned_area"]


def test_crossover_is_not_extrapolated(final):
    c = final["crossover"]
    assert len(c["measured_points"]) >= 6
    if c["smallest_openrom_winning_point"] is None:
        assert "none" in c["measured_crossover_interval"]
        assert "extrapolation" in c["conclusion"]


def test_limitations_cover_the_required_points(final):
    joined = " ".join(final["limitations"]).lower()
    for phrase in ("mnist only", "convolution", "onnx", "place-and-route",
                   "unverified", "784-32-10"):
        assert phrase in joined


def test_future_work_is_ranked_and_unimplemented(final):
    fw = final["future_work"]
    assert [w["rank"] for w in fw] == list(range(1, len(fw) + 1))
    assert any("onnx" in w["item"].lower() for w in fw)


def test_environment_admits_it_is_not_one_click(final):
    assert "NOT one-click portable" in final["environment"]["note"]
    for k in ("python", "yosys", "iverilog", "magic", "netgen", "klayout"):
        assert final["environment"][k]
    assert final["environment"]["openram"]["openram_commit"]
