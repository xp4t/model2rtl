"""Pure-NumPy integer golden model.

This is the authoritative functional reference for every later stage
(behavioural RTL simulation, gate-level simulation, physical-ROM backend).
It performs no floating-point Dense arithmetic: every operation below is an
exact integer operation that the generated RTL is expected to reproduce
bit for bit.

All intermediate arithmetic is carried in int64, which is strictly wider than
every declared contract width, so Python/NumPy never wraps.  The declared
widths are then *checked* (see check_widths=True), which is how we prove that
the analytically derived accumulator widths are sufficient and that the only
value-changing operations are the explicitly defined saturation points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np

from . import contract as C


class ContractViolation(RuntimeError):
    """Raised when an intermediate value does not fit its declared width."""


def _fits_signed(values: np.ndarray, bits: int) -> bool:
    lo = -(1 << (bits - 1))
    hi = (1 << (bits - 1)) - 1
    return bool(values.min() >= lo and values.max() <= hi)


def alphabet_lookup(indices: np.ndarray) -> np.ndarray:
    """Map 4-bit weight indices to signed alphabet levels."""
    idx = np.asarray(indices)
    if idx.min() < 0 or idx.max() >= C.K:
        raise ContractViolation("weight index outside 0..%d" % (C.K - 1))
    return C.ALPHABET[idx.astype(np.int64)].astype(np.int64)


def requantize_relu_u8(acc: np.ndarray, shift: int = C.HIDDEN_REQUANT_SHIFT
                       ) -> np.ndarray:
    """ReLU, then round-half-up right shift, then saturate to uint8.

    Hardware semantics:
        relu   = acc[msb] ? 0 : acc          (signed compare against 0)
        rnd    = relu + (1 << (shift-1))
        shft   = rnd >> shift                (relu >= 0, so logical == arith)
        out    = shft > 255 ? 255 : shft[7:0]
    """
    relu = np.maximum(acc.astype(np.int64), 0)
    rnd = relu + (1 << (shift - 1))
    shifted = rnd >> shift
    return np.clip(shifted, C.ACT_MIN, C.ACT_MAX).astype(np.int64)


@dataclass
class IntegerModel:
    """Trained model parameters in their integer storage form."""

    layer1_weight_indices: np.ndarray  # uint8 values 0..15, shape (784, 32)
    layer2_weight_indices: np.ndarray  # uint8 values 0..15, shape (32, 10)
    layer1_bias: np.ndarray            # int, shape (32,), accumulator domain
    layer2_bias: np.ndarray            # int, shape (10,), accumulator domain
    stats: Dict[str, int] = field(default_factory=dict)

    # -- validation ------------------------------------------------------
    def validate(self) -> None:
        w1, w2 = self.layer1_weight_indices, self.layer2_weight_indices
        if w1.shape != (C.INPUT_DIM, C.HIDDEN_DIM):
            raise ContractViolation("layer1 shape %s != (784, 32)" % (w1.shape,))
        if w2.shape != (C.HIDDEN_DIM, C.OUTPUT_DIM):
            raise ContractViolation("layer2 shape %s != (32, 10)" % (w2.shape,))
        for name, w in (("layer1", w1), ("layer2", w2)):
            if not np.issubdtype(w.dtype, np.integer):
                raise ContractViolation("%s indices are not integer" % name)
            if w.min() < 0 or w.max() >= C.K:
                raise ContractViolation("%s index outside 0..15" % name)
        if self.layer1_bias.shape != (C.HIDDEN_DIM,):
            raise ContractViolation("layer1 bias shape mismatch")
        if self.layer2_bias.shape != (C.OUTPUT_DIM,):
            raise ContractViolation("layer2 bias shape mismatch")
        for name, b in (("layer1", self.layer1_bias), ("layer2", self.layer2_bias)):
            if not np.issubdtype(b.dtype, np.integer):
                raise ContractViolation("%s bias is not integer" % name)
            if not _fits_signed(b.astype(np.int64), C.BIAS_BITS[name]):
                raise ContractViolation(
                    "%s bias does not fit %d signed bits" % (name, C.BIAS_BITS[name]))

    # -- inference -------------------------------------------------------
    def layer1_accumulate(self, x_u8: np.ndarray) -> np.ndarray:
        w = alphabet_lookup(self.layer1_weight_indices)
        return x_u8.astype(np.int64) @ w + self.layer1_bias.astype(np.int64)

    def layer2_accumulate(self, h_u8: np.ndarray) -> np.ndarray:
        w = alphabet_lookup(self.layer2_weight_indices)
        return h_u8.astype(np.int64) @ w + self.layer2_bias.astype(np.int64)

    def forward(self, x_u8: np.ndarray, check_widths: bool = True,
                collect: dict | None = None) -> np.ndarray:
        """Integer forward pass. Returns signed logits, shape (N, 10)."""
        x = np.asarray(x_u8)
        if x.ndim == 1:
            x = x[None, :]
        if x.shape[1] != C.INPUT_DIM:
            raise ContractViolation("input must have 784 columns")
        if not np.issubdtype(x.dtype, np.integer):
            raise ContractViolation("input activations must be integer")
        if x.min() < C.ACT_MIN or x.max() > C.ACT_MAX:
            raise ContractViolation("input activation outside uint8 range")

        acc1 = self.layer1_accumulate(x)
        if check_widths:
            self._check_layer1(x, acc1)
        h = requantize_relu_u8(acc1)
        acc2 = self.layer2_accumulate(h)
        if check_widths:
            self._check_layer2(h, acc2)

        if collect is not None:
            pre_sat = (np.maximum(acc1, 0) + (1 << (C.HIDDEN_REQUANT_SHIFT - 1))
                       ) >> C.HIDDEN_REQUANT_SHIFT
            collect.setdefault("acc1_min", []).append(int(acc1.min()))
            collect.setdefault("acc1_max", []).append(int(acc1.max()))
            collect.setdefault("hidden_min", []).append(int(h.min()))
            collect.setdefault("hidden_max", []).append(int(h.max()))
            collect.setdefault("hidden_presat_max", []).append(int(pre_sat.max()))
            collect.setdefault("hidden_sat_count", []).append(
                int((pre_sat > C.ACT_MAX).sum()))
            collect.setdefault("hidden_zero_count", []).append(int((h == 0).sum()))
            collect.setdefault("hidden_elems", []).append(int(h.size))
            collect.setdefault("logit_min", []).append(int(acc2.min()))
            collect.setdefault("logit_max", []).append(int(acc2.max()))
        return acc2

    def predict(self, x_u8: np.ndarray, check_widths: bool = True) -> np.ndarray:
        return np.argmax(self.forward(x_u8, check_widths=check_widths), axis=1)

    # -- width checks ----------------------------------------------------
    def _check_layer1(self, x: np.ndarray, acc: np.ndarray) -> None:
        cw = C.layer1_widths()
        w = alphabet_lookup(self.layer1_weight_indices)
        prods = np.array([x.min() * w.min(), x.min() * w.max(),
                          x.max() * w.min(), x.max() * w.max()], dtype=np.int64)
        if not _fits_signed(prods, cw.product_bits):
            raise ContractViolation("layer1 product overflow")
        if not _fits_signed(acc, cw.accumulator_bits):
            raise ContractViolation("layer1 accumulator overflow")

    def _check_layer2(self, h: np.ndarray, acc: np.ndarray) -> None:
        cw = C.layer2_widths()
        w = alphabet_lookup(self.layer2_weight_indices)
        prods = np.array([h.min() * w.min(), h.min() * w.max(),
                          h.max() * w.min(), h.max() * w.max()], dtype=np.int64)
        if not _fits_signed(prods, cw.product_bits):
            raise ContractViolation("layer2 product overflow")
        if not _fits_signed(acc, cw.accumulator_bits):
            raise ContractViolation("layer2 accumulator overflow")


def accuracy(model: IntegerModel, x_u8: np.ndarray, labels: np.ndarray,
             batch: int = 2000, collect: dict | None = None) -> float:
    correct = 0
    for start in range(0, x_u8.shape[0], batch):
        xb = x_u8[start:start + batch]
        logits = model.forward(xb, collect=collect)
        correct += int((np.argmax(logits, axis=1) == labels[start:start + batch]).sum())
    return correct / float(x_u8.shape[0])
