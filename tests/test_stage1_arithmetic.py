"""Stage-1 arithmetic: the Multiply-Select-Add reorganisation must be
bit-identical to the Stage-0 golden model, and the RTL product bank must be
exactly right for the signed/unsigned corner cases.
"""

import os

import numpy as np
import pytest

from model2rtl import contract as C
from model2rtl import fabric as F
from model2rtl import golden as G
from model2rtl import sim as SIM
from conftest import require_tool


# ---------------------------------------------------------------------------
# Python-level: MSA reorganisation vs the Stage-0 golden model
# ---------------------------------------------------------------------------

def _random_model(rng, cfg=F.FabricConfig()):
    w = F.derive_widths(cfg)
    b1lim = 1 << (w["layer1_bias_bits"] - 2)
    b2lim = 1 << (w["layer2_bias_bits"] - 2)
    return (rng.integers(0, cfg.k, (cfg.n_in, cfg.n_hidden)).astype(np.int64),
            rng.integers(-b1lim, b1lim, cfg.n_hidden).astype(np.int64),
            rng.integers(0, cfg.k, (cfg.n_hidden, cfg.n_out)).astype(np.int64),
            rng.integers(-b2lim, b2lim, cfg.n_out).astype(np.int64))


def test_product_bank_matches_the_alphabet(cfg):
    for x in (0, 1, 2, 127, 128, 254, 255):
        bank = F.product_bank(x, cfg)
        assert len(bank) == cfg.k == 16
        assert bank == [x * int(a) for a in cfg.alphabet]
        assert min(bank) >= C.layer1_widths().product_min
        assert max(bank) <= C.layer1_widths().product_max


def test_msa_matches_golden_on_the_trained_model(integer_model, mnist_test, cfg):
    x, _ = mnist_test
    ref = integer_model.forward(x[:25])
    for n in range(25):
        got = F.msa_forward(x[n], integer_model.layer1_weight_indices,
                            integer_model.layer1_bias,
                            integer_model.layer2_weight_indices,
                            integer_model.layer2_bias, cfg)
        assert np.array_equal(got, ref[n]), "MSA differs from golden on image %d" % n


def test_msa_matches_golden_on_random_models_and_activations(cfg):
    rng = np.random.default_rng(20250818)
    for trial in range(3):
        i1, b1, i2, b2 = _random_model(rng, cfg)
        model = G.IntegerModel(layer1_weight_indices=i1, layer2_weight_indices=i2,
                               layer1_bias=b1, layer2_bias=b2)
        model.validate()
        x = rng.integers(0, 256, (5, cfg.n_in)).astype(np.int64)
        ref = model.forward(x)
        for n in range(x.shape[0]):
            got = F.msa_forward(x[n], i1, b1, i2, b2, cfg)
            assert np.array_equal(got, ref[n]), "trial %d image %d" % (trial, n)


