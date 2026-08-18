"""Fixed integer arithmetic contract for the model2rtl MNIST MLP fabric.

Everything in this module is *architecture level*: it depends only on the
topology, on K, on the activation format and on the fixed weight alphabet.
It never depends on trained parameter values.

The trained model contributes exactly two kinds of data:

  * per-synapse 4-bit weight indices  (model/mnist_weights_indices.npz)
  * per-neuron integer biases         (model/mnist_weights_indices.npz)

Both are model parameters and live outside the fixed compute fabric.

Pipeline implemented by the contract (and, later, by the RTL):

    uint8 activation
      -> 4-bit weight index
      -> alphabet lookup (signed int4 level)
      -> signed integer product
      -> widened signed accumulation
      -> + signed integer bias
      -> ReLU (hidden layer only)
      -> round-half-up arithmetic right shift by a FIXED shift
      -> saturate to uint8
      -> next layer

The output layer stops after the bias: logits are signed integers and the
prediction is argmax(logits). No requantisation is applied to the logits
because argmax is invariant under a common positive scaling.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Tuple

import numpy as np

# --------------------------------------------------------------------------
# Architectural constants
# --------------------------------------------------------------------------

#: Number of weight levels (size of the quantisation alphabet).
K = 16

#: Weight index width in bits.
WEIGHT_INDEX_BITS = 4

#: Activation width in bits (unsigned).
ACT_BITS = 8

#: Activation representation is unsigned with zero-point 0.
ACT_SIGNED = False
ACT_MIN = 0
ACT_MAX = (1 << ACT_BITS) - 1  # 255

#: The weight alphabet is the plain two's-complement int4 range.
#: alphabet[index] = index - 8, i.e. levels -8 .. +7.
#: It is architecture level: it never changes with the trained model.
ALPHABET_OFFSET = 1 << (WEIGHT_INDEX_BITS - 1)  # 8
ALPHABET = np.arange(K, dtype=np.int32) - ALPHABET_OFFSET  # [-8 .. +7]
ALPHABET_SIGNED = True
WEIGHT_VALUE_BITS = WEIGHT_INDEX_BITS  # signed 4-bit values

#: Hidden-layer requantisation shift.  Fixed architectural constant.
#:
#: It was chosen once, by the `--sweep-hidden-shift` diagnostic in
#: scripts/train_mnist_mlp.py, and then frozen into this contract.  Shifts 5
#: through 10 all landed within ~1.9 percentage points of each other on the
#: validation split, so the choice is not accuracy critical; 8 is used because
#: it is the largest shift that still keeps the observed hidden activations
#: inside uint8 without any saturation, which gives the cleanest hardware
#: semantics (a whole-byte shift, and a saturation path that is present for
#: safety rather than exercised in normal operation).
#:
#: It is NOT re-derived per trained model.  A different trained index set uses
#: the same shift, so the compute fabric stays weight independent.
HIDDEN_REQUANT_SHIFT = 8

#: Rounding rule for the requantisation shift.
ROUNDING_RULE = "round-half-up (add 1 << (shift-1), then arithmetic right shift)"

#: Saturation rule after requantisation.
SATURATION_RULE = "clamp to [0, 255] (unsigned 8-bit)"

#: Topology.
INPUT_DIM = 784
HIDDEN_DIM = 32
OUTPUT_DIM = 10

#: Declared bias widths (signed, two's complement).
#:
#: Architecture level, not model level: the bias is defined to be allowed to
#: span the full signed range of its layer's dot product, so its width is
#: derived from the topology and the alphabet exactly like every other width
#: here.  A trained model whose bias needs more than this is rejected by
#: IntegerModel.validate() rather than silently wrapped.
#: (Filled in below, once bits_for_signed_range() is defined.)
BIAS_BITS: dict = {}


# --------------------------------------------------------------------------
# Analytical width computation
# --------------------------------------------------------------------------

def bits_for_signed_range(lo: int, hi: int) -> int:
    """Smallest N such that a two's-complement N-bit integer holds [lo, hi]."""
    if lo > hi:
        raise ValueError("empty range")
    n = 1
    while not (-(1 << (n - 1)) <= lo and hi <= (1 << (n - 1)) - 1):
        n += 1
        if n > 512:
            raise OverflowError("range too large")
    return n


def bits_for_unsigned_range(lo: int, hi: int) -> int:
    """Smallest N such that an unsigned N-bit integer holds [lo, hi]."""
    if lo < 0:
        raise ValueError("negative value in unsigned range")
    n = 1
    while hi > (1 << n) - 1:
        n += 1
        if n > 512:
            raise OverflowError("range too large")
    return n


