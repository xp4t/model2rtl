"""Topology-general integer reference model.

:mod:`model2rtl.golden` is the frozen Stage-0 oracle.  It is pinned to the
demonstrated 784-32-10 MNIST network by design and must not be edited: every
verified result from Stage 1 onward was measured against it, and its SHA-256 is
recorded in four stage reports.

This module implements the SAME arithmetic for an arbitrary two-layer dense
network, parameterised by :class:`model2rtl.fabric.FabricConfig`.  It does not
replace the oracle; it generalises it, and
:func:`assert_matches_frozen_oracle` proves the two agree bit for bit on the
frozen model.  The test suite runs that proof, so the general path can never
drift from the verified one.

Supported topology: input -> Dense(n_hidden) -> ReLU + requantise -> Dense(n_out)
-> signed logits -> argmax.  Anything else is rejected, not approximated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from . import contract as C
from .fabric import FabricConfig, derive_widths


class ModelSpecError(ValueError):
    """The parameters do not describe a network this compiler can build."""


def alphabet_for(k: int) -> np.ndarray:
    """alphabet[i] = i - k/2, the two's-complement level set for a k-level code."""
    if k < 2 or (k & (k - 1)):
        raise ModelSpecError("K must be a power of two >= 2, got %r" % k)
    return np.arange(k, dtype=np.int64) - (k // 2)


def alphabet_lookup(indices: np.ndarray, k: int = C.K) -> np.ndarray:
    idx = np.asarray(indices)
    if idx.min() < 0 or idx.max() >= k:
        raise ModelSpecError("weight index outside 0..%d" % (k - 1))
    return alphabet_for(k)[idx.astype(np.int64)].astype(np.int64)


def requantize_relu(acc: np.ndarray, shift: int, act_bits: int) -> np.ndarray:
    """ReLU, round-half-up right shift, saturate to the activation range.

    Identical hardware semantics to model2rtl.golden.requantize_relu_u8:
        relu = acc < 0 ? 0 : acc
        out  = clamp((relu + (1 << (shift-1))) >> shift, 0, 2**act_bits - 1)
    """
    if shift < 1:
        raise ModelSpecError("requantisation shift must be >= 1, got %d" % shift)
    relu = np.maximum(np.asarray(acc, dtype=np.int64), 0)
    shifted = (relu + (1 << (shift - 1))) >> shift
    return np.clip(shifted, 0, (1 << act_bits) - 1).astype(np.int64)


@dataclass
class GeneralIntegerModel:
    """A quantized two-layer dense network in its integer storage form."""

    layer1_weight_indices: np.ndarray      # (n_in, n_hidden), values 0..K-1
    layer2_weight_indices: np.ndarray      # (n_hidden, n_out)
    layer1_bias: np.ndarray                # (n_hidden,), accumulator domain
    layer2_bias: np.ndarray                # (n_out,), accumulator domain
    cfg: FabricConfig = field(default_factory=FabricConfig)
    provenance: Dict[str, object] = field(default_factory=dict)

    # -- construction ----------------------------------------------------
    @classmethod
    def from_arrays(cls, w1_idx, w2_idx, b1, b2, k: int = C.K,
                    act_bits: int = C.ACT_BITS, requant_shift: int = 8,
                    module_name: str = "mlp_fabric",
                    provenance: Optional[dict] = None
                    ) -> "GeneralIntegerModel":
        """Infer the topology from the arrays instead of assuming it."""
        w1 = np.asarray(w1_idx)
        w2 = np.asarray(w2_idx)
        if w1.ndim != 2 or w2.ndim != 2:
            raise ModelSpecError("weight index arrays must be 2-D")
        cfg = FabricConfig(n_in=int(w1.shape[0]), n_hidden=int(w1.shape[1]),
                           n_out=int(w2.shape[1]), k=k, act_bits=act_bits,
                           requant_shift=requant_shift,
                           module_name=module_name)
        m = cls(layer1_weight_indices=w1.astype(np.int64),
                layer2_weight_indices=w2.astype(np.int64),
                layer1_bias=np.asarray(b1).astype(np.int64),
                layer2_bias=np.asarray(b2).astype(np.int64),
                cfg=cfg, provenance=dict(provenance or {}))
        m.validate()
        return m

    # -- validation ------------------------------------------------------
    def validate(self) -> None:
        cfg = self.cfg
        w1, w2 = self.layer1_weight_indices, self.layer2_weight_indices
        if w1.shape != (cfg.n_in, cfg.n_hidden):
            raise ModelSpecError("layer1 shape %s does not match the topology "
                                 "(%d, %d)" % (w1.shape, cfg.n_in, cfg.n_hidden))
        if w2.shape != (cfg.n_hidden, cfg.n_out):
            raise ModelSpecError("layer2 shape %s does not match the topology "
                                 "(%d, %d); the hidden width must agree with "
                                 "layer 1" % (w2.shape, cfg.n_hidden, cfg.n_out))
        for name, w in (("layer1", w1), ("layer2", w2)):
            if not np.issubdtype(w.dtype, np.integer):
                raise ModelSpecError("%s indices are not integer" % name)
            if w.min() < 0 or w.max() >= cfg.k:
                raise ModelSpecError("%s index outside 0..%d"
                                     % (name, cfg.k - 1))
        if self.layer1_bias.shape != (cfg.n_hidden,):
            raise ModelSpecError("layer1 bias shape %s != (%d,)"
                                 % (self.layer1_bias.shape, cfg.n_hidden))
        if self.layer2_bias.shape != (cfg.n_out,):
            raise ModelSpecError("layer2 bias shape %s != (%d,)"
                                 % (self.layer2_bias.shape, cfg.n_out))
        w = derive_widths(cfg)
        for name, b, bits in (("layer1", self.layer1_bias,
                               w["layer1_bias_bits"]),
                              ("layer2", self.layer2_bias,
                               w["layer2_bias_bits"])):
            if not np.issubdtype(np.asarray(b).dtype, np.integer):
                raise ModelSpecError("%s bias is not integer" % name)
            lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            if b.size and (b.min() < lo or b.max() > hi):
                raise ModelSpecError(
                    "%s bias does not fit %d signed bits (range %d..%d, needs "
                    "%d..%d). Rescale the layer before quantising."
                    % (name, bits, lo, hi, int(b.min()), int(b.max())))

    # -- inference -------------------------------------------------------
    def layer1_accumulate(self, x: np.ndarray) -> np.ndarray:
        w = alphabet_lookup(self.layer1_weight_indices, self.cfg.k)
        return np.asarray(x, dtype=np.int64) @ w \
            + self.layer1_bias.astype(np.int64)

    def layer2_accumulate(self, h: np.ndarray) -> np.ndarray:
        w = alphabet_lookup(self.layer2_weight_indices, self.cfg.k)
        return np.asarray(h, dtype=np.int64) @ w \
            + self.layer2_bias.astype(np.int64)

    def hidden(self, x: np.ndarray) -> np.ndarray:
        return requantize_relu(self.layer1_accumulate(x),
                               self.cfg.requant_shift, self.cfg.act_bits)

    def forward(self, x: np.ndarray, check_widths: bool = True) -> np.ndarray:
        cfg = self.cfg
        xa = np.asarray(x)
        if xa.ndim == 1:
            xa = xa[None, :]
        if xa.shape[1] != cfg.n_in:
            raise ModelSpecError("input must have %d columns, got %d"
                                 % (cfg.n_in, xa.shape[1]))
        if not np.issubdtype(xa.dtype, np.integer):
            raise ModelSpecError("input activations must be integer")
        hi = (1 << cfg.act_bits) - 1
        if xa.min() < 0 or xa.max() > hi:
            raise ModelSpecError("input activation outside 0..%d" % hi)

        acc1 = self.layer1_accumulate(xa)
        h = requantize_relu(acc1, cfg.requant_shift, cfg.act_bits)
        acc2 = self.layer2_accumulate(h)
        if check_widths:
            self._check_widths(acc1, acc2)
        return acc2

    def predict(self, x: np.ndarray, check_widths: bool = True) -> np.ndarray:
        return np.argmax(self.forward(x, check_widths=check_widths), axis=1)

    def _check_widths(self, acc1: np.ndarray, acc2: np.ndarray) -> None:
        w = derive_widths(self.cfg)
        for name, acc, bits in (("layer1", acc1, w["layer1_acc_bits"]),
                                ("layer2", acc2, w["layer2_acc_bits"])):
            lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            if acc.min() < lo or acc.max() > hi:
                raise ModelSpecError(
                    "%s accumulator overflowed its declared %d bits "
                    "(observed %d..%d, representable %d..%d)"
                    % (name, bits, int(acc.min()), int(acc.max()), lo, hi))

    # -- reporting -------------------------------------------------------
    def to_dict(self) -> dict:
        from dataclasses import asdict
        w = derive_widths(self.cfg)
        return {
            "topology": "%d -> %d -> ReLU -> %d"
                        % (self.cfg.n_in, self.cfg.n_hidden, self.cfg.n_out),
            "config": asdict(self.cfg),
            "widths": w,
            "synapses": {
                "layer1": int(self.layer1_weight_indices.size),
                "layer2": int(self.layer2_weight_indices.size),
                "total": int(self.layer1_weight_indices.size
                             + self.layer2_weight_indices.size),
            },
            "weight_index_histogram": {
                "layer1": np.bincount(self.layer1_weight_indices.ravel(),
                                      minlength=self.cfg.k).tolist(),
                "layer2": np.bincount(self.layer2_weight_indices.ravel(),
                                      minlength=self.cfg.k).tolist(),
            },
            "bias_range": {
                "layer1": [int(self.layer1_bias.min()),
                           int(self.layer1_bias.max())],
                "layer2": [int(self.layer2_bias.min()),
                           int(self.layer2_bias.max())],
            },
            "provenance": self.provenance,
        }


# --------------------------------------------------------------------------
# Equivalence with the frozen oracle
# --------------------------------------------------------------------------

def from_frozen(model, module_name: str = "mnist_mlp_fabric"
                ) -> "GeneralIntegerModel":
    """Wrap a frozen model2rtl.golden.IntegerModel without changing anything."""
    return GeneralIntegerModel.from_arrays(
        model.layer1_weight_indices, model.layer2_weight_indices,
        model.layer1_bias, model.layer2_bias,
        k=C.K, act_bits=C.ACT_BITS, requant_shift=C.HIDDEN_REQUANT_SHIFT,
        module_name=module_name,
        provenance={"source": "frozen model2rtl.golden.IntegerModel"})


def assert_matches_frozen_oracle(model, x: np.ndarray) -> dict:
    """Prove this module reproduces the frozen Stage-0 oracle exactly.

    Compares hidden activations, logits and predictions element by element.
    Raises on the first disagreement; the test suite runs this so the general
    path cannot silently diverge from the verified one.
    """
    from .golden import alphabet_lookup as frozen_lookup
    from .golden import requantize_relu_u8

    gen = from_frozen(model)
    xa = np.asarray(x, dtype=np.int64)

    frozen_acc1 = xa @ frozen_lookup(model.layer1_weight_indices) \
        + model.layer1_bias.astype(np.int64)
    frozen_hidden = requantize_relu_u8(frozen_acc1)
    frozen_logits = model.forward(xa)
    frozen_pred = np.argmax(frozen_logits, axis=1)

    gen_hidden = gen.hidden(xa)
    gen_logits = gen.forward(xa)
    gen_pred = gen.predict(xa)

    diffs = {
        "hidden_mismatches": int((gen_hidden != frozen_hidden).sum()),
        "logit_mismatches": int((gen_logits != frozen_logits).sum()),
        "prediction_mismatches": int((gen_pred != frozen_pred).sum()),
        "hidden_compared": int(frozen_hidden.size),
        "logits_compared": int(frozen_logits.size),
        "predictions_compared": int(frozen_pred.size),
    }
    bad = sum(diffs[k] for k in ("hidden_mismatches", "logit_mismatches",
                                 "prediction_mismatches"))
    if bad:
        raise ModelSpecError(
            "the general integer model does not reproduce the frozen oracle: %s"
            % diffs)
    return diffs