def test_msa_matches_golden_on_edge_activations(integer_model, cfg):
    edge = np.array([
        np.zeros(cfg.n_in),
        np.full(cfg.n_in, 255),
        np.full(cfg.n_in, 1),
        np.tile([0, 255], cfg.n_in // 2),
        np.tile([255, 0], cfg.n_in // 2),
    ], dtype=np.int64)
    ref = integer_model.forward(edge)
    for n in range(edge.shape[0]):
        got = F.msa_forward(edge[n], integer_model.layer1_weight_indices,
                            integer_model.layer1_bias,
                            integer_model.layer2_weight_indices,
                            integer_model.layer2_bias, cfg)
        assert np.array_equal(got, ref[n])


def test_weight_word_packing_round_trip(integer_model, cfg):
    idx = integer_model.layer1_weight_indices
    words = F.pack_weight_words(idx, cfg)
    assert len(words) == cfg.n_in
    for i in (0, 1, 391, 783):
        assert F.unpack_weight_word(words[i], cfg.n_hidden, cfg) == \
            [int(v) for v in idx[i]]
    # neuron 0 must live in the least significant nibble
    assert words[0] & 0xF == int(idx[0, 0])
    assert (words[0] >> 4) & 0xF == int(idx[0, 1])


def test_requantization_edge_cases_match_contract(cfg):
    acc = np.array([-1, 0, 127, 128, 255, 256, 383, 384, 65279, 65280,
                    65281, 1 << 22], dtype=np.int64)
    assert np.array_equal(F.requantize(acc, cfg), G.requantize_relu_u8(acc))


# ---------------------------------------------------------------------------
# RTL-level: exact signed product arithmetic in the real production fabric
# ---------------------------------------------------------------------------

REQUIRED_PAIRS = [(x, wv) for x in (0, 1, 255) for wv in (-8, -1, 0, 1, 7)]


@pytest.mark.parametrize("activation", [0, 1, 255])
def test_rtl_product_bank_exact_for_signed_corner_cases(activation, cfg,
                                                        fabric_path, tmp_path):
    """Drive one non-zero activation and read back every neuron's dot product.

    Input feature 0 carries activation `activation` and neuron j selects weight
    index j % 16, so acc1[j] must equal exactly activation * alphabet[j % 16].
    Every other input feature carries activation 0 AND weight index 8 (level 0),
    so it contributes nothing.  This exercises the real production fabric, not
    a stub.
    """
    require_tool("iverilog")
    i1 = np.full((cfg.n_in, cfg.n_hidden), 8, dtype=np.int64)
    i1[0] = [j % cfg.k for j in range(cfg.n_hidden)]
    b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
    i2 = np.full((cfg.n_hidden, cfg.n_out), 8, dtype=np.int64)
    b2 = np.zeros(cfg.n_out, dtype=np.int64)

    img = np.zeros((1, cfg.n_in), dtype=np.int64)
    img[0, 0] = activation

    out = SIM.simulate(str(tmp_path), cfg, i1, b1, i2, b2, img,
                       fabric_path=fabric_path)
    expect = np.array([activation * int(cfg.alphabet[j % cfg.k])
                       for j in range(cfg.n_hidden)], dtype=np.int64)
    assert np.array_equal(out.acc1[0], expect), \
        "RTL products wrong for x=%d: %s vs %s" % (activation, out.acc1[0], expect)

    # explicitly confirm the required (x, weight) pairs were covered
    covered = {(activation, int(cfg.alphabet[j % cfg.k]))
               for j in range(cfg.n_hidden)}
    for wv in (-8, -1, 0, 1, 7):
        assert (activation, wv) in covered
        j = int(np.where(cfg.alphabet == wv)[0][0])
        assert int(out.acc1[0][j]) == activation * wv

    # no wraparound anywhere
    pmin, pmax = C.layer1_widths().product_min, C.layer1_widths().product_max
    assert out.acc1[0].min() >= pmin and out.acc1[0].max() <= pmax


def test_rtl_argmax_tie_breaks_to_lowest_index(cfg, fabric_path, tmp_path):
    """With all weights at level 0 the logits are exactly the layer-2 biases."""
    require_tool("iverilog")
    i1 = np.full((cfg.n_in, cfg.n_hidden), 8, dtype=np.int64)
    b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
    i2 = np.full((cfg.n_hidden, cfg.n_out), 8, dtype=np.int64)
    img = np.zeros((3, cfg.n_in), dtype=np.int64)

    cases = [
        np.array([5, 5, 1, 0, -1, 0, 0, 0, 0, 0], dtype=np.int64),   # tie at 0,1
        np.array([1, 7, 7, 7, 0, 0, 0, 0, 0, 0], dtype=np.int64),    # tie at 1,2,3
        np.array([-3, -3, -3, -3, -3, -3, -3, -3, -3, -3], dtype=np.int64),
    ]
    for n, b2 in enumerate(cases):
        out = SIM.simulate(str(tmp_path / ("tie%d" % n)), cfg, i1, b1, i2, b2,
                           img[:1], fabric_path=fabric_path)
        assert np.array_equal(out.logits[0], b2), \
            "logits should equal the biases: %s" % out.logits[0]
        assert out.predictions[0] == int(np.argmax(b2)), \
            "RTL argmax %d != numpy argmax %d" % (out.predictions[0],
                                                  int(np.argmax(b2)))
        # numpy argmax returns the lowest index on ties; so must the RTL
        assert out.predictions[0] == int(np.flatnonzero(b2 == b2.max())[0])


def test_rtl_hidden_saturation_and_relu(cfg, fabric_path, tmp_path):
    """Force layer-1 accumulators far above and far below the uint8 window."""
    require_tool("iverilog")
    # all inputs 255, all weights +7  -> acc1 = 784*255*7 = 1399440 -> saturates
    i1_hi = np.full((cfg.n_in, cfg.n_hidden), 15, dtype=np.int64)
    # all weights -8 -> acc1 strongly negative -> ReLU must give hidden = 0
    i1_lo = np.full((cfg.n_in, cfg.n_hidden), 0, dtype=np.int64)
    b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
    i2 = np.full((cfg.n_hidden, cfg.n_out), 8, dtype=np.int64)
    b2 = np.zeros(cfg.n_out, dtype=np.int64)
    img = np.full((1, cfg.n_in), 255, dtype=np.int64)

    hi = SIM.simulate(str(tmp_path / "hi"), cfg, i1_hi, b1, i2, b2, img,
                      fabric_path=fabric_path)
    assert (hi.acc1[0] == 784 * 255 * 7).all()
    assert (hi.hidden[0] == 255).all(), "uint8 saturation not applied"

    lo = SIM.simulate(str(tmp_path / "lo"), cfg, i1_lo, b1, i2, b2, img,
                      fabric_path=fabric_path)
    assert (lo.acc1[0] == 784 * 255 * -8).all()
    assert (lo.hidden[0] == 0).all(), "ReLU not applied before the shift"


def test_rtl_rounding_is_round_half_up(cfg, fabric_path, tmp_path):
    """Craft exact accumulator values that straddle the rounding boundary.

    Input feature 0 carries activation 1 with weight level +1, so acc1 = 1.
    The bias then sets the accumulator to any value we like.
    """
    require_tool("iverilog")
    i1 = np.full((cfg.n_in, cfg.n_hidden), 8, dtype=np.int64)
    i1[0] = 9  # alphabet level +1
    img = np.zeros((1, cfg.n_in), dtype=np.int64)
    img[0, 0] = 1

    # acc1[j] = 1 + b1[j]; pick b1 so acc1 hits the interesting points
    targets = [-1, 0, 127, 128, 129, 255, 256, 383, 384, 65279, 65280, 65281]
    b1 = np.zeros(cfg.n_hidden, dtype=np.int64)
    for j, t in enumerate(targets):
        b1[j] = t - 1
    i2 = np.full((cfg.n_hidden, cfg.n_out), 8, dtype=np.int64)
    b2 = np.zeros(cfg.n_out, dtype=np.int64)

    out = SIM.simulate(str(tmp_path), cfg, i1, b1, i2, b2, img,
                       fabric_path=fabric_path)
    acc = np.array(targets, dtype=np.int64)
    expect = G.requantize_relu_u8(acc)
    assert np.array_equal(out.hidden[0][:len(targets)], expect), \
        "%s vs %s" % (out.hidden[0][:len(targets)], expect)