def product_range(act_min: int, act_max: int,
                  alphabet: np.ndarray) -> Tuple[int, int]:
    """Exact min/max of activation * alphabet_level over the whole domain."""
    a = np.array([act_min, act_max], dtype=np.int64)
    w = alphabet.astype(np.int64)
    prods = np.outer(a, w)
    return int(prods.min()), int(prods.max())


def product_width(act_min: int, act_max: int, alphabet: np.ndarray) -> int:
    lo, hi = product_range(act_min, act_max, alphabet)
    return bits_for_signed_range(lo, hi)


def accumulator_range(n_terms: int, act_min: int, act_max: int,
                      alphabet: np.ndarray) -> Tuple[int, int]:
    """Worst-case accumulator range for a dot product of n_terms products."""
    p_lo, p_hi = product_range(act_min, act_max, alphabet)
    return n_terms * p_lo, n_terms * p_hi


def accumulator_width(n_terms: int, act_min: int, act_max: int,
                      alphabet: np.ndarray, bias_bits: int) -> int:
    """Accumulator width covering the dot product *and* the bias addition."""
    lo, hi = accumulator_range(n_terms, act_min, act_max, alphabet)
    b_lo = -(1 << (bias_bits - 1))
    b_hi = (1 << (bias_bits - 1)) - 1
    return bits_for_signed_range(lo + b_lo, hi + b_hi)


def _dot_bits(n_terms: int) -> int:
    lo, hi = accumulator_range(n_terms, ACT_MIN, ACT_MAX, ALPHABET)
    return bits_for_signed_range(lo, hi)


BIAS_BITS.update({
    "layer1": _dot_bits(INPUT_DIM),
    "layer2": _dot_bits(HIDDEN_DIM),
})


@dataclass
class LayerWidths:
    name: str
    n_inputs: int
    n_outputs: int
    act_in_bits: int
    act_in_signed: bool
    act_in_min: int
    act_in_max: int
    weight_index_bits: int
    weight_value_bits: int
    product_min: int
    product_max: int
    product_bits: int
    dot_min: int
    dot_max: int
    dot_bits: int
    bias_bits: int
    accumulator_min: int
    accumulator_max: int
    accumulator_bits: int
    requant_shift: int | None
    output_bits: int
    output_signed: bool
    output_min: int
    output_max: int

    def to_dict(self) -> dict:
        return asdict(self)


def layer1_widths() -> LayerWidths:
    p_lo, p_hi = product_range(ACT_MIN, ACT_MAX, ALPHABET)
    d_lo, d_hi = accumulator_range(INPUT_DIM, ACT_MIN, ACT_MAX, ALPHABET)
    bias_bits = BIAS_BITS["layer1"]
    acc_lo = d_lo - (1 << (bias_bits - 1))
    acc_hi = d_hi + (1 << (bias_bits - 1)) - 1
    return LayerWidths(
        name="layer1",
        n_inputs=INPUT_DIM,
        n_outputs=HIDDEN_DIM,
        act_in_bits=ACT_BITS,
        act_in_signed=ACT_SIGNED,
        act_in_min=ACT_MIN,
        act_in_max=ACT_MAX,
        weight_index_bits=WEIGHT_INDEX_BITS,
        weight_value_bits=WEIGHT_VALUE_BITS,
        product_min=p_lo,
        product_max=p_hi,
        product_bits=bits_for_signed_range(p_lo, p_hi),
        dot_min=d_lo,
        dot_max=d_hi,
        dot_bits=bits_for_signed_range(d_lo, d_hi),
        bias_bits=bias_bits,
        accumulator_min=acc_lo,
        accumulator_max=acc_hi,
        accumulator_bits=bits_for_signed_range(acc_lo, acc_hi),
        requant_shift=HIDDEN_REQUANT_SHIFT,
        output_bits=ACT_BITS,
        output_signed=False,
        output_min=ACT_MIN,
        output_max=ACT_MAX,
    )


def layer2_widths() -> LayerWidths:
    p_lo, p_hi = product_range(ACT_MIN, ACT_MAX, ALPHABET)
    d_lo, d_hi = accumulator_range(HIDDEN_DIM, ACT_MIN, ACT_MAX, ALPHABET)
    bias_bits = BIAS_BITS["layer2"]
    acc_lo = d_lo - (1 << (bias_bits - 1))
    acc_hi = d_hi + (1 << (bias_bits - 1)) - 1
    return LayerWidths(
        name="layer2",
        n_inputs=HIDDEN_DIM,
        n_outputs=OUTPUT_DIM,
        act_in_bits=ACT_BITS,
        act_in_signed=ACT_SIGNED,
        act_in_min=ACT_MIN,
        act_in_max=ACT_MAX,
        weight_index_bits=WEIGHT_INDEX_BITS,
        weight_value_bits=WEIGHT_VALUE_BITS,
        product_min=p_lo,
        product_max=p_hi,
        product_bits=bits_for_signed_range(p_lo, p_hi),
        dot_min=d_lo,
        dot_max=d_hi,
        dot_bits=bits_for_signed_range(d_lo, d_hi),
        bias_bits=bias_bits,
        accumulator_min=acc_lo,
        accumulator_max=acc_hi,
        accumulator_bits=bits_for_signed_range(acc_lo, acc_hi),
        requant_shift=None,
        output_bits=bits_for_signed_range(acc_lo, acc_hi),
        output_signed=True,
        output_min=acc_lo,
        output_max=acc_hi,
    )


