"""Post-training quantization of a float two-layer MLP onto the fixed contract.

The contract this project implements has NO multiplicative requantisation
scale.  Weights are one of K fixed integer levels (-K/2 .. K/2-1), activations
are unsigned integers, and the only requantisation operator is a power-of-two
shift.  Quantisation therefore has to express the float network in that form:

    float:    a1 = x_f . W1 + B1                 (x_f = x_u8 * input_scale)
    integer:  acc1 = x_u8 . A1 + b1              (A1 integer levels)

Choose a per-layer scale s1 and set A1 = clip(round(W1 * input_scale / s1)),
b1 = round(B1 / s1).  Then acc1 ~= a1 / s1, so the integer accumulator is the
float pre-activation in units of s1.

    h = clamp((relu(acc1) + 2^(shift-1)) >> shift, 0, 2^act_bits - 1)

so h ~= relu(a1) / (s1 * 2^shift).  Layer 2 repeats the construction with
s2, and the layer-2 bias absorbs the accumulated scale:

    b2 = round(B2 / (s1 * 2^shift * s2))

The logits come out in units of (s1 * 2^shift * s2), and argmax is invariant
under that positive factor, so nothing further is needed.

Two knobs are chosen by MEASUREMENT on calibration data, not by assumption:
the requantisation shift, and the input scale.  Both are reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import contract as C
from .genmodel import GeneralIntegerModel, ModelSpecError
from .ingest import FloatNetwork

#: Candidate requantisation shifts.  The Stage-0 MNIST model chose 8 by an
#: identical sweep; nothing here assumes that value.
DEFAULT_SHIFTS: Tuple[int, ...] = (4, 5, 6, 7, 8, 9, 10, 11, 12)

#: Candidate input scales.  A Keras MNIST model is usually trained on x/255,
#: but plenty are trained on raw uint8.  Both are tried and the better one is
#: kept, so a wrong guess cannot pass silently.
DEFAULT_INPUT_SCALES: Tuple[float, ...] = (1.0 / 255.0, 1.0)


class QuantizationError(ValueError):
    pass


@dataclass
class QuantResult:
    model: GeneralIntegerModel
    input_scale: float
    requant_shift: int
    layer1_scale: float
    layer2_scale: float
    calibration_accuracy: Optional[float]
    float_accuracy: Optional[float]
    search: List[dict] = field(default_factory=list)
    clipping: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": "post-training quantization",
            "input_scale": self.input_scale,
            "requant_shift": self.requant_shift,
            "layer1_weight_scale": self.layer1_scale,
            "layer2_weight_scale": self.layer2_scale,
            "float_accuracy_on_calibration": self.float_accuracy,
            "integer_accuracy_on_calibration": self.calibration_accuracy,
            "accuracy_change_points": (
                None if (self.float_accuracy is None
                         or self.calibration_accuracy is None)
                else round(100.0 * (self.calibration_accuracy
                                    - self.float_accuracy), 4)),
            "weight_clipping_percent": self.clipping,
            "search": self.search,
            "notes": self.notes,
            "scale_note":
                "These scales are a QUANTISATION artefact, not hardware. The "
                "emitted RTL contains no multiplicative scale: it stores only "
                "weight indices and integer biases, and requantises with a "
                "power-of-two shift.",
        }


def _quantize_tensor(w: np.ndarray, k: int) -> Tuple[np.ndarray, float, float]:
    """Per-tensor quantisation onto the levels -k/2 .. k/2-1.

    The alphabet is ASYMMETRIC (-8 .. +7 for K = 16), so scaling by
    max|w| / 7 would waste the extra negative level and needlessly squash
    every weight. Scale against whichever side actually binds.
    """
    lo, hi = -(k // 2), k // 2 - 1        # -8, +7 for K = 16
    w_max, w_min = float(np.max(w)), float(np.min(w))
    scale = max(w_max / hi if w_max > 0 else 0.0,
                w_min / lo if w_min < 0 else 0.0)
    if scale == 0.0:                       # all-zero tensor
        return np.zeros(w.shape, dtype=np.int64), 1.0, 0.0
    levels = np.round(w / scale)
    clipped = float(np.mean((levels < lo) | (levels > hi)) * 100.0)
    levels = np.clip(levels, lo, hi).astype(np.int64)
    return levels, scale, clipped


def _accuracy(pred: np.ndarray, y: np.ndarray) -> float:
    return float((np.asarray(pred) == np.asarray(y)).mean())


def quantize_ptq(net: FloatNetwork,
                 x_calib: Optional[np.ndarray] = None,
                 y_calib: Optional[np.ndarray] = None,
                 k: int = C.K, act_bits: int = C.ACT_BITS,
                 shifts: Sequence[int] = DEFAULT_SHIFTS,
                 input_scales: Optional[Sequence[float]] = None,
                 module_name: str = "mlp_fabric") -> QuantResult:
    """Quantize a float network, choosing the shift and input scale by search.

    Without calibration data the search cannot be scored, so the middle shift
    is used and the result is reported as UNMEASURED rather than presented as
    if it had been validated.
    """
    if input_scales is None:
        input_scales = DEFAULT_INPUT_SCALES
    hi_act = (1 << act_bits) - 1

    a2, s2, clip2 = _quantize_tensor(net.w2, k)

    best, search = None, []
    for in_scale in input_scales:
        a1, s1, clip1 = _quantize_tensor(net.w1 * in_scale, k)
        b1 = np.round(net.b1 / s1).astype(np.int64)
        for shift in shifts:
            b2 = np.round(net.b2 / (s1 * (1 << shift) * s2)).astype(np.int64)
            try:
                model = GeneralIntegerModel.from_arrays(
                    a1 + k // 2, a2 + k // 2, b1, b2, k=k, act_bits=act_bits,
                    requant_shift=shift, module_name=module_name)
            except ModelSpecError as exc:
                search.append({"input_scale": in_scale, "shift": shift,
                               "rejected": str(exc)[:160]})
                continue

            entry = {"input_scale": in_scale, "shift": shift}
            if x_calib is not None:
                h = model.hidden(x_calib)
                entry["hidden_saturation_percent"] = round(
                    100.0 * float((h >= hi_act).mean()), 4)
                entry["hidden_zero_percent"] = round(
                    100.0 * float((h == 0).mean()), 4)
                if y_calib is not None:
                    entry["accuracy"] = _accuracy(
                        model.predict(x_calib, check_widths=False), y_calib)
            search.append(entry)

            if best is None:
                best = (entry, model, in_scale, shift, s1, s2, clip1)
            elif "accuracy" in entry:
                if entry["accuracy"] > best[0].get("accuracy", -1):
                    best = (entry, model, in_scale, shift, s1, s2, clip1)
            elif shift == shifts[len(shifts) // 2] and "accuracy" not in best[0]:
                best = (entry, model, in_scale, shift, s1, s2, clip1)

    if best is None:
        raise QuantizationError(
            "no (input scale, shift) combination produced a model that fits the "
            "declared bias widths. The float biases are too large relative to "
            "the weight scale for this contract; rescale the network before "
            "compiling. Attempts: %s" % search[:6])

    entry, model, in_scale, shift, s1, s2, clip1 = best
    notes = list(net.notes)
    if y_calib is None:
        notes.append(
            "NO LABELLED CALIBRATION DATA: the requantisation shift and input "
            "scale were not chosen by measured accuracy. Supply --calibration "
            "with labels to make this an evidence-based choice.")
    if len(set(s.get("input_scale") for s in search if "accuracy" in s)) > 1:
        accs = {s["input_scale"]: s["accuracy"] for s in search
                if "accuracy" in s}
        notes.append("input scale chosen by measurement: %s"
                     % {("1/255" if abs(v - 1 / 255) < 1e-9 else str(v)):
                        round(max(a for s, a in
                                  [(e["input_scale"], e["accuracy"])
                                   for e in search if "accuracy" in e]
                                  if abs(s - v) < 1e-12), 4)
                        for v in sorted(set(accs))})

    float_acc = None
    if x_calib is not None and y_calib is not None:
        float_acc = _accuracy(float_predict(net, x_calib, in_scale), y_calib)

    return QuantResult(
        model=model, input_scale=in_scale, requant_shift=shift,
        layer1_scale=s1, layer2_scale=s2,
        calibration_accuracy=entry.get("accuracy"), float_accuracy=float_acc,
        search=search,
        clipping={"layer1_percent": round(clip1, 4),
                  "layer2_percent": round(clip2, 4)},
        notes=notes)


def float_predict(net: FloatNetwork, x_u8: np.ndarray,
                  input_scale: float) -> np.ndarray:
    """The float network's own prediction, for an honest comparison."""
    x = np.asarray(x_u8, dtype=np.float64) * input_scale
    h = np.maximum(x @ net.w1 + net.b1, 0.0)
    return np.argmax(h @ net.w2 + net.b2, axis=1)
