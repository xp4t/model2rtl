"""Stage 3: full behavioural verification of the production RTL.

Every expected value comes from the Stage-0 NumPy integer golden model.
These tests re-run the checks independently of scripts/verify_stage3.py.
"""

import hashlib
import os
import re

import numpy as np
import pytest

from model2rtl import stage3_sim as S3
from model2rtl.golden import alphabet_lookup, requantize_relu_u8
from conftest import require_tool

N_IMAGES = 64          # kept modest here; the release script runs 500
N_TRACE = 4


@pytest.fixture(scope="session")
def subset():
    return S3.test_set(N_IMAGES)


@pytest.fixture(scope="session")
def golden(subset, integer_model):
    x, y, _ = subset
    w1 = alphabet_lookup(integer_model.layer1_weight_indices)
    hidden = requantize_relu_u8(x @ w1 + integer_model.layer1_bias)
    logits = integer_model.forward(x)
    return {"hidden": hidden, "logits": logits,
            "pred": np.argmax(logits, axis=1), "y": y}


@pytest.fixture(scope="session")
def portable_run(subset, root, top_rtl, tmp_path_factory):
    require_tool("iverilog")
    x, _, _ = subset
    d = tmp_path_factory.mktemp("s3_portable")
    return S3.run_images(root, str(d), "portable", x, trace_images=N_TRACE)


@pytest.fixture(scope="session")
def openram_run(subset, root, openram_rtl, tmp_path_factory):
    require_tool("iverilog")
    x, _, _ = subset
    d = tmp_path_factory.mktemp("s3_openram")
    return S3.run_images(root, str(d), "openram", x)


# --------------------------------------------------------------------------
# test set
# --------------------------------------------------------------------------

def test_test_set_is_deterministic_and_unfiltered(subset):
    x, y, meta = subset
    x2, y2, meta2 = S3.test_set(N_IMAGES)
    assert np.array_equal(x, x2) and np.array_equal(y, y2)
    assert meta["indices_sha256"] == meta2["indices_sha256"]
    assert "no filtering" in meta["selection_policy"]
    assert min(meta["label_histogram"]) > 0, "a digit class is missing"


# --------------------------------------------------------------------------
# primary backend
# --------------------------------------------------------------------------

def test_portable_hidden_activations_are_bit_exact(portable_run, golden):
    assert int((portable_run["hidden"] != golden["hidden"]).sum()) == 0


def test_portable_logits_are_bit_exact(portable_run, golden):
    assert int((portable_run["logits"] != golden["logits"]).sum()) == 0


def test_portable_predictions_match_the_integer_golden_model(portable_run, golden):
    assert np.array_equal(portable_run["predictions"], golden["pred"])


def test_portable_latency_is_fixed(portable_run):
    assert set(portable_run["cycles"]) == {864}


def test_three_metrics_are_kept_separate(portable_run, golden):
    """RTL correctness is not the same thing as classification accuracy."""
    rtl_vs_golden = int((portable_run["predictions"] != golden["pred"]).sum())
    int_acc = float((golden["pred"] == golden["y"]).mean())
    rtl_acc = float((portable_run["predictions"] == golden["y"]).mean())
    assert rtl_vs_golden == 0           # the Stage-3 criterion
    assert rtl_acc == int_acc           # equal because the RTL is exact
    assert int_acc > 0.90               # reported separately, not the criterion


# --------------------------------------------------------------------------
# secondary backend
# --------------------------------------------------------------------------

def test_openram_behavioral_is_bit_exact(openram_run, golden):
    assert int((openram_run["hidden"] != golden["hidden"]).sum()) == 0
    assert int((openram_run["logits"] != golden["logits"]).sum()) == 0
    assert np.array_equal(openram_run["predictions"], golden["pred"])


def test_backends_agree_with_each_other(portable_run, openram_run):
    assert np.array_equal(portable_run["hidden"], openram_run["hidden"])
    assert np.array_equal(portable_run["logits"], openram_run["logits"])
    assert np.array_equal(portable_run["predictions"], openram_run["predictions"])
    assert portable_run["cycles"] == openram_run["cycles"]


# --------------------------------------------------------------------------
# internal cycle trace
# --------------------------------------------------------------------------

