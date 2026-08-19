"""The model2rtl compiler CLI: any two-layer dense MLP in, portable RTL out.

The generalization is ADDITIVE. model2rtl.golden, contract, fabric and
verilog_emit are frozen and untouched; the general path reuses them and is
proven here to reproduce them exactly. Two properties matter most:

  * the general integer model equals the frozen Stage-0 oracle, and
  * compiling the frozen MNIST parameters regenerates the verified RTL
    byte-for-byte.

If either breaks, the generalization has changed a verified result.
"""

import json
import os
import subprocess
import sys

import numpy as np
import pytest

from model2rtl import contract as C
from model2rtl import genmodel as G
from model2rtl.compile import compile_model
from model2rtl.fabric import FabricConfig
from model2rtl.ingest import FloatNetwork, UnsupportedModel, load
from model2rtl.quantize import quantize_ptq
from model2rtl.verilog_emit import emit_fabric_verilog

from conftest import require_tool

FROZEN_FABRIC_SHA = \
    "7757362642b37fd0044bb7b323467116998caee69bad091d8454fc6010691e1c"


# -- the general model equals the frozen oracle -----------------------------

def test_general_model_reproduces_the_frozen_oracle(integer_model, mnist_test):
    x, _ = mnist_test
    r = G.assert_matches_frozen_oracle(integer_model, x[:500].astype(np.int64))
    assert r["hidden_mismatches"] == 0
    assert r["logit_mismatches"] == 0
    assert r["prediction_mismatches"] == 0
    assert r["logits_compared"] == 5000


def test_general_model_infers_the_topology(integer_model):
    g = G.from_frozen(integer_model)
    assert (g.cfg.n_in, g.cfg.n_hidden, g.cfg.n_out) == (784, 32, 10)
    assert g.cfg.requant_shift == C.HIDDEN_REQUANT_SHIFT


def test_general_model_accepts_other_topologies():
    rng = np.random.default_rng(0)
    m = G.GeneralIntegerModel.from_arrays(
        rng.integers(0, 16, (64, 16)), rng.integers(0, 16, (16, 4)),
        rng.integers(-100, 100, 16), rng.integers(-50, 50, 4))
    assert (m.cfg.n_in, m.cfg.n_hidden, m.cfg.n_out) == (64, 16, 4)
    assert m.forward(rng.integers(0, 256, (5, 64))).shape == (5, 4)


def test_general_model_rejects_inconsistent_shapes():
    rng = np.random.default_rng(0)
    with pytest.raises(G.ModelSpecError):
        G.GeneralIntegerModel.from_arrays(
            rng.integers(0, 16, (64, 16)), rng.integers(0, 16, (8, 4)),
            np.zeros(16, dtype=np.int64), np.zeros(4, dtype=np.int64))


def test_general_model_rejects_out_of_range_bias():
    """A bias that will not fit the derived width must fail closed."""
    rng = np.random.default_rng(0)
    with pytest.raises(G.ModelSpecError):
        G.GeneralIntegerModel.from_arrays(
            rng.integers(0, 16, (8, 4)), rng.integers(0, 16, (4, 2)),
            np.full(4, 1 << 30, dtype=np.int64), np.zeros(2, dtype=np.int64))


# -- the frozen RTL is reproduced exactly -----------------------------------

def test_emitter_reproduces_the_frozen_fabric():
    import hashlib
    src = emit_fabric_verilog(FabricConfig())
    assert hashlib.sha256(src.encode()).hexdigest() == FROZEN_FABRIC_SHA


def test_cli_regenerates_the_verified_mnist_rtl(root, tmp_path):
    """The whole point: the general compiler must not have changed anything."""
    import hashlib
    out = tmp_path / "mnistout"
    rc = _run_cli(["--indices", os.path.join(root, "model",
                                             "mnist_weights_indices.npz"),
                   "--output", str(out), "--prefix", "mnist_mlp", "--quiet"])
    assert rc == 0

    def sha(p):
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    assert sha(out / "mnist_mlp_fabric.v") == FROZEN_FABRIC_SHA
    assert sha(out / "mnist_mlp_fabric.v") == \
        sha(os.path.join(root, "rtl", "mnist_mlp_fabric.v"))
    assert sha(out / "mnist_mlp_params.v") == \
        sha(os.path.join(root, "rtl", "mnist_mlp_params_portable.v"))


