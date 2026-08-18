"""The canonical parameter images are the single source of truth."""

import json
import os

import numpy as np
import pytest

from model2rtl import contract as C
from model2rtl.fabric import FabricConfig
from model2rtl.param_image import (IMAGE_ORDER, ParamImage, bias_bus_word,
                                   build_images, default_dir, read_manifest,
                                   unpack_weight_image, weight_bus_word)


def test_four_images_with_the_required_shapes(param_images):
    assert set(param_images) == set(IMAGE_ORDER)
    assert (param_images["weights_l1"].depth,
            param_images["weights_l1"].width) == (784, 128)
    assert (param_images["weights_l2"].depth,
            param_images["weights_l2"].width) == (32, 40)
    assert (param_images["bias_l1"].depth, param_images["bias_l1"].width) == (32, 22)
    assert (param_images["bias_l2"].depth, param_images["bias_l2"].width) == (10, 17)


def test_images_are_deterministic(integer_model):
    a = build_images(integer_model)
    b = build_images(integer_model)
    for n in IMAGE_ORDER:
        assert a[n].sha256() == b[n].sha256()
        assert a[n].canonical_bytes() == b[n].canonical_bytes()


def test_every_weight_nibble_round_trips_to_the_trained_npz(param_images,
                                                            integer_model):
    """25,408 / 25,408 weight indices must come back exactly."""
    cfg = FabricConfig()
    l1 = unpack_weight_image(param_images["weights_l1"], 32, cfg)
    l2 = unpack_weight_image(param_images["weights_l2"], 10, cfg)
    assert l1.shape == (784, 32) and l2.shape == (32, 10)
    assert np.array_equal(l1, integer_model.layer1_weight_indices)
    assert np.array_equal(l2, integer_model.layer2_weight_indices)
    assert l1.size + l2.size == 25408


def test_every_bias_round_trips_bit_exactly(param_images, integer_model):
    assert param_images["bias_l1"].signed_rows() == \
        [int(v) for v in integer_model.layer1_bias]
    assert param_images["bias_l2"].signed_rows() == \
        [int(v) for v in integer_model.layer2_bias]


def test_neuron_zero_is_the_least_significant_nibble(param_images, integer_model):
    row = param_images["weights_l1"].rows[0]
    for j in range(32):
        assert (row >> (4 * j)) & 0xF == int(integer_model.layer1_weight_indices[0, j])


def test_layer2_bias_is_sign_extended_never_zero_extended(param_images):
    negatives = [i for i, v in enumerate(param_images["bias_l2"].signed_rows())
                 if v < 0]
    assert negatives, "no negative layer-2 bias to test with"
    for i in negatives:
        bus = bias_bus_word(param_images, 1, i)
        assert bus >> 17 == 0b11111, "high bits are not a sign extension"
        assert bus - (1 << 22) == param_images["bias_l2"].signed_rows()[i]


def test_invalid_addresses_return_zero_and_do_not_alias(param_images):
    assert weight_bus_word(param_images, 0, 784) == 0
    assert weight_bus_word(param_images, 1, 32) == 0
    assert weight_bus_word(param_images, 1, 1023) == 0
    assert bias_bus_word(param_images, 0, 32) == 0
    assert bias_bus_word(param_images, 1, 10) == 0
    # an out-of-range layer-2 address must not wrap onto a valid row
    for a in range(32, 1024):
        assert weight_bus_word(param_images, 1, a) == 0


def test_layer2_weight_word_leaves_the_high_bus_bits_zero(param_images):
    for a in range(32):
        assert weight_bus_word(param_images, 1, a) >> 40 == 0


def test_written_manifest_matches_the_in_memory_images(root, param_images):
    d = default_dir(root)
    if not os.path.exists(os.path.join(d, "manifest.json")):
        pytest.skip("run scripts/gen_weight_rom_portable.py first")
    man = read_manifest(d)
    for n in IMAGE_ORDER:
        assert man["images"][n]["sha256"] == param_images[n].sha256()
        assert man["images"][n]["depth"] == param_images[n].depth
        assert man["images"][n]["width"] == param_images[n].width
        blob = open(os.path.join(d, n + ".bin"), "rb").read()
        assert blob == param_images[n].canonical_bytes()


def test_image_rejects_out_of_range_rows():
    with pytest.raises(ValueError):
        ParamImage(name="bad", depth=2, width=4, rows=(0, 16),
                   packing="", orientation="", signed=False)
    with pytest.raises(ValueError):
        ParamImage(name="bad", depth=3, width=4, rows=(0, 1),
                   packing="", orientation="", signed=False)
