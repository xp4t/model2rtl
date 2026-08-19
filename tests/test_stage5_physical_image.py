"""Stage 5: the two physical transformations must be exactly reversible.

The logical images stay authoritative.  Banking and byte padding are allowed to
change the physical representation and nothing else, so every one of these
tests is ultimately the same question: does decode(encode(x)) == x?
"""

import pytest

from model2rtl import phys_image as P
from model2rtl.param_image import IMAGE_ORDER, bias_bus_word, weight_bus_word


# -- banking ----------------------------------------------------------------

def test_layer1_is_banked_into_four_parallel_macros(physical_images):
    names = P.macros_of("weights_l1")
    assert len(names) == P.L1_BANKS == 4
    for b, n in enumerate(names):
        p = physical_images[n]
        assert p.depth == 784
        assert p.width == P.L1_BANK_BITS == 32
        assert p.bank_index == b
        assert p.logical_bit_slice == (32 * b, 32 * b + 31)


def test_banks_partition_the_logical_word_exactly(physical_images):
    slices = sorted(physical_images[n].logical_bit_slice
                    for n in P.macros_of("weights_l1"))
    covered = []
    for lo, hi in slices:
        covered.extend(range(lo, hi + 1))
    assert sorted(covered) == list(range(128))       # no gap, no overlap


def test_bank_rows_are_the_logical_slice(param_images, physical_images):
    logical = param_images["weights_l1"]
    for b in range(P.L1_BANKS):
        p = physical_images["weights_l1_b%d" % b]
        for a in range(logical.depth):
            assert p.rows[a] == (logical.rows[a] >> (32 * b)) & 0xFFFFFFFF


def test_every_logical_row_reassembles_from_the_banks(param_images,
                                                      physical_images):
    logical = param_images["weights_l1"]
    got = P.decode_logical_rows(physical_images, "weights_l1", logical.width)
    assert len(got) == 784
    assert got == list(logical.rows)


# -- bias padding -----------------------------------------------------------

@pytest.mark.parametrize("name,logical_bits", [("bias_l1", 22),
                                               ("bias_l2", 17)])
def test_bias_is_sign_padded_to_24_bits(physical_images, param_images,
                                        name, logical_bits):
    p = physical_images[name]
    assert p.width == P.BIAS_PHYS_BITS == 24
    assert p.sign_padded is True
    assert p.logical_width == logical_bits
    assert p.depth == param_images[name].depth


def test_padding_is_sign_extension_never_zero_extension(param_images,
                                                        physical_images):
    """A negative bias must have ones in the pad, not zeros."""
    for name in ("bias_l1", "bias_l2"):
        logical, p = param_images[name], physical_images[name]
        bits = logical.width
        negatives = 0
        for a, v in enumerate(logical.rows):
            pad = p.rows[a] >> bits
            if v >> (bits - 1):                      # negative
                negatives += 1
                assert pad == (1 << (24 - bits)) - 1, \
                    "%s row %d: negative value was zero extended" % (name, a)
            else:
                assert pad == 0
        assert negatives > 0, "%s has no negative value to test with" % name


@pytest.mark.parametrize("bits", [22, 17])
def test_special_bias_values_survive_the_round_trip(bits):
    """0, +1, -1 and both representable extremes."""
    for v in (0, 1, -1, (1 << (bits - 1)) - 1, -(1 << (bits - 1))):
        two = v & ((1 << bits) - 1)
        phys = P._sign_extend(two, bits, 24)
        assert phys >> 24 == 0
        back = P._truncate(phys, bits)
        signed = back - (1 << bits) if back >> (bits - 1) else back
        assert signed == v


def test_padding_does_not_change_any_bus_value(param_images, physical_images):
    for layer, name in ((0, "bias_l1"), (1, "bias_l2")):
        for a in range(param_images[name].depth):
            assert (P.bias_bus_word_from_physical(physical_images, layer, a)
                    == bias_bus_word(param_images, layer, a))


# -- the whole set ----------------------------------------------------------

def test_full_roundtrip_every_memory(param_images, physical_images):
    r = P.verify_roundtrip(physical_images, param_images)
    assert r["mismatches"] == 0
    assert r["rows_checked"] == 784 + 32 + 32 + 10
    for name in IMAGE_ORDER:
        assert r["per_memory"][name]["mismatches"] == 0


def test_weight_bus_is_unchanged_by_banking(param_images, physical_images):
    for layer, name in ((0, "weights_l1"), (1, "weights_l2")):
        for a in range(param_images[name].depth):
            assert (P.weight_bus_word_from_physical(physical_images, layer, a)
                    == weight_bus_word(param_images, layer, a))


def test_invalid_addresses_still_return_zero(physical_images):
    assert P.weight_bus_word_from_physical(physical_images, 0, 784) == 0
    assert P.weight_bus_word_from_physical(physical_images, 1, 32) == 0
    assert P.bias_bus_word_from_physical(physical_images, 0, 32) == 0
    assert P.bias_bus_word_from_physical(physical_images, 1, 10) == 0


def test_every_physical_width_is_byte_granular(physical_images):
    """The whole reason the transformations exist."""
    for p in physical_images.values():
        assert p.width % 8 == 0
        assert p.word_size_bytes() == p.width // 8


def test_physical_images_are_hashable_and_stable(physical_images,
                                                 param_images):
    from model2rtl.phys_image import build_physical_images
    again = build_physical_images(param_images)
    for n in P.PHYS_ORDER:
        assert again[n].sha256() == physical_images[n].sha256()
        assert len(physical_images[n].sha256()) == 64


def test_physical_image_hashes_differ_from_logical(physical_images,
                                                   param_images):
    """A physical image is a different object and must not collide."""
    logical = {i.sha256() for i in param_images.values()}
    for n in P.PHYS_ORDER:
        assert physical_images[n].sha256() not in logical


def test_broken_padding_is_detected(param_images, physical_images):
    """The reverse map must fail closed, not silently truncate."""
    import dataclasses
    p = physical_images["bias_l2"]
    rows = list(p.rows)
    rows[0] ^= 1 << 23                     # corrupt the pad only
    bad = dict(physical_images)
    bad["bias_l2"] = dataclasses.replace(p, rows=tuple(rows))
    with pytest.raises(P.PhysImageError):
        P.decode_logical_rows(bad, "bias_l2", 17)