def test_compiled_report_is_self_describing(root, tmp_path):
    out = tmp_path / "o"
    assert _run_cli(["--indices", os.path.join(root, "model",
                                               "mnist_weights_indices.npz"),
                     "--output", str(out), "--prefix", "mnist_mlp",
                     "--quiet"]) == 0
    rep = json.load(open(out / "compile_report.json"))
    assert rep["topology"] == "784 -> 32 -> ReLU -> 10"
    assert rep["latency"]["cycles_per_inference"] == 864
    assert rep["weight_independence"]["identical"] is True
    assert rep["model"]["synapses"]["total"] == 25408
    joined = " ".join(rep["not_claimed"]).lower()
    assert "no synthesis" in joined


# -- weight independence, asserted on every compile -------------------------

def test_every_compile_proves_weight_independence(tmp_path):
    rng = np.random.default_rng(5)
    shas = []
    for seed in (1, 2):
        r = np.random.default_rng(seed)
        m = G.GeneralIntegerModel.from_arrays(
            r.integers(0, 16, (32, 8)), r.integers(0, 16, (8, 3)),
            r.integers(-500, 500, 8), r.integers(-100, 100, 3),
            module_name="mlp_fabric")
        rep = compile_model(m, str(tmp_path / ("o%d" % seed)))
        assert rep["weight_independence"]["identical"] is True
        shas.append(rep["emitted"]["mlp_fabric.v"])
    assert shas[0] == shas[1], "two models of one shape gave different fabrics"


# -- ingestion fails closed -------------------------------------------------

def test_ingest_rejects_unknown_format(tmp_path):
    p = tmp_path / "m.onnx"
    p.write_text("x")
    with pytest.raises(UnsupportedModel, match="unrecognised model format"):
        load(str(p))


def test_ingest_rejects_missing_file():
    with pytest.raises(UnsupportedModel, match="not found"):
        load("/nonexistent/model.h5")


def test_ingest_npz_requires_all_four_arrays(tmp_path):
    p = tmp_path / "m.npz"
    np.savez(p, w1=np.zeros((4, 2)), b1=np.zeros(2))
    with pytest.raises(UnsupportedModel, match="missing"):
        load(str(p))


def test_ingest_npz_roundtrip(tmp_path):
    p = tmp_path / "m.npz"
    np.savez(p, w1=np.zeros((4, 2)), b1=np.zeros(2),
             w2=np.zeros((2, 3)), b2=np.zeros(3))
    net = load(str(p))
    assert (net.n_in, net.n_hidden, net.n_out) == (4, 2, 3)
    assert len(net.source_sha256) == 64


# -- quantization -----------------------------------------------------------

def test_ptq_recovers_an_already_quantized_model(integer_model, mnist_test):
    """Quantizing a network whose weights ARE alphabet levels must return
    those exact levels: the asymmetric -8..+7 range has to be handled."""
    from model2rtl.golden import alphabet_lookup
    x, y = mnist_test
    net = FloatNetwork(
        w1=alphabet_lookup(integer_model.layer1_weight_indices).astype(float),
        b1=integer_model.layer1_bias.astype(float),
        w2=alphabet_lookup(integer_model.layer2_weight_indices).astype(float),
        b2=integer_model.layer2_bias.astype(float))
    r = quantize_ptq(net, x[:200].astype(np.int64), y[:200],
                     input_scales=(1.0,), shifts=(8,))
    assert r.layer1_scale == 1.0 and r.layer2_scale == 1.0
    assert np.array_equal(r.model.layer1_weight_indices,
                          integer_model.layer1_weight_indices)
    assert np.array_equal(r.model.layer2_weight_indices,
                          integer_model.layer2_weight_indices)
    assert np.array_equal(r.model.layer1_bias, integer_model.layer1_bias)
    assert r.clipping["layer1_percent"] == 0.0


def test_ptq_chooses_the_shift_by_measurement(mnist_test):
    """The shift trades hidden saturation against hidden sparsity, and the
    search must actually explore that, not pick a constant."""
    rng = np.random.default_rng(2)
    net = FloatNetwork(w1=rng.normal(0, 0.3, (784, 16)),
                       b1=rng.normal(0, 0.1, 16),
                       w2=rng.normal(0, 0.4, (16, 10)),
                       b2=rng.normal(0, 0.1, 10))
    x, y = mnist_test
    r = quantize_ptq(net, x[:200].astype(np.int64), y[:200],
                     input_scales=(1.0 / 255.0,))
    scored = [s for s in r.search if "accuracy" in s]
    assert len(scored) >= 5
    assert any(s["hidden_saturation_percent"] > 0 for s in scored)
    assert r.requant_shift == max(scored,
                                  key=lambda s: s["accuracy"])["shift"]


