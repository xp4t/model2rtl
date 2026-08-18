"""Validations 1, 2, 8: index legality, alphabet reconstruction, shapes."""

import numpy as np

from model2rtl import contract as C


def test_shapes_are_exactly_784x32_and_32x10(integer_model):
    assert integer_model.layer1_weight_indices.shape == (784, 32)
    assert integer_model.layer2_weight_indices.shape == (32, 10)
    assert integer_model.layer1_bias.shape == (32,)
    assert integer_model.layer2_bias.shape == (10,)


def test_every_index_is_an_integer_in_0_15(integer_model):
    for w in (integer_model.layer1_weight_indices,
              integer_model.layer2_weight_indices):
        assert np.issubdtype(w.dtype, np.integer)
        assert w.min() >= 0
        assert w.max() < 16
        assert np.array_equal(w, np.round(w))


def test_npz_stores_indices_as_uint8_and_biases_as_int32(paths):
    with np.load(paths["npz"]) as z:
        assert z["layer1_weight_indices"].dtype == np.uint8
        assert z["layer2_weight_indices"].dtype == np.uint8
        assert z["layer1_bias"].dtype == np.int32
        assert z["layer2_bias"].dtype == np.int32
        assert set(z.files) == {"layer1_weight_indices", "layer2_weight_indices",
                                "layer1_bias", "layer2_bias"}


def test_alphabet_lookup_reconstructs_quantized_weights(integer_model, stage0_report):
    """alphabet[index] must reproduce the quantised weight tensors exactly."""
    for name, idx in (("layer1", integer_model.layer1_weight_indices),
                      ("layer2", integer_model.layer2_weight_indices)):
        w = C.ALPHABET[idx]
        # round-trip: value -> index -> value
        back = (w + C.ALPHABET_OFFSET).astype(np.int64)
        assert np.array_equal(back, idx)
        assert int(w.min()) == stage0_report[name]["min_quantized_weight"]
        assert int(w.max()) == stage0_report[name]["max_quantized_weight"]
        assert w.min() >= -8 and w.max() <= 7


def test_biases_fit_declared_widths(integer_model):
    for name, b in (("layer1", integer_model.layer1_bias),
                    ("layer2", integer_model.layer2_bias)):
        bits = C.BIAS_BITS[name]
        assert b.min() >= -(1 << (bits - 1))
        assert b.max() <= (1 << (bits - 1)) - 1


def test_index_histogram_matches_report(integer_model, stage0_report):
    for name, idx in (("layer1", integer_model.layer1_weight_indices),
                      ("layer2", integer_model.layer2_weight_indices)):
        hist = np.bincount(idx.ravel(), minlength=16).tolist()
        assert hist == stage0_report[name]["weight_index_histogram"]
        assert sum(hist) == idx.size
