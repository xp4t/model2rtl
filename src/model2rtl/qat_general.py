"""Quantization-aware fine-tuning for an arbitrary two-layer dense network.

model2rtl.qat is the frozen Stage-0 trainer, pinned to 784-32-10 and used to
produce the verified MNIST model.  This module implements the same
straight-through-estimator scheme for any topology, and starts from an already
trained float network rather than from scratch.

Why it exists: 4-bit weights are aggressive.  Post-training quantization gives
you a working design immediately but pays for it in accuracy, because the float
weights were never trained to survive a 16-level alphabet.  Fine-tuning with
the exact integer pipeline in the forward pass lets the weights move to places
that quantize well, which is how the reference MNIST model kept 96.45% against
a 96.52% float baseline.

TensorFlow is imported lazily: it is a training-time dependency only, and the
compiler, the integer model and the RTL emitters never need it.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from . import contract as C
from .genmodel import GeneralIntegerModel
from .ingest import FloatNetwork
from .quantize import (DEFAULT_SHIFTS, QuantResult, _accuracy, float_predict,
                       quantize_ptq)


def _require_tf():
    try:
        import tensorflow as tf
    except ImportError as exc:                                # pragma: no cover
        raise SystemExit(
            "quantization-aware training needs TensorFlow, which is an "
            "optional dependency:\n    pip install -e \".[train]\"\n"
            "(original error: %s)" % exc)
    return tf


def qat_finetune(net: FloatNetwork, x: np.ndarray, y: np.ndarray,
                 epochs: int = 20, batch_size: int = 128,
                 input_scale: Optional[float] = None,
                 shift: Optional[int] = None,
                 shifts: Sequence[int] = DEFAULT_SHIFTS,
                 val_split: float = 0.1, seed: int = 1234,
                 module_name: str = "mlp_fabric",
                 learning_rate: float = 2e-3) -> QuantResult:
    """Fine-tune `net` so it survives 4-bit quantization, then export.

    The scale and shift are established first by the PTQ search, so the
    starting point is the best purely post-training answer and any improvement
    is attributable to the fine-tuning.  The returned QuantResult reports both.
    """
    tf = _require_tf()

    # 1. PTQ first: it fixes the input scale and the shift by measurement, and
    #    gives an honest baseline for what fine-tuning is worth.
    kw = {}
    if input_scale is not None:
        kw["input_scales"] = (input_scale,)
    if shift is not None:
        kw["shifts"] = (shift,)
    else:
        kw["shifts"] = shifts
    base = quantize_ptq(net, x, y, module_name=module_name, **kw)
    cfg = base.model.cfg
    s1, s2, in_scale, sh = (base.layer1_scale, base.layer2_scale,
                            base.input_scale, base.requant_shift)

    lo, hi = -(cfg.k // 2), cfg.k // 2 - 1
    act_max = float((1 << cfg.act_bits) - 1)

    tf.keras.utils.set_random_seed(seed)

    def ste(q, latent):
        return latent + tf.stop_gradient(q - latent)

    def q_w(w_latent):
        q = tf.clip_by_value(tf.round(w_latent), float(lo), float(hi))
        return ste(q, w_latent)

    def q_b(b_latent, bits):
        blo = -float(1 << (bits - 1))
        bhi = float((1 << (bits - 1)) - 1)
        return ste(tf.clip_by_value(tf.round(b_latent), blo, bhi), b_latent)

    from .fabric import derive_widths
    w = derive_widths(cfg)

    class QuantMLPGeneral(tf.keras.Model):
        """Latent variables live in the INTEGER domain: a latent weight of 3.4
        quantizes to 3. That keeps the straight-through estimator simple and
        makes the export a plain round-and-clip."""

        def __init__(self):
            super().__init__()
            self.w1 = self.add_weight(shape=(cfg.n_in, cfg.n_hidden),
                                      initializer="zeros", name="w1")
            self.b1 = self.add_weight(shape=(cfg.n_hidden,),
                                      initializer="zeros", name="b1")
            self.w2 = self.add_weight(shape=(cfg.n_hidden, cfg.n_out),
                                      initializer="zeros", name="w2")
            self.b2 = self.add_weight(shape=(cfg.n_out,),
                                      initializer="zeros", name="b2")
            self.log_temp = self.add_weight(
                shape=(), name="log_temp",
                initializer=tf.keras.initializers.Constant(6.0))

        def integer_logits(self, x_u8):
            xf = tf.cast(x_u8, tf.float32)
            acc1 = tf.matmul(xf, q_w(self.w1)) \
                + q_b(self.b1, w["layer1_bias_bits"])
            relu = tf.nn.relu(acc1)
            scaled = relu / float(1 << sh)
            h = ste(tf.clip_by_value(tf.floor(scaled + 0.5), 0.0, act_max),
                    scaled)
            return tf.matmul(h, q_w(self.w2)) \
                + q_b(self.b2, w["layer2_bias_bits"])

        def call(self, x_u8, training=False):
            return self.integer_logits(x_u8) / tf.exp(self.log_temp)

    model = QuantMLPGeneral()
    model.build((None, cfg.n_in))
    # start from the PTQ solution, expressed in the integer latent domain
    model.w1.assign((net.w1 * in_scale / s1).astype(np.float32))
    model.b1.assign((net.b1 / s1).astype(np.float32))
    model.w2.assign((net.w2 / s2).astype(np.float32))
    model.b2.assign((net.b2 / (s1 * (1 << sh) * s2)).astype(np.float32))

    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(
                      from_logits=True),
                  metrics=["accuracy"])
    hist = model.fit(x.astype(np.float32), y.astype(np.int64),
                     epochs=epochs, batch_size=batch_size,
                     validation_split=val_split, verbose=0)

    a1 = np.clip(np.round(model.w1.numpy()), lo, hi).astype(np.int64)
    a2 = np.clip(np.round(model.w2.numpy()), lo, hi).astype(np.int64)
    b1 = np.round(model.b1.numpy()).astype(np.int64)
    b2 = np.round(model.b2.numpy()).astype(np.int64)
    tuned = GeneralIntegerModel.from_arrays(
        a1 + cfg.k // 2, a2 + cfg.k // 2, b1, b2, k=cfg.k,
        act_bits=cfg.act_bits, requant_shift=sh, module_name=module_name,
        provenance={"quantization": "quantization-aware fine-tuning",
                    "epochs": int(epochs), "seed": int(seed)})

    acc_qat = _accuracy(tuned.predict(x, check_widths=False), y)
    acc_ptq = base.calibration_accuracy
    keep_qat = acc_ptq is None or acc_qat >= acc_ptq
    chosen = tuned if keep_qat else base.model

    notes = list(base.notes)
    notes.append(
        "QAT fine-tune: %d epochs, PTQ %.4f -> QAT %.4f on the supplied data; "
        "kept the %s model."
        % (epochs, acc_ptq if acc_ptq is not None else float("nan"), acc_qat,
           "fine-tuned" if keep_qat else "PTQ (fine-tuning did not help)"))
    notes.append(
        "Accuracy above is measured on the data you passed. If that is also "
        "the training data it is an OPTIMISTIC estimate; evaluate on a held-out "
        "set for a number you can quote.")

    return QuantResult(
        model=chosen, input_scale=in_scale, requant_shift=sh,
        layer1_scale=s1, layer2_scale=s2,
        calibration_accuracy=max(acc_qat, acc_ptq) if acc_ptq is not None
        else acc_qat,
        float_accuracy=base.float_accuracy,
        search=base.search + [{"method": "qat", "epochs": int(epochs),
                               "accuracy": acc_qat,
                               "final_train_accuracy": float(
                                   hist.history["accuracy"][-1]),
                               "final_val_accuracy": float(
                                   hist.history.get("val_accuracy",
                                                    [float("nan")])[-1])}],
        clipping=base.clipping, notes=notes)
