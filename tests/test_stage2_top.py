"""mnist_mlp_top: fabric + one build-time selected parameter backend."""

import os
import re

import numpy as np
import pytest

from model2rtl import sim as SIM
from model2rtl import stage2_sim as S2
from model2rtl.golden import alphabet_lookup, requantize_relu_u8
from conftest import require_tool

N_IMAGES = 200


@pytest.fixture(scope="session")
def golden(integer_model, mnist_test):
    x, y = mnist_test
    x = x[:N_IMAGES]
    logits = integer_model.forward(x)
    w1 = alphabet_lookup(integer_model.layer1_weight_indices)
    hidden = requantize_relu_u8(x.astype(np.int64) @ w1 + integer_model.layer1_bias)
    return {"x": x, "y": y[:N_IMAGES], "logits": logits,
            "pred": np.argmax(logits, axis=1), "hidden": hidden}


@pytest.fixture(scope="session")
def top_runs(golden, top_rtl, portable_rtl, openram_rtl, root, tmp_path_factory):
    require_tool("iverilog")
    out = {}
    for backend in ("portable", "openram"):
        d = tmp_path_factory.mktemp("top_" + backend)
        out[backend] = S2.run_top_inference(root, str(d), backend, golden["x"])
    return out


def test_top_instantiates_the_unmodified_fabric(top_rtl):
    src = open(top_rtl).read()
    assert "mnist_mlp_fabric u_fabric" in src
    assert "mnist_mlp_params u_params" in src
    # the top must not re-implement any arithmetic
    assert "*" not in re.sub(r"//[^\n]*", "", src).replace("always @(*)", "")


def test_backend_selection_is_build_time_only(root):
    sel_p = open(os.path.join(root, "rtl",
                              "mnist_mlp_params_sel_portable.v")).read()
    sel_o = open(os.path.join(root, "rtl",
                              "mnist_mlp_params_sel_openram.v")).read()
    for src, backend in ((sel_p, "mnist_mlp_params_portable"),
                         (sel_o, "mnist_mlp_params_openram")):
        assert "module mnist_mlp_params (" in src
        assert "%s u_backend" % backend in src
    # no runtime mux anywhere
    top = open(os.path.join(root, "rtl", "mnist_mlp_top.v")).read()
    assert "backend_sel" not in top and "BACKEND" not in top.replace(
        "BACKEND SELECTION IS BUILD TIME", "")


@pytest.mark.parametrize("backend", ["portable", "openram"])
def test_top_compiles_in_strict_verilog2001(backend, root, tmp_path):
    require_tool("iverilog")
    srcs = (S2.PORTABLE_SOURCES if backend == "portable" else S2.OPENRAM_SOURCES)
    paths = [os.path.join(root, "rtl", s) for s in srcs]
    r = SIM.iverilog_compile(paths, str(tmp_path / "a.out"), str(tmp_path),
                             std="2001")
    assert r.returncode == 0, r.output
    assert "warning" not in r.output.lower(), r.output


@pytest.mark.parametrize("backend", ["portable", "openram"])
def test_top_elaborates_clean_in_yosys(backend, root, tmp_path):
    require_tool("yosys")
    srcs = (S2.PORTABLE_SOURCES if backend == "portable" else S2.OPENRAM_SOURCES)
    merged = str(tmp_path / ("top_%s.v" % backend))
    with open(merged, "w") as out:
        for s in srcs:
            out.write(open(os.path.join(root, "rtl", s)).read())
            out.write("\n")
    res = SIM.yosys_check(merged, "mnist_mlp_top")
    assert res["ok"], res["log"][-3000:]
    assert res["latch_lines"] == []
    assert "multiple conflicting drivers" not in res["log"]
    assert "is used but has no driver" not in res["log"]
    assert "Found and reported 0 problems." in res["log"]


@pytest.mark.parametrize("backend", ["portable", "openram"])
def test_logits_are_bit_exact_against_the_integer_golden_model(backend, top_runs,
                                                               golden):
    r = top_runs[backend]
    assert np.array_equal(r["logits"], golden["logits"]), \
        "%s backend logit mismatch" % backend


@pytest.mark.parametrize("backend", ["portable", "openram"])
def test_hidden_activations_are_bit_exact(backend, top_runs, golden):
    assert np.array_equal(top_runs[backend]["hidden"], golden["hidden"])


@pytest.mark.parametrize("backend", ["portable", "openram"])
def test_predictions_match_and_accuracy_is_reported(backend, top_runs, golden):
    r = top_runs[backend]
    assert np.array_equal(r["predictions"], golden["pred"])
    acc = float((r["predictions"] == golden["y"]).mean())
    assert acc > 0.90, "accuracy over %d images was %.4f" % (N_IMAGES, acc)


def test_backend_to_backend_results_are_identical(top_runs):
    p, o = top_runs["portable"], top_runs["openram"]
    assert np.array_equal(p["logits"], o["logits"])
    assert np.array_equal(p["hidden"], o["hidden"])
    assert np.array_equal(p["predictions"], o["predictions"])
    assert p["cycles"] == o["cycles"], "the backends have different latency"


def test_latency_is_unchanged_from_stage1(top_runs):
    for backend, r in top_runs.items():
        assert set(r["cycles"]) == {864}, \
            "%s changed the inference latency: %s" % (backend, set(r["cycles"]))
