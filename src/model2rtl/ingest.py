"""Read a trained Keras model and extract the parameters model2rtl can compile.

This compiler builds exactly one shape of network:

    input -> Dense(n_hidden) -> ReLU -> Dense(n_out) -> logits -> argmax

Anything else is REJECTED with a description of what was found.  It is never
approximated, silently reshaped, or partially compiled: a compiler that quietly
drops a layer produces hardware that does not implement the model.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


class UnsupportedModel(ValueError):
    """The model is outside what this compiler implements."""


#: Layers that carry no inference-time arithmetic and are skipped.
_TRANSPARENT = {"InputLayer", "Flatten", "Dropout", "Reshape", "Rescaling",
                "SpatialDropout1D", "GaussianNoise"}

#: Activations accepted on the OUTPUT layer.  The fabric emits raw signed
#: logits and predicts with argmax, and argmax is invariant under softmax and
#: under any strictly increasing scalar function, so a monotonic output
#: activation can simply be dropped.  Sigmoid qualifies: thresholding the raw
#: logit at 0 is exactly thresholding sigmoid(logit) at 0.5.
_OK_OUTPUT_ACT = {"linear", "softmax", "sigmoid", None}


@dataclass
class FloatNetwork:
    """A float two-layer dense network, straight out of Keras."""

    w1: np.ndarray                       # (n_in, n_hidden)
    b1: np.ndarray                       # (n_hidden,)
    w2: np.ndarray                       # (n_hidden, n_out)
    b2: np.ndarray                       # (n_out,)
    source: str = ""
    source_sha256: str = ""
    layer_names: List[str] = field(default_factory=list)
    output_activation: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def n_in(self) -> int:
        return int(self.w1.shape[0])

    @property
    def n_hidden(self) -> int:
        return int(self.w1.shape[1])

    @property
    def n_out(self) -> int:
        return int(self.w2.shape[1])

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_sha256": self.source_sha256,
            "topology": "%d -> %d -> ReLU -> %d"
                        % (self.n_in, self.n_hidden, self.n_out),
            "n_in": self.n_in, "n_hidden": self.n_hidden, "n_out": self.n_out,
            "layers_seen": self.layer_names,
            "output_activation": self.output_activation,
            "weight_ranges": {
                "layer1": [float(self.w1.min()), float(self.w1.max())],
                "layer2": [float(self.w2.min()), float(self.w2.max())],
            },
            "bias_ranges": {
                "layer1": [float(self.b1.min()), float(self.b1.max())],
                "layer2": [float(self.b2.min()), float(self.b2.max())],
            },
            "notes": self.notes,
        }


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _activation_name(layer) -> Optional[str]:
    act = getattr(layer, "activation", None)
    if act is None:
        return None
    return getattr(act, "__name__", str(act))


def load_keras(path: str) -> FloatNetwork:
    """Load a .h5 / .keras model and extract the two Dense layers.

    Raises UnsupportedModel with the actual layer list if the graph is not the
    supported shape.
    """
    if not os.path.isfile(path):
        raise UnsupportedModel("model file not found: %s" % path)
    try:
        import tensorflow as tf                                # noqa: F401
    except ImportError as exc:
        raise UnsupportedModel(
            "reading a Keras model needs TensorFlow, which is an optional "
            "dependency of this project. Install it with:\n"
            "    pip install -e \".[train]\"\n"
            "(original error: %s)" % exc)

    from tensorflow import keras
    model = keras.models.load_model(path, compile=False)

    seen, dense, notes = [], [], []
    for layer in model.layers:
        kind = type(layer).__name__
        seen.append("%s(%s)" % (kind, layer.name))
        if kind in _TRANSPARENT:
            if kind == "Rescaling":
                notes.append(
                    "a Rescaling layer was skipped; its scale is NOT folded in. "
                    "Pass --input-scale explicitly if your model expects "
                    "pre-scaled inputs.")
            continue
        if kind in ("Activation", "ReLU"):
            name = _activation_name(layer) if kind == "Activation" else "relu"
            if name not in ("relu", "linear", "softmax"):
                raise UnsupportedModel(
                    "unsupported activation %r in layer %s. This fabric "
                    "implements ReLU on the hidden layer and nothing else."
                    % (name, layer.name))
            continue
        if kind == "Dense":
            dense.append(layer)
            continue
        raise UnsupportedModel(
            "layer %s is a %s, which this compiler does not implement. It "
            "builds a two-layer dense MLP only: no convolution, pooling, "
            "normalisation or recurrence.\nLayers found: %s"
            % (layer.name, kind, ", ".join(seen)))

    if len(dense) != 2:
        raise UnsupportedModel(
            "expected exactly 2 Dense layers, found %d. This compiler builds "
            "input -> Dense -> ReLU -> Dense only.\nLayers found: %s"
            % (len(dense), ", ".join(seen)))

    hidden_layer, out_layer = dense
    hidden_act = _activation_name(hidden_layer)
    if hidden_act not in ("relu", "linear", None):
        raise UnsupportedModel(
            "the hidden Dense layer uses activation %r; the fabric implements "
            "ReLU. Retrain with relu, or split the activation into a separate "
            "ReLU layer." % hidden_act)
    if hidden_act in ("linear", None):
        # a separate ReLU/Activation layer must have supplied it
        if not any(n.startswith(("ReLU", "Activation")) for n in seen):
            raise UnsupportedModel(
                "no ReLU was found between the two Dense layers. The fabric "
                "always applies ReLU there, so compiling this model would "
                "change its arithmetic.\nLayers found: %s" % ", ".join(seen))

    out_act = _activation_name(out_layer)
    if out_act not in _OK_OUTPUT_ACT:
        raise UnsupportedModel(
            "the output Dense layer uses activation %r. Only linear or softmax "
            "are supported, because the fabric emits raw signed logits and "
            "predicts with argmax." % out_act)
    if out_act == "softmax":
        notes.append("output softmax dropped: argmax over logits is identical, "
                     "and the fabric emits raw signed logits.")
    if out_act == "sigmoid":
        notes.append(
            "output sigmoid dropped: it is strictly increasing, so comparing "
            "the raw logit against 0 is exactly comparing sigmoid(logit) "
            "against 0.5. Use the `logits` port, not `prediction`.")

    w1, b1 = [np.asarray(a, dtype=np.float64) for a in hidden_layer.get_weights()[:2]] \
        if len(hidden_layer.get_weights()) >= 2 else (None, None)
    w2, b2 = [np.asarray(a, dtype=np.float64) for a in out_layer.get_weights()[:2]] \
        if len(out_layer.get_weights()) >= 2 else (None, None)
    for name, arr in (("hidden weights", w1), ("hidden bias", b1),
                      ("output weights", w2), ("output bias", b2)):
        if arr is None:
            raise UnsupportedModel(
                "%s missing: a Dense layer without a bias is not supported, "
                "because the fabric always adds one." % name)
    if w1.shape[1] != w2.shape[0]:
        raise UnsupportedModel("hidden width disagrees: %s then %s"
                               % (w1.shape, w2.shape))
    if int(w2.shape[1]) == 1:
        notes.append(
            "SINGLE OUTPUT: the `prediction` port is argmax over one logit and "
            "is therefore always 0. It carries no information for this model. "
            "Read `logits` and threshold it yourself.")

    return FloatNetwork(w1=w1, b1=b1, w2=w2, b2=b2, source=os.path.abspath(path),
                        source_sha256=_sha(path), layer_names=seen,
                        output_activation=out_act, notes=notes)


def load_npz(path: str) -> FloatNetwork:
    """Load float weights from a .npz holding w1, b1, w2, b2.

    A TensorFlow-free path, useful for testing and for models exported from
    somewhere other than Keras.
    """
    with np.load(path) as z:
        missing = [k for k in ("w1", "b1", "w2", "b2") if k not in z]
        if missing:
            raise UnsupportedModel(
                "%s is missing %s. A float .npz must hold w1, b1, w2, b2."
                % (path, ", ".join(missing)))
        w1, b1, w2, b2 = (np.asarray(z[k], dtype=np.float64)
                          for k in ("w1", "b1", "w2", "b2"))
    if w1.ndim != 2 or w2.ndim != 2 or w1.shape[1] != w2.shape[0]:
        raise UnsupportedModel("inconsistent shapes: w1 %s, w2 %s"
                               % (w1.shape, w2.shape))
    return FloatNetwork(w1=w1, b1=b1, w2=w2, b2=b2,
                        source=os.path.abspath(path), source_sha256=_sha(path),
                        layer_names=["npz:w1", "npz:w2"],
                        output_activation="linear")


def load(path: str) -> FloatNetwork:
    """Dispatch on file extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".h5", ".keras", ".hdf5"):
        return load_keras(path)
    if ext == ".npz":
        return load_npz(path)
    raise UnsupportedModel(
        "unrecognised model format %r. Supported: .h5 / .keras (Keras) and "
        ".npz holding w1, b1, w2, b2." % ext)