def test_internal_trace_matches_the_golden_model_cycle_by_cycle(
        portable_run, subset, integer_model, param_images):
    x, _, _ = subset
    chk = S3.check_trace(portable_run["trace_path"], x[:N_TRACE], integer_model,
                         param_images)
    assert chk["images_traced"] == N_TRACE
    assert chk["failures"] == 0, chk["first_failures"]
    assert chk["total_checks"] > 10000


def test_trace_covers_every_required_checkpoint(portable_run, subset,
                                                integer_model, param_images):
    x, _, _ = subset
    c = S3.check_trace(portable_run["trace_path"], x[:N_TRACE], integer_model,
                       param_images)["checks"]
    for key in ("mac_l1", "mac_l2", "fin_l1", "fin_l2", "weight_word",
                "bias_word", "product", "accumulator", "requant", "logit"):
        assert c[key] > 0, "checkpoint %r was never exercised" % key
    assert c["mac_l1"] == 784 * N_TRACE
    assert c["mac_l2"] == 32 * N_TRACE
    assert c["fin_l1"] == 32 * N_TRACE
    assert c["fin_l2"] == 10 * N_TRACE


def test_memory_pipeline_has_no_off_by_one(portable_run, subset, integer_model,
                                           param_images):
    """Every consumed ROM word must belong to the address issued one cycle earlier."""
    x, _, _ = subset
    chk = S3.check_trace(portable_run["trace_path"], x[:N_TRACE], integer_model,
                         param_images)
    assert chk["checks"]["weight_word"] == (784 + 32) * N_TRACE
    assert chk["checks"]["bias_word"] == (32 + 10) * N_TRACE
    assert chk["failures"] == 0


# --------------------------------------------------------------------------
# stalls
# --------------------------------------------------------------------------

@pytest.mark.parametrize("mode,kw", [
    (S3.STALL_PERIODIC, {"stall_n": 7}),
    (S3.STALL_PSEUDORANDOM, {}),
])
def test_results_are_independent_of_legal_input_timing(mode, kw, root, subset,
                                                       golden, top_rtl, tmp_path):
    require_tool("iverilog")
    x, _, _ = subset
    n = 8
    r = S3.run_images(root, str(tmp_path), "portable", x[:n], stall_mode=mode, **kw)
    assert np.array_equal(r["hidden"], golden["hidden"][:n])
    assert np.array_equal(r["logits"], golden["logits"][:n])
    assert np.array_equal(r["predictions"], golden["pred"][:n])
    assert min(r["cycles"]) > 864, "the stall pattern had no effect"


# --------------------------------------------------------------------------
# reset
# --------------------------------------------------------------------------

@pytest.mark.parametrize("reset_at,label", [
    (-1, "idle"), (20, "early layer 1"), (700, "late layer 1"),
    (795, "layer-1 finalisation"), (830, "layer 2"),
    (855, "layer-2 finalisation"),
])
def test_reset_leaves_no_stale_state(reset_at, label, root, subset, golden,
                                     top_rtl, tmp_path):
    require_tool("iverilog")
    x, _, _ = subset
    r = S3.run_reset(root, str(tmp_path), "portable", x[:2], reset_at)
    assert r["stale_state_failures"] == 0, "stale state after reset at %s" % label
    assert np.array_equal(r["logits"][0], golden["logits"][1])
    assert np.array_equal(r["hidden"][0], golden["hidden"][1])


# --------------------------------------------------------------------------
# back to back
# --------------------------------------------------------------------------

def test_at_least_20_back_to_back_transactions_are_all_exact(portable_run, golden):
    assert portable_run["logits"].shape[0] >= 20
    assert int((portable_run["logits"] != golden["logits"]).sum()) == 0
    assert len(set(portable_run["cycles"])) == 1


# --------------------------------------------------------------------------
# argmax
# --------------------------------------------------------------------------

