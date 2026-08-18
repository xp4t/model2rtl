"""Quantisation-aware training of the MNIST MLP under the fixed contract.

The Keras graph simulates the *exact* integer pipeline of
:mod:`model2rtl.contract` using straight-through estimators, so the trained
float latent variables round directly onto the deployed integer parameters.
There is no separate post-training quantisation step and no calibration pass.

TensorFlow is a training-time dependency only.  Nothing in
:mod:`model2rtl.golden`, :mod:`model2rtl.contract` or :mod:`model2rtl.storage`
imports it.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import tensorflow as tf

from . import contract as C
from .golden import IntegerModel

#: Latent-to-integer scaling used only during training.  The deployed weight
#: is round(w_latent * WEIGHT_LATENT_SCALE) clipped to the alphabet, so the
#: latent variable lives in a well-conditioned range for Adam.
WEIGHT_LATENT_SCALE = 8.0
BIAS_LATENT_SCALE = {"layer1": 1024.0, "layer2": 256.0}


def _ste(quantised: tf.Tensor, latent: tf.Tensor) -> tf.Tensor:
    """Forward = quantised value, backward = identity w.r.t. latent."""
    return latent + tf.stop_gradient(quantised - latent)


def quantise_weights(w_latent: tf.Tensor) -> tf.Tensor:
    scaled = w_latent * WEIGHT_LATENT_SCALE
    q = tf.clip_by_value(tf.round(scaled),
                         float(C.ALPHABET.min()), float(C.ALPHABET.max()))
    return _ste(q, scaled)


def quantise_bias(b_latent: tf.Tensor, scale: float, bits: int) -> tf.Tensor:
    scaled = b_latent * scale
    lo = -float(1 << (bits - 1))
    hi = float((1 << (bits - 1)) - 1)
    q = tf.clip_by_value(tf.round(scaled), lo, hi)
    return _ste(q, scaled)


def requantise_relu_u8(acc: tf.Tensor, shift: int) -> tf.Tensor:
    """Differentiable stand-in for golden.requantize_relu_u8."""
    relu = tf.nn.relu(acc)
    scaled = relu / float(1 << shift)
    q = tf.clip_by_value(tf.floor(scaled + 0.5), 0.0, float(C.ACT_MAX))
    return _ste(q, scaled)


class QuantMLP(tf.keras.Model):
    """Flatten(28x28) -> Dense(32) -> ReLU -> Dense(10), all integer-simulated."""

    def __init__(self, hidden_shift: int = C.HIDDEN_REQUANT_SHIFT, seed: int = 1234):
        super().__init__()
        self.hidden_shift = int(hidden_shift)
        init1 = tf.keras.initializers.RandomNormal(stddev=0.19, seed=seed)
        init2 = tf.keras.initializers.RandomNormal(stddev=0.25, seed=seed + 1)
        self.w1 = self.add_weight(shape=(C.INPUT_DIM, C.HIDDEN_DIM),
                                  initializer=init1, name="w1_latent")
        self.b1 = self.add_weight(shape=(C.HIDDEN_DIM,),
                                  initializer="zeros", name="b1_latent")
        self.w2 = self.add_weight(shape=(C.HIDDEN_DIM, C.OUTPUT_DIM),
                                  initializer=init2, name="w2_latent")
        self.b2 = self.add_weight(shape=(C.OUTPUT_DIM,),
                                  initializer="zeros", name="b2_latent")
        # Softmax temperature. Training-only: argmax over the integer logits is
        # invariant under this positive scaling, so it never reaches hardware.
        self.log_temp = self.add_weight(shape=(), initializer=
                                        tf.keras.initializers.Constant(6.0),
                                        name="log_temp")

    def integer_logits(self, x_u8: tf.Tensor) -> tf.Tensor:
        x = tf.cast(x_u8, tf.float32)  # exact: uint8 values are exact in fp32
        w1q = quantise_weights(self.w1)
        b1q = quantise_bias(self.b1, BIAS_LATENT_SCALE["layer1"],
                            C.BIAS_BITS["layer1"])
        acc1 = tf.matmul(x, w1q) + b1q
        h = requantise_relu_u8(acc1, self.hidden_shift)
        w2q = quantise_weights(self.w2)
        b2q = quantise_bias(self.b2, BIAS_LATENT_SCALE["layer2"],
                            C.BIAS_BITS["layer2"])
        return tf.matmul(h, w2q) + b2q

    def call(self, x_u8, training=False):
        logits = self.integer_logits(x_u8)
        return logits / tf.exp(self.log_temp)

    # -- export ----------------------------------------------------------
    def export_integer_model(self) -> IntegerModel:
        w1 = np.clip(np.round(self.w1.numpy() * WEIGHT_LATENT_SCALE),
                     C.ALPHABET.min(), C.ALPHABET.max()).astype(np.int64)
        w2 = np.clip(np.round(self.w2.numpy() * WEIGHT_LATENT_SCALE),
                     C.ALPHABET.min(), C.ALPHABET.max()).astype(np.int64)
        b1 = np.round(self.b1.numpy() * BIAS_LATENT_SCALE["layer1"]).astype(np.int64)
        b2 = np.round(self.b2.numpy() * BIAS_LATENT_SCALE["layer2"]).astype(np.int64)
        model = IntegerModel(
            layer1_weight_indices=(w1 + C.ALPHABET_OFFSET).astype(np.int64),
            layer2_weight_indices=(w2 + C.ALPHABET_OFFSET).astype(np.int64),
            layer1_bias=b1,
            layer2_bias=b2,
        )
        model.validate()
        return model

    def saturation_stats(self) -> dict:
        """How many latent weights are pinned outside the alphabet range."""
        out = {}
        for name, var in (("layer1", self.w1), ("layer2", self.w2)):
            scaled = np.round(var.numpy() * WEIGHT_LATENT_SCALE)
            n_sat = int(((scaled < C.ALPHABET.min()) |
                         (scaled > C.ALPHABET.max())).sum())
            out[name] = {
                "weight_saturation_count": n_sat,
                "weight_saturation_percentage": 100.0 * n_sat / scaled.size,
                "pre_clip_min": int(scaled.min()),
                "pre_clip_max": int(scaled.max()),
            }
        return out


def set_determinism(seed: int) -> None:
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()


def train(data: dict, epochs: int = 30, batch_size: int = 128,
          lr: float = 1e-3, seed: int = 1234,
          hidden_shift: int = C.HIDDEN_REQUANT_SHIFT,
          verbose: int = 2) -> Tuple[QuantMLP, dict]:
    set_determinism(seed)
    model = QuantMLP(hidden_shift=hidden_shift, seed=seed)
    schedule = tf.keras.optimizers.schedules.CosineDecay(lr, epochs *
                                                         (len(data["x_train"]) //
                                                          batch_size))
    model.compile(
        optimizer=tf.keras.optimizers.Adam(schedule),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )
    history = model.fit(
        data["x_train"], data["y_train"],
        validation_data=(data["x_val"], data["y_val"]),
        epochs=epochs, batch_size=batch_size, shuffle=True, verbose=verbose,
    )
    return model, history.history


# --------------------------------------------------------------------------
# Floating-point baseline (reference only; never an RTL oracle)
# --------------------------------------------------------------------------

def train_float(data: dict, epochs: int = 30, batch_size: int = 128,
                lr: float = 1e-3, seed: int = 1234, verbose: int = 2):
    """Plain float32 Flatten/Dense(32)/ReLU/Dense(10) baseline.

    Reported for context only.  Per the project rules, the Keras float model
    is NOT the oracle for RTL verification; the NumPy integer golden model is.
    """
    set_determinism(seed)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(C.INPUT_DIM,)),
        tf.keras.layers.Rescaling(1.0 / 255.0),
        tf.keras.layers.Dense(C.HIDDEN_DIM, activation="relu"),
        tf.keras.layers.Dense(C.OUTPUT_DIM),
    ])
    schedule = tf.keras.optimizers.schedules.CosineDecay(
        lr, epochs * (len(data["x_train"]) // batch_size))
    model.compile(optimizer=tf.keras.optimizers.Adam(schedule),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=["accuracy"])
    hist = model.fit(data["x_train"], data["y_train"],
                     validation_data=(data["x_val"], data["y_val"]),
                     epochs=epochs, batch_size=batch_size, shuffle=True,
                     verbose=verbose)
    return model, hist.history


def evaluate_keras_accuracy(model, x, y, batch: int = 2000) -> float:
    correct = 0
    for s in range(0, len(x), batch):
        p = np.argmax(model.predict(x[s:s + batch], verbose=0), axis=1)
        correct += int((p == y[s:s + batch]).sum())
    return correct / float(len(x))


def qat_integer_logits_numpy(model: QuantMLP, x, batch: int = 2000) -> np.ndarray:
    """Integer logits as computed by the TensorFlow QAT graph."""
    outs = []
    for s in range(0, len(x), batch):
        outs.append(model.integer_logits(tf.constant(x[s:s + batch])).numpy())
    return np.concatenate(outs, axis=0)
