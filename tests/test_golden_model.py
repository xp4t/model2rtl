"""Validations 3, 7, 10: determinism, accuracy, absence of silent overflow."""

import numpy as np
import pytest

from model2rtl import contract as C
from model2rtl.golden import (ContractViolation, IntegerModel, accuracy,
                              alphabet_lookup, requantize_relu_u8)


def test_integer_inference_is_deterministic(integer_model, mnist_test):
    x, _ = mnist_test
    a = integer_model.forward(x[:500])
    b = integer_model.forward(x[:500])
    c = integer_model.forward(x[:500])
    assert np.array_equal(a, b)
    assert np.array_equal(a, c)
    assert a.dtype == np.int64


def test_batching_does_not_change_results(integer_model, mnist_test):
    x, _ = mnist_test
    full = integer_model.forward(x[:300])
    chunked = np.concatenate([integer_model.forward(x[i:min(i + 37, 300)])
                              for i in range(0, 300, 37)], axis=0)
    assert np.array_equal(full, chunked)


def test_single_image_matches_batch(integer_model, mnist_test):
    x, _ = mnist_test
    batch = integer_model.forward(x[:16])
    for i in range(16):
        assert np.array_equal(integer_model.forward(x[i]), batch[i:i + 1])


def test_quantized_accuracy_above_90_percent(integer_model, mnist_test):
    x, y = mnist_test
    acc = accuracy(integer_model, x, y)
    assert acc > 0.90, "quantised integer accuracy %.4f is not > 0.90" % acc


def test_no_floating_point_in_the_integer_path(integer_model, mnist_test):
    x, _ = mnist_test
    w = alphabet_lookup(integer_model.layer1_weight_indices)
    assert np.issubdtype(w.dtype, np.integer)
    acc1 = integer_model.layer1_accumulate(x[:64])
    assert np.issubdtype(acc1.dtype, np.integer)
    h = requantize_relu_u8(acc1)
    assert np.issubdtype(h.dtype, np.integer)
    assert h.min() >= 0 and h.max() <= 255


def test_requantization_rule_is_round_half_up_then_clip():
    acc = np.array([-1000, -1, 0, 127, 128, 129, 255, 256, 383, 384,
                    65279, 65280, 65281, 1 << 20], dtype=np.int64)
    got = requantize_relu_u8(acc, shift=8)
    want = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 255, 255, 255, 255],
                    dtype=np.int64)
    assert np.array_equal(got, want)


def test_relu_is_applied_before_the_shift():
    """A negative accumulator must produce 0, never a rounded negative value."""
    acc = np.array([-1, -128, -129, -(1 << 20)], dtype=np.int64)
    assert np.array_equal(requantize_relu_u8(acc), np.zeros(4, dtype=np.int64))


def test_no_overflow_outside_declared_saturation_points(integer_model, mnist_test):
    """forward() width checks pass on the whole test set."""
    x, _ = mnist_test
    l1, l2 = C.layer1_widths(), C.layer2_widths()
    for s in range(0, x.shape[0], 2000):
        xb = x[s:s + 2000]
        acc1 = integer_model.layer1_accumulate(xb)
        assert acc1.min() >= -(1 << (l1.accumulator_bits - 1))
        assert acc1.max() <= (1 << (l1.accumulator_bits - 1)) - 1
        h = requantize_relu_u8(acc1)
        acc2 = integer_model.layer2_accumulate(h)
        assert acc2.min() >= -(1 << (l2.accumulator_bits - 1))
        assert acc2.max() <= (1 << (l2.accumulator_bits - 1)) - 1
        # forward() performs the same checks and must not raise
        integer_model.forward(xb, check_widths=True)


def test_worst_case_saturating_input_does_not_overflow(integer_model):
    """All-255 input drives the accumulators as hard as the contract allows."""
    x = np.full((1, 784), 255, dtype=np.int64)
    logits = integer_model.forward(x, check_widths=True)
    assert logits.shape == (1, 10)


def test_contract_violations_are_raised_not_silently_wrapped(integer_model):
    x = np.full((1, 784), 256, dtype=np.int64)
    with pytest.raises(ContractViolation):
        integer_model.forward(x)
    with pytest.raises(ContractViolation):
        integer_model.forward(np.zeros((1, 784), dtype=np.float32))
    with pytest.raises(ContractViolation):
        alphabet_lookup(np.array([16]))


def test_prediction_is_argmax_of_integer_logits(integer_model, mnist_test):
    x, _ = mnist_test
    logits = integer_model.forward(x[:200])
    assert np.array_equal(integer_model.predict(x[:200]), np.argmax(logits, axis=1))


def test_validate_rejects_illegal_parameters():
    good = IntegerModel(
        layer1_weight_indices=np.zeros((784, 32), dtype=np.int64),
        layer2_weight_indices=np.zeros((32, 10), dtype=np.int64),
        layer1_bias=np.zeros(32, dtype=np.int64),
        layer2_bias=np.zeros(10, dtype=np.int64))
    good.validate()
    bad = IntegerModel(
        layer1_weight_indices=np.full((784, 32), 16, dtype=np.int64),
        layer2_weight_indices=np.zeros((32, 10), dtype=np.int64),
        layer1_bias=np.zeros(32, dtype=np.int64),
        layer2_bias=np.zeros(10, dtype=np.int64))
    with pytest.raises(ContractViolation):
        bad.validate()
