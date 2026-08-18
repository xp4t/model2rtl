"""The fixed fabric must be provably independent of the trained model.

Three independent lines of evidence:
  1. the generator never opens the trained-parameter file (instrumented);
  2. regenerating with a *different* valid weight set, and again with different
     biases, produces a byte-identical file (SHA-256);
  3. no numeric literal in the emitted Verilog can carry a trained value.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import pytest

from model2rtl import contract as C
from model2rtl import fabric as F
from model2rtl import storage as S


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ---------------------------------------------------------------------------
# 1. the generator never touches trained parameters
# ---------------------------------------------------------------------------

def test_generator_never_opens_the_trained_parameter_file(cfg, monkeypatch):
    """Instrument every file-open path the generator could possibly use."""
    import builtins
    opened = []

    real_open = builtins.open
    real_load = np.load

    def spy_open(file, *a, **kw):
        opened.append(str(file))
        return real_open(file, *a, **kw)

    def spy_load(file, *a, **kw):
        opened.append(str(file))
        return real_load(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(np, "load", spy_load)

    from model2rtl.verilog_emit import emit_fabric_verilog
    text = emit_fabric_verilog(cfg)

    monkeypatch.undo()
    assert text
    for path in opened:
        low = path.lower()
        assert not low.endswith(".npz"), "generator opened an NPZ: %s" % path
        assert os.sep + "model" + os.sep not in low, \
            "generator read from model/: %s" % path


def test_generator_source_does_not_reference_the_weight_file(root):
    gen = os.path.join(root, "scripts", "gen_compute_fabric.py")
    emit = os.path.join(root, "src", "model2rtl", "verilog_emit.py")
    for path in (gen, emit):
        src = open(path).read()
        body = re.sub(r'"""(.|\n)*?"""', "", src)   # drop docstrings
        body = re.sub(r"#[^\n]*", "", body)
        for token in ("mnist_weights_indices", "layer1_weight_indices",
                      "layer2_weight_indices", "load_indices", "np.load"):
            assert token not in body, "%s references %s" % (path, token)


# ---------------------------------------------------------------------------
# 2. SHA-256 equality across substituted model parameters
# ---------------------------------------------------------------------------

def _regen(root: str, out: str) -> str:
    """Run the real generator as a subprocess and return the file SHA-256."""
    env = dict(os.environ)
    r = subprocess.run([sys.executable,
                        os.path.join(root, "scripts", "gen_compute_fabric.py"),
                        "--out", out],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert os.path.exists(out)
    return sha256_file(out)


def _alternate_model(seed: int, integer_model, alt_bias: bool):
    rng = np.random.default_rng(seed)
    from model2rtl.golden import IntegerModel
    w = F.derive_widths(F.FabricConfig())
    if alt_bias:
        i1 = integer_model.layer1_weight_indices.copy()
        i2 = integer_model.layer2_weight_indices.copy()
        lim1 = 1 << (w["layer1_bias_bits"] - 2)
        lim2 = 1 << (w["layer2_bias_bits"] - 2)
        b1 = rng.integers(-lim1, lim1, C.HIDDEN_DIM).astype(np.int64)
        b2 = rng.integers(-lim2, lim2, C.OUTPUT_DIM).astype(np.int64)
    else:
        i1 = rng.integers(0, C.K, (C.INPUT_DIM, C.HIDDEN_DIM)).astype(np.int64)
        i2 = rng.integers(0, C.K, (C.HIDDEN_DIM, C.OUTPUT_DIM)).astype(np.int64)
        b1 = integer_model.layer1_bias.copy()
        b2 = integer_model.layer2_bias.copy()
    m = IntegerModel(layer1_weight_indices=i1, layer2_weight_indices=i2,
                     layer1_bias=b1, layer2_bias=b2)
    m.validate()
    return m


@pytest.mark.parametrize("alt_bias,seed", [(False, 11), (True, 22)])
def test_fabric_sha_is_unchanged_when_model_parameters_change(
        alt_bias, seed, root, paths, integer_model, tmp_path):
    """Swap the trained NPZ for a different valid one and regenerate.

    The trained file is restored afterwards and its SHA-256 re-verified, so a
    failure inside this test cannot damage the Stage-0 artefact.
    """
    npz = paths["npz"]
    original_sha = sha256_file(npz)
    backup = str(tmp_path / "backup.npz")
    shutil.copyfile(npz, backup)

    out_a = str(tmp_path / "fabric_a.v")
    out_b = str(tmp_path / "fabric_b.v")
    try:
        sha_a = _regen(root, out_a)
        S.save_indices(npz, _alternate_model(seed, integer_model, alt_bias))
        assert sha256_file(npz) != original_sha, "the NPZ was not actually changed"
        sha_b = _regen(root, out_b)
    finally:
        shutil.copyfile(backup, npz)

    assert sha256_file(npz) == original_sha, \
        "the trained NPZ was not restored byte-identically"
    assert sha_a == sha_b, (
        "the fabric changed when the %s changed: %s != %s"
        % ("biases" if alt_bias else "weight indices", sha_a, sha_b))
    assert open(out_a).read() == open(out_b).read()


def test_committed_fabric_matches_a_fresh_generation(root, fabric_path, tmp_path):
    out = str(tmp_path / "fresh.v")
    assert _regen(root, out) == sha256_file(fabric_path), \
        "rtl/mnist_mlp_fabric.v is stale"


def test_fabric_is_identical_for_two_different_weight_sets_at_runtime(
        cfg, fabric_path, integer_model, mnist_test, tmp_path):
    """One fabric, two completely different weight sets, both correct.

    Stage 3 will repeat this through the ROM backends; proving it now shows the
    fabric holds no trained state at all.
    """
    from model2rtl import sim as SIM
    from model2rtl.golden import IntegerModel
    from conftest import require_tool
    require_tool("iverilog")
    x, _ = mnist_test

    alt = _alternate_model(99, integer_model, alt_bias=False)
    runs = []
    for name, m in (("trained", integer_model), ("alternate", alt)):
        out = SIM.simulate(str(tmp_path / name), cfg, m.layer1_weight_indices,
                           m.layer1_bias, m.layer2_weight_indices, m.layer2_bias,
                           x[:4], fabric_path=fabric_path)
        want = m.forward(x[:4])
        assert np.array_equal(out.logits, want), \
            "%s weight set mismatched the golden model" % name
        runs.append(out.logits)
    assert not np.array_equal(runs[0], runs[1]), \
        "the two weight sets produced identical logits; the test proves nothing"


# ---------------------------------------------------------------------------
# 3. no trained value can hide in the emitted Verilog
# ---------------------------------------------------------------------------

def architectural_literals(cfg) -> set:
    """Every integer the fabric is architecturally entitled to contain."""
    w = F.derive_widths(cfg)
    allowed = set(range(0, cfg.k + 1))                      # levels, states
    allowed |= {cfg.n_in, cfg.n_hidden, cfg.n_out, cfg.k}
    for v in w.values():
        if isinstance(v, int):
            allowed |= {abs(v), abs(v) - 1, abs(v) + 1}
    pw = w["product_bits"]
    for i in range(cfg.k + 1):                              # bank slice offsets
        allowed |= {i * pw, i * pw - 1}
    a2 = w["layer2_acc_bits"]
    for i in range(cfg.n_out + 1):                          # logit slice offsets
        allowed |= {i * a2, i * a2 - 1}
    allowed |= {w["act_bits"], w["act_max"], w["round_const"],
                w["round_const"] - 1}
    allowed |= {cfg.n_in - 1, cfg.n_hidden - 1, cfg.n_out - 1}
    return allowed


def test_no_numeric_literal_in_the_fabric_can_carry_a_trained_value(
        fabric_source, cfg):
    body = re.sub(r"//[^\n]*", "", fabric_source)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    allowed = architectural_literals(cfg)

    found = {int(t) for t in re.findall(r"(?<![\w'])(\d+)(?![\w'])", body)}
    unexplained = sorted(found - allowed)
    assert unexplained == [], \
        ("unexplained numeric literals in the fabric (possible baked-in trained "
         "value): %s" % unexplained)


def test_trained_biases_do_not_appear_in_the_fabric(fabric_source, integer_model,
                                                   cfg):
    """No trained bias appears as a literal.

    Values that are themselves architectural constants (a slice offset, a
    width) are excluded: the previous test already proves that EVERY literal in
    the file is architectural, so a bias that merely collides numerically with
    one of them carries no trained information.  Every other bias must be
    absent outright.
    """
    body = re.sub(r"//[^\n]*", "", fabric_source)
    allowed = architectural_literals(cfg)
    checked = 0
    for b in list(integer_model.layer1_bias) + list(integer_model.layer2_bias):
        v = abs(int(b))
        if v in allowed:
            continue
        checked += 1
        assert re.search(r"(?<![\w'])%d(?![\w'])" % v, body) is None, \
            "trained bias %d appears verbatim in the fabric" % int(b)
    assert checked >= 20, "too few biases were actually distinguishable"


def test_fabric_has_no_bulk_data_block(fabric_source, cfg):
    """A baked-in weight table would be enormous; the fabric is not."""
    assert len(fabric_source) < 60000
    assert "$readmem" not in fabric_source
    assert fabric_source.count("'h") <= 4
    # 25408 synapses could never fit
    assert fabric_source.count("=") < 1000