@pytest.mark.parametrize("label,b2", [
    ("unique max at 0", [100, -5, -5, -5, -5, -5, -5, -5, -5, -5]),
    ("unique max at 9", [-5, -5, -5, -5, -5, -5, -5, -5, -5, 100]),
    ("two-way tie", [7, 7, 1, 2, 3, 4, 5, 6, 0, -1]),
    ("three-way tie", [1, 9, 9, 9, 2, 3, 4, 5, 6, 7]),
    ("ten-way tie", [9] * 10),
    ("all negative", [-12, -3, -99, -3, -40, -7, -8, -9, -10, -11]),
    ("extrema", [-65536] * 4 + [65535] + [-65536] * 5),
])
def test_argmax_tie_rule_is_lowest_index(label, b2, root, tmp_path, cfg):
    require_tool("iverilog")
    b2 = np.array(b2, dtype=np.int64)
    _, imgs = S3.zero_weight_model(b2, cfg)
    run, _ = S3.run_with_params(root, str(tmp_path), imgs,
                                np.zeros((1, cfg.n_in), dtype=np.int64), cfg)
    assert np.array_equal(run["logits"][0], b2), "logits should equal the biases"
    assert int(run["predictions"][0]) == int(np.argmax(b2))
    assert int(run["predictions"][0]) == int(np.flatnonzero(b2 == b2.max())[0])


# --------------------------------------------------------------------------
# arithmetic edges through the complete top level
# --------------------------------------------------------------------------

@pytest.mark.parametrize("act", [0, 255])
def test_activation_extremes_against_every_alphabet_level(act, root, tmp_path, cfg):
    require_tool("iverilog")
    zero = cfg.k // 2
    i1 = np.full((cfg.n_in, cfg.n_hidden), zero, dtype=np.int64)
    i1[0] = [j % cfg.k for j in range(cfg.n_hidden)]
    i2 = np.full((cfg.n_hidden, cfg.n_out), zero, dtype=np.int64)
    m, imgs = S3.images_from_arrays(i1, np.zeros(cfg.n_hidden, dtype=np.int64),
                                    i2, np.zeros(cfg.n_out, dtype=np.int64), cfg)
    x = np.zeros((1, cfg.n_in), dtype=np.int64)
    x[0, 0] = act
    run, _ = S3.run_with_params(root, str(tmp_path), imgs, x, cfg)
    w1 = alphabet_lookup(i1)
    assert np.array_equal(run["hidden"], requantize_relu_u8(x @ w1))
    assert np.array_equal(run["logits"], m.forward(x))
    exercised = [int(v) for v in cfg.alphabet[i1[0]]]
    for wv in (-8, -1, 0, 1, 7):
        assert wv in exercised


def test_hidden_saturation_and_relu_at_the_top_level(root, tmp_path, cfg):
    require_tool("iverilog")
    zero = cfg.k // 2
    i2 = np.full((cfg.n_hidden, cfg.n_out), zero, dtype=np.int64)
    x = np.full((1, cfg.n_in), 255, dtype=np.int64)
    for level, expect in ((cfg.k - 1, 255), (0, 0)):
        i1 = np.full((cfg.n_in, cfg.n_hidden), level, dtype=np.int64)
        _, imgs = S3.images_from_arrays(i1, np.zeros(cfg.n_hidden, dtype=np.int64),
                                        i2, np.zeros(cfg.n_out, dtype=np.int64),
                                        cfg)
        run, _ = S3.run_with_params(root, str(tmp_path / ("sat%d" % level)),
                                    imgs, x, cfg)
        assert (run["hidden"] == expect).all()


def test_round_half_up_boundaries_at_the_top_level(root, tmp_path, cfg):
    require_tool("iverilog")
    zero = cfg.k // 2
    targets = [-1, 0, 127, 128, 129, 255, 256, 383, 384, 65279, 65280, 65281]
    i1 = np.full((cfg.n_in, cfg.n_hidden), zero, dtype=np.int64)
    i1[0] = zero + 1
    b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
    for j, t in enumerate(targets):
        b1[j] = t - 1
    i2 = np.full((cfg.n_hidden, cfg.n_out), zero, dtype=np.int64)
    _, imgs = S3.images_from_arrays(i1, b1, i2,
                                    np.zeros(cfg.n_out, dtype=np.int64), cfg)
    x = np.zeros((1, cfg.n_in), dtype=np.int64)
    x[0, 0] = 1
    run, _ = S3.run_with_params(root, str(tmp_path), imgs, x, cfg)
    want = requantize_relu_u8(np.array(targets, dtype=np.int64))
    assert np.array_equal(run["hidden"][0][:len(targets)], want)


# --------------------------------------------------------------------------
# alternate parameter set
# --------------------------------------------------------------------------