def width_report() -> dict:
    """Full arithmetic contract as a JSON-serialisable dict."""
    l1 = layer1_widths()
    l2 = layer2_widths()
    return {
        "K": K,
        "weight_index_bits": WEIGHT_INDEX_BITS,
        "weight_alphabet": [int(v) for v in ALPHABET],
        "weight_alphabet_rule": "alphabet[i] = i - 8  (two's-complement int4)",
        "weight_alphabet_signed": ALPHABET_SIGNED,
        "weight_value_bits": WEIGHT_VALUE_BITS,
        "activation_bits": ACT_BITS,
        "activation_signed": ACT_SIGNED,
        "activation_zero_point": 0,
        "activation_min": ACT_MIN,
        "activation_max": ACT_MAX,
        "hidden_requant_shift": HIDDEN_REQUANT_SHIFT,
        "rounding_rule": ROUNDING_RULE,
        "saturation_rule": SATURATION_RULE,
        "relu_semantics": "hidden = max(accumulator, 0) applied BEFORE the "
                          "requantisation shift, so the shifted value is "
                          "always non-negative",
        "output_rule": "logits = accumulator2 (no requantisation); "
                       "prediction = argmax(logits), lowest index wins ties",
        "tensor_orientation": {
            "layer1_weight_indices": "[in_features=784, out_features=32]",
            "layer2_weight_indices": "[in_features=32, out_features=10]",
            "dot_product": "acc[o] = sum_i act[i] * alphabet[idx[i, o]]",
        },
        "layer1": l1.to_dict(),
        "layer2": l2.to_dict(),
    }


# --------------------------------------------------------------------------
# Multiply-Select-Add operator analysis
# --------------------------------------------------------------------------

def msa_layer_analysis(n_inputs: int, n_outputs: int, k: int = K) -> dict:
    naive = n_inputs * n_outputs
    shared = n_inputs * k
    return {
        "inputs": n_inputs,
        "outputs": n_outputs,
        "K": k,
        "naive_multipliers": naive,
        "shared_product_generators": shared,
        "selectors": n_inputs * n_outputs,
        "selector_fan_in": k,
        "ratio_naive_over_shared": naive / shared,
        "sharing_reduces_product_generators": n_outputs > k,
    }


def msa_report() -> dict:
    l1 = msa_layer_analysis(INPUT_DIM, HIDDEN_DIM)
    l2 = msa_layer_analysis(HIDDEN_DIM, OUTPUT_DIM)
    naive = l1["naive_multipliers"] + l2["naive_multipliers"]
    shared = l1["shared_product_generators"] + l2["shared_product_generators"]
    return {
        "layer1": l1,
        "layer2": l2,
        "total": {
            "naive_multipliers": naive,
            "shared_product_generators": shared,
            "selectors": l1["selectors"] + l2["selectors"],
            "ratio_naive_over_shared": naive / shared,
        },
        "crossover_note": (
            "Product-generator sharing reduces the raw product count only when "
            "a layer's output fanout exceeds K. Layer 1 has fanout 32 > K=16 "
            "so sharing wins; layer 2 has fanout 10 < K=16 so sharing costs "
            "more product generators than the naive form."
        ),
        "synthesis_caveat": (
            "Source-level multiplier counts are not physical multiplier or DSP "
            "counts. Every product here has a constant int4 operand, so "
            "synthesis is free to implement it as shifts, adds and negations. "
            "Synthesised resource and area numbers are reported separately in "
            "later stages."
        ),
    }


def storage_report() -> dict:
    l1 = INPUT_DIM * HIDDEN_DIM
    l2 = HIDDEN_DIM * OUTPUT_DIM
    total = l1 + l2
    bits = total * WEIGHT_INDEX_BITS
    return {
        "layer1_synapses": l1,
        "layer2_synapses": l2,
        "total_synapses": total,
        "index_bits_per_synapse": WEIGHT_INDEX_BITS,
        "total_index_bits": bits,
        "total_index_bytes": bits // 8,
    }
