"""Read-only inspection helpers for legacy Keras HDF5 models.

This module deliberately does not import TensorFlow or Keras.  It reads the
serialized graph and stored tensor metadata directly, which keeps slash-name
legacy models inspectable before any executable loader is involved.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple


class LegacyH5Error(ValueError):
    """Raised when an HDF5 model cannot be safely inspected or verified."""


Shape = Tuple[Optional[int], ...]


def sha256_file(path: str) -> str:
    """Return the SHA-256 digest of *path* without loading it into memory."""
    digest = sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_hash(path: str, expected_sha256: str) -> str:
    """Verify a source file before a caller passes it to a model loader."""
    actual = sha256_file(path)
    if actual.lower() != expected_sha256.lower():
        raise LegacyH5Error(
            "source SHA-256 mismatch for %s: expected %s, got %s"
            % (path, expected_sha256, actual)
        )
    return actual


@dataclass(frozen=True)
class LayerRecord:
    """A serialized Keras layer, including nested Functional children."""

    index: int
    path: Tuple[str, ...]
    name: str
    class_name: str
    input_shape: Optional[Shape]
    output_shape: Optional[Shape]
    activation: Optional[str]
    dropout_rate: Optional[float]
    parameter_count: int
    trainable: bool
    inference_behavior: str
    partition: str
    children: Tuple["LayerRecord", ...] = ()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "path": list(self.path),
            "name": self.name,
            "class_name": self.class_name,
            "input_shape": _shape_to_list(self.input_shape),
            "output_shape": _shape_to_list(self.output_shape),
            "activation": self.activation,
            "dropout_rate": self.dropout_rate,
            "parameter_count": self.parameter_count,
            "trainable": self.trainable,
            "inference_behavior": self.inference_behavior,
            "partition": self.partition,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True)
class DenseLayerRecord:
    """Stored Dense tensor metadata, derived from HDF5 datasets."""

    name: str
    path: Tuple[str, ...]
    in_features: int
    out_features: int
    activation: str
    kernel_shape: Tuple[int, int]
    bias_shape: Optional[Tuple[int, ...]]
    parameter_count: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": list(self.path),
            "in_features": self.in_features,
            "out_features": self.out_features,
            "activation": self.activation,
            "kernel_shape": list(self.kernel_shape),
            "bias_shape": list(self.bias_shape) if self.bias_shape else None,
            "parameter_count": self.parameter_count,
        }


@dataclass(frozen=True)
class DenseSuffixBoundary:
    """The GAP output where the unsupported software prefix ends."""

    layer_name: str
    feature_width: int
    unsupported_prefix: Tuple[str, ...]
    dense_suffix: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "layer_name": self.layer_name,
            "feature_width": self.feature_width,
            "unsupported_prefix": list(self.unsupported_prefix),
            "dense_suffix": list(self.dense_suffix),
        }


@dataclass(frozen=True)
class LegacyModelAnalysis:
    """Read-only graph, tensor, and hybrid-partition summary."""

    source_path: str
    source_sha256: str
    keras_version: Optional[str]
    input_shape: Optional[Shape]
    layers: Tuple[LayerRecord, ...]
    dense_layers: Tuple[DenseLayerRecord, ...]
    dropout_rates: Tuple[float, ...]
    boundary: DenseSuffixBoundary
    execution_mode: str = "hybrid"
    full_cnn_in_rtl: bool = False

    @property
    def output_shape(self) -> Optional[Shape]:
        if not self.dense_layers:
            return None
        return (None, self.dense_layers[-1].out_features)

    @property
    def final_activation(self) -> Optional[str]:
        return self.dense_layers[-1].activation if self.dense_layers else None

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "keras_version": self.keras_version,
            "input_shape": _shape_to_list(self.input_shape),
            "output_shape": _shape_to_list(self.output_shape),
            "layers": [layer.to_dict() for layer in self.layers],
            "dense_layers": [layer.to_dict() for layer in self.dense_layers],
            "dropout_rates": list(self.dropout_rates),
            "final_activation": self.final_activation,
            "boundary": self.boundary.to_dict(),
            "execution_mode": self.execution_mode,
            "full_cnn_in_rtl": self.full_cnn_in_rtl,
        }


def analyze_h5(path: str) -> LegacyModelAnalysis:
    """Parse a legacy Keras H5 graph and tensors without executing a model."""
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - packaging failure
        raise LegacyH5Error("h5py is required to inspect legacy H5 models") from exc

    source = Path(path)
    if not source.is_file():
        raise LegacyH5Error("model file does not exist: %s" % path)
    source_hash = sha256_file(str(source))
    try:
        with h5py.File(source, "r") as handle:
            config = _read_model_config(handle)
            dataset_shapes = _dataset_shapes(handle)
            root_config = config.get("config")
            if not isinstance(root_config, dict):
                raise LegacyH5Error("model_config has no object config")
            raw_layers = root_config.get("layers")
            if not isinstance(raw_layers, list):
                raise LegacyH5Error("model_config has no layers list")
            counter = [0]
            layers = tuple(
                _parse_layer(raw, (), counter, dataset_shapes) for raw in raw_layers
            )
            keras_version = _attribute_text(handle.attrs.get("keras_version"))
    except OSError as exc:
        raise LegacyH5Error("could not open H5 model %s: %s" % (path, exc)) from exc

    flattened = tuple(_walk_layers(layers))
    input_shape = next(
        (layer.output_shape for layer in flattened if layer.class_name == "InputLayer"),
        None,
    )
    dense_layers = tuple(_dense_records(flattened, dataset_shapes))
    boundary = _find_boundary(flattened, dense_layers)
    dropout_rates = tuple(
        layer.dropout_rate
        for layer in flattened
        if layer.class_name == "Dropout" and layer.dropout_rate is not None
    )
    return LegacyModelAnalysis(
        source_path=str(source.resolve()),
        source_sha256=source_hash,
        keras_version=keras_version,
        input_shape=input_shape,
        layers=layers,
        dense_layers=dense_layers,
        dropout_rates=dropout_rates,
        boundary=boundary,
    )


def find_dense_suffix(analysis: LegacyModelAnalysis) -> DenseSuffixBoundary:
    """Return the validated GlobalAveragePooling2D-to-Dense split boundary."""
    return analysis.boundary


def _read_model_config(handle: Any) -> dict:
    raw = handle.attrs.get("model_config")
    if raw is None:
        raise LegacyH5Error("model_config attribute is missing")
    text = _attribute_text(raw)
    if not text:
        raise LegacyH5Error("model_config attribute is empty")
    try:
        config = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LegacyH5Error("model_config is invalid JSON") from exc
    if not isinstance(config, dict):
        raise LegacyH5Error("model_config root must be an object")
    return config


def _attribute_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _dataset_shapes(handle: Any) -> dict:
    if "model_weights" not in handle:
        raise LegacyH5Error("model_weights group is missing")
    shapes = {}

    def collect(name: str, obj: Any) -> None:
        if hasattr(obj, "shape"):
            shapes[name] = tuple(int(dim) for dim in obj.shape)

    handle["model_weights"].visititems(collect)
    return shapes


def _parse_layer(raw: Any, parent: Tuple[str, ...], counter: list, dataset_shapes: dict) -> LayerRecord:
    if not isinstance(raw, dict):
        raise LegacyH5Error("model_config layer is not an object")
    class_name = raw.get("class_name")
    config = raw.get("config")
    if not isinstance(class_name, str) or not isinstance(config, dict):
        raise LegacyH5Error("model_config layer lacks class_name or config")
    name = raw.get("name", config.get("name"))
    if not isinstance(name, str) or not name:
        raise LegacyH5Error("model_config layer has no name")
    path = parent + (name,)
    index = counter[0]
    counter[0] += 1
    raw_children = config.get("layers") if class_name in {"Functional", "Model", "Sequential"} else None
    children = tuple(
        _parse_layer(child, path, counter, dataset_shapes) for child in raw_children or ()
    )
    input_shape, output_shape = _known_shapes(class_name, config, dataset_shapes, name)
    return LayerRecord(
        index=index,
        path=path,
        name=name,
        class_name=class_name,
        input_shape=input_shape,
        output_shape=output_shape,
        activation=_activation_name(config.get("activation")),
        dropout_rate=_dropout_rate(config) if class_name == "Dropout" else None,
        parameter_count=_parameter_count_for_layer(dataset_shapes, name)
        if not children
        else 0,
        trainable=bool(config.get("trainable", True)),
        inference_behavior="identity" if class_name == "Dropout" else "active",
        partition="software" if class_name not in {"Dense", "Dropout", "Flatten"} else "hardware",
        children=children,
    )


def _known_shapes(class_name: str, config: dict, dataset_shapes: dict, name: str) -> Tuple[Optional[Shape], Optional[Shape]]:
    if class_name == "InputLayer":
        shape = config.get("batch_input_shape")
        return None, _shape_from_json(shape)
    if class_name == "Dense":
        kernel = _layer_dataset(dataset_shapes, name, "kernel:0")
        if kernel and len(kernel) == 2:
            return (None, kernel[0]), (None, kernel[1])
    if class_name == "GlobalAveragePooling2D":
        return None, None
    return None, None


def _shape_from_json(value: Any) -> Optional[Shape]:
    if not isinstance(value, (list, tuple)):
        return None
    try:
        return tuple(None if item is None else int(item) for item in value)
    except (TypeError, ValueError):
        return None


def _activation_name(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("class_name") or value.get("registered_name")
        return str(name) if name else None
    return None


def _dropout_rate(config: dict) -> float:
    try:
        return float(config["rate"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LegacyH5Error("Dropout layer has no valid rate") from exc


def _parameter_count_for_layer(dataset_shapes: dict, name: str) -> int:
    return sum(_element_count(shape) for path, shape in dataset_shapes.items() if _belongs_to_layer(path, name))


def _element_count(shape: Tuple[int, ...]) -> int:
    count = 1
    for dim in shape:
        count *= dim
    return count


def _belongs_to_layer(dataset_path: str, name: str) -> bool:
    return ("/" + name + "/") in ("/" + dataset_path)


def _layer_dataset(dataset_shapes: dict, name: str, suffix: str) -> Optional[Tuple[int, ...]]:
    matches = [shape for path, shape in dataset_shapes.items() if _belongs_to_layer(path, name) and path.endswith("/" + suffix)]
    if len(matches) > 1:
        raise LegacyH5Error("ambiguous %s tensor for layer %s" % (suffix, name))
    return matches[0] if matches else None


def _walk_layers(layers: Iterable[LayerRecord]) -> Iterable[LayerRecord]:
    for layer in layers:
        yield layer
        yield from _walk_layers(layer.children)


def _dense_records(layers: Iterable[LayerRecord], dataset_shapes: dict) -> Iterable[DenseLayerRecord]:
    for layer in layers:
        if layer.class_name != "Dense":
            continue
        kernel = _layer_dataset(dataset_shapes, layer.name, "kernel:0")
        bias = _layer_dataset(dataset_shapes, layer.name, "bias:0")
        if kernel is None or len(kernel) != 2:
            raise LegacyH5Error("Dense layer %s has no rank-2 kernel" % layer.name)
        if bias is not None and (len(bias) != 1 or bias[0] != kernel[1]):
            raise LegacyH5Error("Dense layer %s has incompatible bias" % layer.name)
        yield DenseLayerRecord(
            name=layer.name,
            path=layer.path,
            in_features=kernel[0],
            out_features=kernel[1],
            activation=layer.activation or "linear",
            kernel_shape=(kernel[0], kernel[1]),
            bias_shape=bias,
            parameter_count=_element_count(kernel) + (_element_count(bias) if bias else 0),
        )


def _find_boundary(layers: Tuple[LayerRecord, ...], dense_layers: Tuple[DenseLayerRecord, ...]) -> DenseSuffixBoundary:
    gaps = [layer for layer in layers if layer.class_name == "GlobalAveragePooling2D"]
    if len(gaps) != 1:
        raise LegacyH5Error("expected exactly one GlobalAveragePooling2D boundary")
    if not dense_layers:
        raise LegacyH5Error("no Dense suffix follows GlobalAveragePooling2D")
    feature_width = dense_layers[0].in_features
    gap = gaps[0]
    if gap.index >= next(layer.index for layer in layers if layer.name == dense_layers[0].name):
        raise LegacyH5Error("Dense suffix does not follow GlobalAveragePooling2D")
    unsupported_prefix = tuple(
        layer.name for layer in layers if layer.index < gap.index and layer.class_name != "InputLayer"
    )
    return DenseSuffixBoundary(
        layer_name=gap.name,
        feature_width=feature_width,
        unsupported_prefix=unsupported_prefix,
        dense_suffix=tuple(layer.name for layer in dense_layers),
    )


def _shape_to_list(shape: Optional[Shape]) -> Optional[list]:
    return list(shape) if shape is not None else None
