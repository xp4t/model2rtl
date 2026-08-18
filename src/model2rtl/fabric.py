"""Stage 1: the fixed Multiply-Select-Add compute fabric.

This module contains three things and no trained parameter of any kind:

  * :class:`FabricConfig` / :func:`derive_widths` -- the topology and the
    arithmetic widths, all derived from the Stage-0 contract formulas.
  * :func:`msa_forward` -- an input-serial Multiply-Select-Add *reference*
    implementation in Python.  It reorganises the Stage-0 golden model into the
    order the hardware executes it and must be bit-identical to it.
  * :func:`emit_fabric_verilog` -- the Verilog-2001 emitter, plus a
    test-only testbench emitter.

Execution model implemented by the fabric (input-serial / output-parallel):

    for each input activation x_i:
        products[k] = x_i * alphabet[k]        for k = 0 .. K-1   (K generators)
        for each output neuron j:
            acc[j] += products[ weight_index[i][j] ]

    then, per neuron j:  acc[j] += bias[j], and the layer epilogue.

Exactly K product generators exist in the whole design.  They are shared by
every output neuron of the currently active layer, and reused across input
cycles and across both layers.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

import numpy as np

from . import contract as C


# --------------------------------------------------------------------------
# Topology / width derivation
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class FabricConfig:
    """Everything the fabric generator is allowed to know.

    Deliberately holds no trained value: only topology, K, the activation
    format and the fixed arithmetic contract.
    """

    n_in: int = C.INPUT_DIM
    n_hidden: int = C.HIDDEN_DIM
    n_out: int = C.OUTPUT_DIM
    k: int = C.K
    act_bits: int = C.ACT_BITS
    requant_shift: int = C.HIDDEN_REQUANT_SHIFT
    module_name: str = "mnist_mlp_fabric"

    @property
    def alphabet(self) -> np.ndarray:
        """alphabet[i] = i - K/2, the fixed two's-complement int4 levels."""
        return np.arange(self.k, dtype=np.int64) - (self.k // 2)

    @property
    def index_bits(self) -> int:
        return int(np.ceil(np.log2(self.k)))


def _bits_unsigned(hi: int) -> int:
    return C.bits_for_unsigned_range(0, hi)


def derive_widths(cfg: FabricConfig) -> Dict[str, int]:
    """All RTL widths, derived from topology + alphabet only.

    Uses exactly the Stage-0 formulas (contract.bits_for_signed_range over the
    exact worst-case product / dot-product ranges).  For the production
    topology the result is asserted equal to the Stage-0 contract.
    """
    act_max = (1 << cfg.act_bits) - 1
    alpha = cfg.alphabet
    p_lo, p_hi = C.product_range(0, act_max, alpha)
    prod_bits = C.bits_for_signed_range(p_lo, p_hi)

    def layer(n_terms: int):
        d_lo, d_hi = n_terms * p_lo, n_terms * p_hi
        dot_bits = C.bits_for_signed_range(d_lo, d_hi)
        bias_bits = dot_bits            # bias may span the full dot range
        acc_bits = C.bits_for_signed_range(d_lo - (1 << (bias_bits - 1)),
                                           d_hi + (1 << (bias_bits - 1)) - 1)
        return dot_bits, bias_bits, acc_bits

    dot1, bias1, acc1 = layer(cfg.n_in)
    dot2, bias2, acc2 = layer(cfg.n_hidden)

    return {
        "product_bits": prod_bits,
        "product_min": p_lo,
        "product_max": p_hi,
        "layer1_dot_bits": dot1,
        "layer1_bias_bits": bias1,
        "layer1_acc_bits": acc1,
        "layer2_dot_bits": dot2,
        "layer2_bias_bits": bias2,
        "layer2_acc_bits": acc2,
        "index_bits": cfg.index_bits,
        "act_bits": cfg.act_bits,
        # interface widths
        "weight_word_bits": max(cfg.n_hidden, cfg.n_out) * cfg.index_bits,
        "weight_addr_bits": _bits_unsigned(max(cfg.n_in, cfg.n_hidden)),
        "bias_data_bits": max(bias1, bias2),
        "bias_addr_bits": _bits_unsigned(max(cfg.n_hidden, cfg.n_out)),
        "logits_bits": cfg.n_out * acc2,
        "prediction_bits": max(1, _bits_unsigned(cfg.n_out - 1)),
        "round_const": 1 << (cfg.requant_shift - 1),
        "requant_shift": cfg.requant_shift,
        "act_max": act_max,
    }


def check_production_widths(cfg: FabricConfig) -> None:
    """Fail closed if the derived widths drift from the frozen Stage-0 contract."""
    if (cfg.n_in, cfg.n_hidden, cfg.n_out, cfg.k) != (
            C.INPUT_DIM, C.HIDDEN_DIM, C.OUTPUT_DIM, C.K):
        return  # synthetic test topology: nothing to compare against
    w = derive_widths(cfg)
    l1, l2 = C.layer1_widths(), C.layer2_widths()
    expected = {
        "product_bits": l1.product_bits,
        "layer1_dot_bits": l1.dot_bits,
        "layer1_bias_bits": l1.bias_bits,
        "layer1_acc_bits": l1.accumulator_bits,
        "layer2_dot_bits": l2.dot_bits,
        "layer2_bias_bits": l2.bias_bits,
        "layer2_acc_bits": l2.accumulator_bits,
        "requant_shift": C.HIDDEN_REQUANT_SHIFT,
    }
    for key, want in expected.items():
        if w[key] != want:
            raise ValueError("Stage-1 width %s = %d contradicts the frozen "
                             "Stage-0 contract value %d" % (key, w[key], want))
    if not np.array_equal(cfg.alphabet, C.ALPHABET.astype(np.int64)):
        raise ValueError("Stage-1 alphabet contradicts the Stage-0 alphabet")


# --------------------------------------------------------------------------
# Input-serial Multiply-Select-Add reference model
# --------------------------------------------------------------------------

def product_bank(x: int, cfg: FabricConfig) -> List[int]:
    """The K shared products for one activation.  This is the whole point."""
    return [int(x) * int(a) for a in cfg.alphabet]


def msa_layer(x_vec: np.ndarray, indices: np.ndarray, bias: np.ndarray,
              cfg: FabricConfig) -> np.ndarray:
    """One layer, executed the way the RTL executes it: input-serial.

    x_vec     : (n_in,) integer activations
    indices   : (n_in, n_out) weight indices, Stage-0 orientation
    """
    n_out = indices.shape[1]
    acc = np.zeros(n_out, dtype=np.int64)
    for i in range(indices.shape[0]):
        bank = product_bank(int(x_vec[i]), cfg)      # K shared products
        row = indices[i]
        for j in range(n_out):
            acc[j] += bank[int(row[j])]              # select, then accumulate
    return acc + bias.astype(np.int64)


def requantize(acc: np.ndarray, cfg: FabricConfig) -> np.ndarray:
    relu = np.maximum(acc, 0)
    shifted = (relu + (1 << (cfg.requant_shift - 1))) >> cfg.requant_shift
    return np.clip(shifted, 0, (1 << cfg.act_bits) - 1)


def msa_forward(x: np.ndarray, i1: np.ndarray, b1: np.ndarray,
                i2: np.ndarray, b2: np.ndarray,
                cfg: FabricConfig = FabricConfig()) -> np.ndarray:
    """Full input-serial MSA inference for one image. Returns signed logits."""
    acc1 = msa_layer(np.asarray(x, dtype=np.int64), i1, b1, cfg)
    hidden = requantize(acc1, cfg)
    return msa_layer(hidden, i2, b2, cfg)


def msa_predict(x: np.ndarray, i1, b1, i2, b2,
                cfg: FabricConfig = FabricConfig()) -> int:
    return int(np.argmax(msa_forward(x, i1, b1, i2, b2, cfg)))


# --------------------------------------------------------------------------
# Weight-word packing (the Stage-2 ROM contract)
# --------------------------------------------------------------------------

def pack_weight_words(indices: np.ndarray, cfg: FabricConfig,
                      word_bits: int | None = None) -> List[int]:
    """Pack one ROM word per input feature.

    Orientation is the Stage-0 orientation, [in_features, out_features]:

        word[i] holds every output neuron's index for input feature i
        weight_index[i][j] = word[i][ j*INDEX_BITS +: INDEX_BITS ]

    i.e. neuron j occupies bits [j*4+3 : j*4], neuron 0 in the least
    significant nibble.  This convention is fixed here and tested in RTL.
    """
    w = derive_widths(cfg)
    word_bits = w["weight_word_bits"] if word_bits is None else word_bits
    n_in, n_out = indices.shape
    words = []
    for i in range(n_in):
        acc = 0
        for j in range(n_out):
            idx = int(indices[i, j])
            if not 0 <= idx < cfg.k:
                raise ValueError("weight index out of range")
            acc |= idx << (j * cfg.index_bits)
        if acc >> word_bits:
            raise ValueError("packed word overflows %d bits" % word_bits)
        words.append(acc)
    return words


def unpack_weight_word(word: int, n_out: int, cfg: FabricConfig) -> List[int]:
    mask = (1 << cfg.index_bits) - 1
    return [(word >> (j * cfg.index_bits)) & mask for j in range(n_out)]


def to_twos_complement(value: int, bits: int) -> int:
    if not -(1 << (bits - 1)) <= value <= (1 << (bits - 1)) - 1:
        raise ValueError("%d does not fit in %d signed bits" % (value, bits))
    return value & ((1 << bits) - 1)
