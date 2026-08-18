"""Validation 9: the analytical widths are sufficient for worst-case use."""

import itertools

import numpy as np
import pytest

from model2rtl import contract as C


def test_alphabet_is_exactly_16_signed_levels():
    assert C.K == 16
    assert len(C.ALPHABET) == 16
    assert len(set(C.ALPHABET.tolist())) == 16
    assert C.ALPHABET.tolist() == list(range(-8, 8))
    assert all(C.ALPHABET[i] == i - C.ALPHABET_OFFSET for i in range(C.K))


def test_bits_for_signed_range_is_tight():
    assert C.bits_for_signed_range(-1, 0) == 1
    assert C.bits_for_signed_range(-128, 127) == 8
    assert C.bits_for_signed_range(-128, 128) == 9
    assert C.bits_for_signed_range(0, 127) == 8


def test_product_width_covers_every_activation_and_level():
    w = C.layer1_widths()
    lo = -(1 << (w.product_bits - 1))
    hi = (1 << (w.product_bits - 1)) - 1
    for a, k in itertools.product(range(C.ACT_MIN, C.ACT_MAX + 1),
                                  C.ALPHABET.tolist()):
        assert lo <= a * k <= hi
    # and one bit narrower must NOT be enough
    lo2 = -(1 << (w.product_bits - 2))
    hi2 = (1 << (w.product_bits - 2)) - 1
    worst = max(abs(C.ACT_MAX * C.ALPHABET.min()), abs(C.ACT_MAX * C.ALPHABET.max()))
    assert not (lo2 <= -worst and worst <= hi2)


@pytest.mark.parametrize("widths,n_terms", [(C.layer1_widths(), C.INPUT_DIM),
                                            (C.layer2_widths(), C.HIDDEN_DIM)])
def test_accumulator_width_covers_worst_case_dot_product_plus_bias(widths, n_terms):
    lo = -(1 << (widths.accumulator_bits - 1))
    hi = (1 << (widths.accumulator_bits - 1)) - 1
    d_lo = n_terms * C.ACT_MAX * int(C.ALPHABET.min())
    d_hi = n_terms * C.ACT_MAX * int(C.ALPHABET.max())
    b_lo = -(1 << (widths.bias_bits - 1))
    b_hi = (1 << (widths.bias_bits - 1)) - 1
    assert lo <= d_lo + b_lo
    assert d_hi + b_hi <= hi


def test_accumulator_width_is_not_over_provisioned_by_more_than_one_bit():
    for w in (C.layer1_widths(), C.layer2_widths()):
        needed = C.bits_for_signed_range(w.accumulator_min, w.accumulator_max)
        assert w.accumulator_bits == needed


def test_worst_case_dot_product_matches_brute_force_extreme():
    """Directly construct the worst-case input and confirm the declared range."""
    w = C.layer2_widths()
    x = np.full(C.HIDDEN_DIM, C.ACT_MAX, dtype=np.int64)
    w_min = np.full(C.HIDDEN_DIM, C.ALPHABET.min(), dtype=np.int64)
    w_max = np.full(C.HIDDEN_DIM, C.ALPHABET.max(), dtype=np.int64)
    assert int(x @ w_min) == w.dot_min
    assert int(x @ w_max) == w.dot_max


def test_msa_analysis_and_crossover():
    r = C.msa_report()
    assert r["layer1"]["naive_multipliers"] == 784 * 32
    assert r["layer1"]["shared_product_generators"] == 784 * 16
    assert r["layer1"]["sharing_reduces_product_generators"] is True
    assert r["layer2"]["naive_multipliers"] == 32 * 10
    assert r["layer2"]["shared_product_generators"] == 32 * 16
    # layer 2 fanout is 10 < K = 16, so sharing must be reported as a loss
    assert r["layer2"]["sharing_reduces_product_generators"] is False
    assert r["layer2"]["shared_product_generators"] > r["layer2"]["naive_multipliers"]


def test_storage_report():
    s = C.storage_report()
    assert s["layer1_synapses"] == 784 * 32
    assert s["layer2_synapses"] == 32 * 10
    assert s["total_synapses"] == 784 * 32 + 32 * 10
    assert s["total_index_bits"] == s["total_synapses"] * 4
    assert s["total_index_bytes"] == s["total_index_bits"] // 8