def test_alternate_parameter_set_runs_on_the_unchanged_fabric(root, tmp_path, cfg,
                                                              fabric_path):
    require_tool("iverilog")
    from model2rtl.fabric import msa_forward
    before = hashlib.sha256(open(fabric_path, "rb").read()).hexdigest()
    m_alt, imgs_alt = S3.alternate_model(31337, cfg)
    rng = np.random.default_rng(4242)
    x = rng.integers(0, 256, (4, cfg.n_in)).astype(np.int64)
    run, params = S3.run_with_params(root, str(tmp_path), imgs_alt, x, cfg)
    after = hashlib.sha256(open(fabric_path, "rb").read()).hexdigest()
    assert before == after, "the fabric changed while hosting another model"
    msa = np.array([msa_forward(x[n], m_alt.layer1_weight_indices,
                                m_alt.layer1_bias, m_alt.layer2_weight_indices,
                                m_alt.layer2_bias, cfg)
                    for n in range(x.shape[0])], dtype=np.int64)
    assert np.array_equal(run["logits"], msa)
    assert np.array_equal(run["logits"], m_alt.forward(x))
    assert os.path.basename(params) == "mnist_mlp_params_portable.v"
    assert str(tmp_path) in params


def test_alternate_parameter_images_differ_from_the_trained_ones(param_images, cfg):
    _, alt = S3.alternate_model(31337, cfg)
    assert alt["weights_l1"].sha256() != param_images["weights_l1"].sha256()


# --------------------------------------------------------------------------
# no model-specific shortcuts
# --------------------------------------------------------------------------

def test_no_labels_or_expected_results_in_the_production_rtl(root):
    for name in ("mnist_mlp_fabric.v", "mnist_mlp_top.v",
                 "mnist_mlp_params_sel_portable.v",
                 "mnist_mlp_params_sel_openram.v"):
        body = re.sub(r"//[^\n]*", "",
                      open(os.path.join(root, "rtl", name)).read())
        for token in ("label", "expected", "golden", "answer", "$readmem",
                      "test_image", "prediction_table"):
            assert token not in body.lower(), "%s contains %r" % (name, token)


def test_only_the_parameter_backend_is_model_dependent(root, param_images):
    fabric = open(os.path.join(root, "rtl", "mnist_mlp_fabric.v")).read()
    for name in ("weights_l1", "weights_l2", "bias_l1", "bias_l2"):
        assert param_images[name].sha256() not in fabric
    word = "%032x" % param_images["weights_l1"].rows[0]
    assert word not in fabric
    assert word in open(os.path.join(root, "rtl",
                                     "mnist_mlp_params_portable.v")).read()


# --------------------------------------------------------------------------
# Stage-3 report
# --------------------------------------------------------------------------

def test_stage3_report_is_consistent(stage3_report, fabric_path):
    rep = stage3_report
    assert rep["stage"] == 3
    assert rep["status"] == "PASS", rep["failures"]
    assert rep["oracle"].startswith("Stage-0 NumPy integer golden model")
    p = rep["portable_backend"]
    assert p["hidden_mismatches"] == 0
    assert p["logit_mismatches"] == 0
    assert p["prediction_mismatches"] == 0
    assert p["images"] >= 200
    o = rep["openram_behavioral_backend"]
    assert o["hidden_mismatches"] == o["logit_mismatches"] == 0
    assert all(v == 0 for v in rep["backend_to_backend"].values())
    assert rep["internal_checkpointing"]["failures"] == 0
    assert rep["internal_checkpointing"]["images_traced"] >= 20
    assert rep["memory_pipeline"]["off_by_one_failures"] == 0
    assert rep["reset"]["stale_state_failures_total"] == 0
    assert rep["argmax"]["failures"] == 0
    assert rep["arithmetic_edges"]["failures"] == 0
    assert rep["alternate_model"]["fabric_unchanged"] is True
    assert rep["alternate_model"]["mismatches_vs_msa_reference"] == 0
    assert rep["shortcut_scan"]["clean"] is True
    assert all(v["ok"] for v in rep["lint"].values())
    assert rep["openrom_physical_status"]["status"].startswith("PARTIAL")
    with open(fabric_path, "rb") as fh:
        assert rep["meta"]["fabric_sha256"] == hashlib.sha256(fh.read()).hexdigest()


def test_stage3_report_makes_no_unearned_claim(stage3_report):
    claims = " ".join(stage3_report["not_claimed"]).lower()
    for topic in ("fpga portability", "fpga gate-level", "asic gate-level",
                  "openrom signoff"):
        assert topic in claims