def test_quantization_report_flags_missing_labels():
    rng = np.random.default_rng(3)
    net = FloatNetwork(w1=rng.normal(0, 0.3, (16, 8)), b1=np.zeros(8),
                       w2=rng.normal(0, 0.3, (8, 4)), b2=np.zeros(4))
    r = quantize_ptq(net, None, None)
    assert any("NO LABELLED CALIBRATION DATA" in n for n in r.notes)
    assert r.calibration_accuracy is None


def test_quantization_report_disclaims_the_scales():
    rng = np.random.default_rng(3)
    net = FloatNetwork(w1=rng.normal(0, 0.3, (16, 8)), b1=np.zeros(8),
                       w2=rng.normal(0, 0.3, (8, 4)), b2=np.zeros(4))
    d = quantize_ptq(net, None, None).to_dict()
    assert "no multiplicative scale" in d["scale_note"]


# -- the emitted RTL for a NEW topology is real ------------------------------

def _run_cli(argv):
    from model2rtl.cli import main
    return main(argv)


def test_cli_rejects_missing_output():
    with pytest.raises(SystemExit):
        _run_cli(["--indices", "x.npz"])


def test_cli_rejects_both_sources(tmp_path):
    with pytest.raises(SystemExit):
        _run_cli(["--model", "a.h5", "--indices", "b.npz",
                  "--output", str(tmp_path)])


def test_emitted_rtl_for_a_new_topology_elaborates(tmp_path):
    require_tool("iverilog")
    rng = np.random.default_rng(11)
    m = G.GeneralIntegerModel.from_arrays(
        rng.integers(0, 16, (64, 16)), rng.integers(0, 16, (16, 4)),
        rng.integers(-200, 200, 16), rng.integers(-50, 50, 4),
        module_name="mlp_fabric")
    out = tmp_path / "rtl"
    compile_model(m, str(out))
    srcs = [str(out / f) for f in ("mlp_top.v", "mlp_fabric.v",
                                   "mlp_params.v", "mlp_params_sel.v")]
    from model2rtl.sim import find_tool
    r = subprocess.run([find_tool("iverilog"), "-g2001", "-Wall", "-o",
                        os.devnull, "-s", "mlp_top"] + srcs,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "" and r.stderr.strip() == ""


def test_emitted_rtl_for_a_new_topology_computes_the_right_answer(tmp_path):
    """The real question: does the generated hardware match the integer model
    for a topology this project never verified by hand?"""
    require_tool("iverilog")
    require_tool("vvp")
    from model2rtl.stage3_sim import _parse_out, _write_images, emit_stage3_tb
    from model2rtl.sim import find_tool, iverilog_compile, _run

    rng = np.random.default_rng(23)
    cfg_in, cfg_h, cfg_o = 40, 12, 5
    m = G.GeneralIntegerModel.from_arrays(
        rng.integers(0, 16, (cfg_in, cfg_h)), rng.integers(0, 16, (cfg_h, cfg_o)),
        rng.integers(-300, 300, cfg_h), rng.integers(-80, 80, cfg_o),
        module_name="mnist_mlp_fabric")          # so the Stage-3 TB fits
    out = tmp_path / "rtl"
    compile_model(m, str(out), prefix="mnist_mlp")

    work = tmp_path / "sim"
    work.mkdir()
    x = rng.integers(0, 256, (6, cfg_in), dtype=np.int64)
    _write_images(str(work), x)
    tb = work / "tb.v"
    tb.write_text(emit_stage3_tb(m.cfg))
    srcs = [str(out / f) for f in ("mnist_mlp_fabric.v", "mnist_mlp_params.v",
                                   "mnist_mlp_params_sel.v", "mnist_mlp_top.v")]
    exe = str(work / "sim.vvp")
    c = iverilog_compile(srcs + [str(tb)], exe, str(work), std="2001",
                         top_params={"tb.NIMG": x.shape[0], "tb.STALL_MODE": 0,
                                     "tb.STALL_N": 7, "tb.TRACE_IMAGES": 0})
    assert c.returncode == 0, c.output
    r = _run([find_tool("vvp"), exe], cwd=str(work))
    assert "TB OK" in r.output, r.output[-2000:]

    cycles, preds, logits = _parse_out(str(work / "out.txt"), cfg_o)
    want = m.forward(x)
    assert np.array_equal(logits, want), "RTL logits differ from the model"
    assert np.array_equal(preds, np.argmax(want, axis=1))
    expected_cycles = cfg_in + 2 * cfg_h + cfg_o + 6
    assert cycles == [expected_cycles] * x.shape[0]
