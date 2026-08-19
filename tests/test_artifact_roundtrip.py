"""Validations 4, 5, 6: artefact reload equivalence and weight/fabric separation."""

import json

import numpy as np

from model2rtl import contract as C
from model2rtl import storage as S


def test_npz_reload_gives_identical_predictions(paths, integer_model, mnist_test):
    x, _ = mnist_test
    reloaded = S.load_indices(paths["npz"])
    assert np.array_equal(reloaded.layer1_weight_indices,
                          integer_model.layer1_weight_indices)
    assert np.array_equal(reloaded.layer2_bias, integer_model.layer2_bias)
    assert np.array_equal(reloaded.forward(x[:1000]),
                          integer_model.forward(x[:1000]))


def test_npz_resave_is_byte_identical(paths, integer_model, tmp_path):
    """Determinism of the stored artefact under a save/load/save round trip."""
    import hashlib
    p1 = str(tmp_path / "a.npz")
    p2 = str(tmp_path / "b.npz")
    S.save_indices(p1, integer_model)
    S.save_indices(p2, S.load_indices(p1))
    h = [hashlib.sha256(open(p, "rb").read()).hexdigest() for p in (p1, p2)]
    assert h[0] == h[1]


def test_quant_params_reload_reproduces_the_contract(paths):
    params = S.load_quant_params(paths["quant"])
    assert S.contract_matches(params)
    assert params["K"] == 16
    assert params["weight_alphabet"] == list(range(-8, 8))
    assert params["hidden_requant_shift"] == C.HIDDEN_REQUANT_SHIFT
    assert params["activation_bits"] == 8
    assert params["activation_signed"] is False


def test_inference_from_reloaded_artifacts_only(paths, integer_model, mnist_test):
    """Rebuild the whole integer path from the two saved files alone."""
    x, _ = mnist_test
    params = S.load_quant_params(paths["quant"])
    alphabet = np.array(params["weight_alphabet"], dtype=np.int64)
    shift = params["hidden_requant_shift"]
    lo, hi = params["activation_min"], params["activation_max"]

    with np.load(paths["npz"]) as z:
        i1 = z["layer1_weight_indices"].astype(np.int64)
        i2 = z["layer2_weight_indices"].astype(np.int64)
        b1 = z["layer1_bias"].astype(np.int64)
        b2 = z["layer2_bias"].astype(np.int64)

    xb = x[:1000].astype(np.int64)
    acc1 = xb @ alphabet[i1] + b1
    h = np.clip((np.maximum(acc1, 0) + (1 << (shift - 1))) >> shift, lo, hi)
    logits = h @ alphabet[i2] + b2
    assert np.array_equal(logits, integer_model.forward(x[:1000]))


def test_quant_params_contains_no_trained_weight_values(paths):
    """The contract file must be weight independent."""
    raw = open(paths["quant"]).read()
    params = json.loads(raw)
    for key in ("layer1_weight_indices", "layer2_weight_indices",
                "layer1_bias", "layer2_bias", "weights", "biases"):
        assert key not in params, "quant_params.json leaks model parameters"

    def big_arrays(node):
        if isinstance(node, list):
            if len(node) > C.K:
                yield node
            for v in node:
                yield from big_arrays(v)
        elif isinstance(node, dict):
            for v in node.values():
                yield from big_arrays(v)

    assert not list(big_arrays(params)), "quant_params.json holds a bulk tensor"
    # 25088 + 320 synapses could never fit in a file this small
    assert len(raw) < 20000


def test_contract_is_independent_of_the_trained_model(integer_model):
    """Validation 6 / fabric independence.

    The arithmetic contract is computed from topology, K and the alphabet
    alone.  Swapping in a completely different weight-index set must not
    change a single declared width, shift or limit.
    """
    before = C.width_report()
    rng = np.random.default_rng(7)
    other = type(integer_model)(
        layer1_weight_indices=rng.integers(0, 16, (784, 32)).astype(np.int64),
        layer2_weight_indices=rng.integers(0, 16, (32, 10)).astype(np.int64),
        layer1_bias=rng.integers(-5000, 5000, 32).astype(np.int64),
        layer2_bias=rng.integers(-5000, 5000, 10).astype(np.int64))
    other.validate()
    other.forward(np.full((4, 784), 255, dtype=np.int64), check_widths=True)
    assert C.width_report() == before
    assert S.quant_params_dict() == S.quant_params_dict()


def test_report_matches_the_saved_artifacts(stage0_report, integer_model, paths):
    from model2rtl import data as D
    h = stage0_report["meta"]["artifact_hashes"]
    assert h["mnist_weights_indices.npz"] == D.file_sha256(paths["npz"])
    assert h["quant_params.json"] == D.file_sha256(paths["quant"])
    assert stage0_report["rtl_generated"] is False
    assert stage0_report["quantized_integer_model"]["test_accuracy"] > 0.90


def test_generated_artifacts_stay_inside_the_current_stage(root):
    """rtl/ holds exactly the files the completed stages are allowed to emit.

    This is a stage-boundary allowlist, not a freeze: it fails when a stage
    emits RTL it was not authorised to emit.  Each entry names the stage that
    introduced it, so an unplanned file is still caught.
    """
    import os
    allowed_rtl = {
        "mnist_mlp_fabric.v",              # Stage 1
        "mnist_mlp_params_portable.v",     # Stage 2, backend A
        "mnist_mlp_params_openram.v",      # Stage 2, backend B
        "mnist_mlp_params_sel_portable.v",
        "mnist_mlp_params_sel_openram.v",
        "mnist_mlp_top.v",
        # Stage 5: the physical OpenROM organisation went into NEW files
        # because the Stage-2 backend and its selector are frozen.
        "mnist_mlp_params_openrom_phys.v",
        "mnist_mlp_params_sel_openrom_phys.v",
    }
    rtl = [f for f in os.listdir(os.path.join(root, "rtl"))
           if not f.startswith(".")]
    assert set(rtl) <= allowed_rtl, "unexpected RTL for this stage: %s" % (
        sorted(set(rtl) - allowed_rtl),)
    # build/ is organised per stage; no stage may drop artefacts at its root
    build = os.path.join(root, "build")
    allowed_build = {"param_images", "openram", "stage4", "stage5"}
    assert set(os.listdir(build)) <= allowed_build, \
        "unexpected build directory: %s" % (
            sorted(set(os.listdir(build)) - allowed_build),)
