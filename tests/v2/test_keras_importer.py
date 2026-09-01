"""Native Keras/HDF5 importer tests using real deterministic models."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import h5py
import numpy as np
import pytest

from model2rtl.v2.ir import ConstantIR, canonical_json


keras = pytest.importorskip("keras")


def _fixed_values(shape: tuple[int, ...], start: int) -> np.ndarray:
    size = int(np.prod(shape))
    return (np.arange(start, start + size, dtype=np.float32) / 32.0).reshape(shape)


def _set_dense_weights(layer: object, start: int) -> None:
    kernel_shape = tuple(int(value) for value in layer.kernel.shape)
    bias_shape = tuple(int(value) for value in layer.bias.shape)
    layer.set_weights(
        [_fixed_values(kernel_shape, start), _fixed_values(bias_shape, -start)]
    )


def _save_h5_dense_dropout(path: Path) -> None:
    model = keras.Sequential(
        [
            keras.Input(shape=(8,), name="features"),
            keras.layers.Dense(4, activation="relu", name="hidden"),
            keras.layers.Dropout(0.25, name="dropout"),
            keras.layers.Dense(2, activation="linear", name="logits"),
        ],
        name="dense_dropout",
    )
    _set_dense_weights(model.get_layer("hidden"), 1)
    _set_dense_weights(model.get_layer("logits"), 101)
    model.save(path)


def _save_keras_dense_chain(path: Path) -> None:
    inputs = keras.Input(shape=(8,), name="features")
    hidden_1 = keras.layers.Dense(6, activation="relu", name="hidden_1")(inputs)
    hidden_2 = keras.layers.Dense(4, activation="relu", name="hidden_2")(hidden_1)
    outputs = keras.layers.Dense(2, activation="softmax", name="classes")(hidden_2)
    model = keras.Model(inputs, outputs, name="dense_chain")
    _set_dense_weights(model.get_layer("hidden_1"), 1)
    _set_dense_weights(model.get_layer("hidden_2"), 101)
    _set_dense_weights(model.get_layer("classes"), 201)
    model.save(path)


def _save_h5_cnn(path: Path) -> None:
    model = keras.Sequential(
        [
            keras.Input(shape=(6, 6, 1), name="image"),
            keras.layers.Conv2D(2, (3, 3), name="conv"),
            keras.layers.MaxPooling2D((2, 2), name="pool"),
            keras.layers.Flatten(name="flatten"),
            keras.layers.Dense(3, activation="relu", name="features"),
            keras.layers.Dense(2, name="classes"),
        ],
        name="cnn_prefix",
    )
    conv = model.get_layer("conv")
    conv.set_weights(
        [
            _fixed_values(tuple(int(value) for value in conv.kernel.shape), 1),
            _fixed_values(tuple(int(value) for value in conv.bias.shape), -1),
        ]
    )
    _set_dense_weights(model.get_layer("features"), 101)
    _set_dense_weights(model.get_layer("classes"), 201)
    model.save(path)


def _save_channels_first_cnn(path: Path) -> None:
    inputs = keras.Input(batch_shape=(1, 3, 6, 6), name="image")
    outputs = keras.layers.Conv2D(
        2,
        (3, 3),
        data_format="channels_first",
        name="conv",
    )(inputs)
    model = keras.Model(inputs, outputs, name="channels_first_cnn")
    conv = model.get_layer("conv")
    conv.set_weights(
        [
            _fixed_values(tuple(int(value) for value in conv.kernel.shape), 1),
            _fixed_values(tuple(int(value) for value in conv.bias.shape), -1),
        ]
    )
    model.save(path)


def _save_unsafe_lambda_envelope(path: Path) -> None:
    model_config = {
        "class_name": "Sequential",
        "config": {
            "name": "unsafe_lambda",
            "layers": [
                {
                    "class_name": "InputLayer",
                    "config": {
                        "name": "features",
                        "batch_input_shape": [None, 4],
                        "dtype": "float32",
                    },
                },
                {"class_name": "Lambda", "config": {"name": "unsafe"}},
            ],
        },
    }
    with h5py.File(path, "w") as handle:
        handle.attrs["model_config"] = json.dumps(model_config)
        handle.attrs["keras_version"] = "2.15.0"
        handle.attrs["backend"] = "tensorflow"


class _LayerWithoutPublicInput:
    """Delegate a real layer while reproducing legacy missing-input metadata."""

    def __init__(self, layer: object) -> None:
        self._layer = layer

    @property
    def input(self) -> object:
        raise AttributeError("layer has never been called")

    def __getattr__(self, name: str) -> object:
        if name == "input":
            raise AttributeError("layer has never been called")
        return getattr(self._layer, name)


class _SequentialWithHiddenLayerInput:
    def __init__(
        self,
        model: object,
        hidden_layer_name: str,
        strip_build_config: bool = False,
    ) -> None:
        self._model = model
        self._hidden_layer_name = hidden_layer_name
        self._strip_build_config = strip_build_config
        self.layers = [
            _LayerWithoutPublicInput(layer)
            if layer.name == hidden_layer_name
            else layer
            for layer in model.layers
        ]
        self.inputs = model.inputs
        self.outputs = model.outputs
        self.name = model.name

    def get_config(self) -> object:
        config = copy.deepcopy(self._model.get_config())
        if self._strip_build_config:
            for record in config["layers"]:
                if record.get("config", {}).get("name") == self._hidden_layer_name:
                    record.pop("build_config", None)
        return config


def _constant_array(constant: ConstantIR) -> np.ndarray:
    data = base64.b64decode(constant.little_endian_data_base64)
    return np.frombuffer(data, dtype=np.dtype(constant.dtype).newbyteorder("<")).reshape(
        constant.shape
    )


def _walk(value: object) -> Iterator[object]:
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def test_h5_import_preserves_dense_constants_dropout_and_source_bytes(
    tmp_path: Path,
) -> None:
    """Dropping Dropout, transposing kernels, or mutating H5 must fail this test."""
    from model2rtl.v2.importers.keras import import_keras

    source = tmp_path / "model.h5"
    _save_h5_dense_dropout(source)
    source_bytes = source.read_bytes()

    first = import_keras(str(source))
    second = import_keras(str(source))

    assert source.read_bytes() == source_bytes
    assert first.report.frontend == "keras"
    assert first.report.source_format == "h5"
    assert first.report.source_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert first.report.frontend_version
    assert first.graph.metadata["keras_recovery"] == {
        "mode": "native_executable",
        "executable": True,
        "weights_verified": True,
        "unsafe_code_blocked": False,
    }
    assert canonical_json(first.graph) == canonical_json(second.graph)
    assert str(tmp_path) not in canonical_json(first.graph)
    assert [node.op_type for node in first.graph.nodes] == [
        "Dense",
        "ReLU",
        "Dropout",
        "Dense",
    ]

    dense_nodes = [node for node in first.graph.nodes if node.op_type == "Dense"]
    constant_by_id = {
        constant.tensor_id: constant for constant in first.graph.constants
    }
    hidden_kernel = constant_by_id[dense_nodes[0].attributes["kernel_tensor_id"]]
    logits_kernel = constant_by_id[dense_nodes[1].attributes["kernel_tensor_id"]]
    assert hidden_kernel.shape == (8, 4)
    assert logits_kernel.shape == (4, 2)
    np.testing.assert_array_equal(
        _constant_array(hidden_kernel), _fixed_values((8, 4), 1)
    )
    np.testing.assert_array_equal(
        _constant_array(logits_kernel), _fixed_values((4, 2), 101)
    )

    dropout = next(node for node in first.graph.nodes if node.op_type == "Dropout")
    assert dropout.attributes["inference_identity_proven"] is True
    assert dropout.attributes["rate"] == 0.25

    loaded = keras.models.load_model(source, compile=False)
    probe = keras.Model(
        loaded.inputs,
        [loaded.get_layer("hidden").output, loaded.get_layer("dropout").output],
    )
    before, after = probe(
        [np.arange(8, dtype=np.float32)[None, :]], training=False
    )
    np.testing.assert_array_equal(np.asarray(before), np.asarray(after))

    copied = tmp_path / "elsewhere" / "same-model.h5"
    copied.parent.mkdir()
    copied.write_bytes(source_bytes)
    assert canonical_json(first.graph) == canonical_json(import_keras(str(copied)).graph)


def test_unsafe_h5_never_calls_native_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing preflight routing would execute the forbidden native loader."""
    from model2rtl.v2.importers import keras as importer

    source = tmp_path / "unsafe.h5"
    _save_unsafe_lambda_envelope(source)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("native loader called for unsafe H5")

    monkeypatch.setattr(importer.keras.models, "load_model", forbidden)

    result = importer.import_keras(str(source))

    assert [node.op_type for node in result.graph.nodes] == ["Lambda"]
    assert result.graph.metadata["keras_recovery"] == {
        "mode": "structural_analysis",
        "executable": False,
        "weights_verified": False,
        "unsafe_code_blocked": True,
        "native_loader_error": None,
    }


def test_native_loader_failure_falls_back_structurally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing fallback routing would turn a complete legacy H5 into an error."""
    from model2rtl.v2.importers import keras as importer

    source = tmp_path / "legacy.h5"
    _save_h5_dense_dropout(source)
    source_bytes = source.read_bytes()

    def fail_native(*args: object, **kwargs: object) -> object:
        raise ValueError("legacy deserializer rejected configuration")

    monkeypatch.setattr(importer.keras.models, "load_model", fail_native)

    result = importer.import_keras(str(source))

    assert source.read_bytes() == source_bytes
    assert result.report.source_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert result.graph.constants == ()
    assert result.graph.metadata["keras_recovery"] == {
        "mode": "structural_analysis",
        "executable": False,
        "weights_verified": False,
        "unsafe_code_blocked": False,
        "native_loader_error": "ValueError: legacy deserializer rejected configuration",
    }


def test_native_graph_conversion_failure_falls_back_structurally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy public tensor metadata must not prevent structural analysis."""
    from model2rtl.v2.importers import ImporterError
    from model2rtl.v2.importers import keras as importer

    source = tmp_path / "legacy_graph.h5"
    _save_h5_dense_dropout(source)

    def fail_graph(*args: object, **kwargs: object) -> object:
        raise ImporterError("native graph conversion failed")

    monkeypatch.setattr(importer, "_graph_from_model", fail_graph)

    result = importer.import_keras(str(source))

    assert result.graph.constants == ()
    assert result.graph.metadata["keras_recovery"] == {
        "mode": "structural_analysis",
        "executable": False,
        "weights_verified": False,
        "unsafe_code_blocked": False,
        "native_loader_error": "ImporterError: native graph conversion failed",
    }


def test_keras_archive_stays_on_native_loader_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accidentally applying HDF5 preflight to ZIP-based .keras must fail."""
    from model2rtl.v2.importers import keras as importer

    source = tmp_path / "native.keras"
    _save_keras_dense_chain(source)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("HDF5 preflight called for .keras archive")

    monkeypatch.setattr(importer, "inspect_h5", forbidden, raising=False)

    result = importer.import_keras(str(source))

    assert result.graph.metadata["keras_recovery"]["mode"] == "native_executable"


def test_sequential_layer_without_public_input_uses_serialized_build_shape() -> None:
    """Requiring layer.input would reject an otherwise introspectable Sequential."""
    from model2rtl.v2.importers import keras as importer

    model = keras.Sequential(
        [
            keras.Input(shape=(8,), name="features"),
            keras.layers.Dense(4, name="hidden"),
            keras.layers.Dense(2, name="output"),
        ],
        name="missing_public_input",
    )
    _set_dense_weights(model.get_layer("hidden"), 1)
    _set_dense_weights(model.get_layer("output"), 101)
    wrapped = _SequentialWithHiddenLayerInput(model, "hidden")

    graph = importer._graph_from_model(wrapped, "h5", "0" * 64)

    assert [node.op_type for node in graph.nodes] == ["Dense", "Dense"]
    assert len(graph.constants) == 4
    graph.validate()


def test_sequential_layer_without_input_or_build_shape_uses_previous_output() -> None:
    """Dropping the prior public output fallback would reject legacy Sequential."""
    from model2rtl.v2.importers import keras as importer

    model = keras.Sequential(
        [
            keras.Input(shape=(8,), name="features"),
            keras.layers.Dense(4, name="hidden"),
            keras.layers.Dense(2, name="output"),
        ],
        name="previous_output_fallback",
    )
    _set_dense_weights(model.get_layer("hidden"), 1)
    _set_dense_weights(model.get_layer("output"), 101)
    wrapped = _SequentialWithHiddenLayerInput(
        model,
        "output",
        strip_build_config=True,
    )

    graph = importer._graph_from_model(wrapped, "h5", "0" * 64)

    output = next(node for node in graph.nodes if node.name == "output")
    input_tensor = next(tensor for tensor in graph.tensors if tensor.id == output.inputs[0])
    assert input_tensor.shape == (None, 4)
    assert input_tensor.dtype == "float32"
    graph.validate()


def test_keras_import_splits_every_fused_dense_activation_explicitly(
    tmp_path: Path,
) -> None:
    """Leaving a fused activation hidden inside Dense must fail this test."""
    from model2rtl.v2.importers.keras import import_keras

    source = tmp_path / "model.keras"
    _save_keras_dense_chain(source)
    source_bytes = source.read_bytes()

    result = import_keras(str(source))

    assert source.read_bytes() == source_bytes
    assert result.report.source_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert result.report.source_format == "keras"
    assert [node.op_type for node in result.graph.nodes] == [
        "Dense",
        "ReLU",
        "Dense",
        "ReLU",
        "Dense",
        "Softmax",
    ]
    for dense in result.graph.nodes[::2]:
        assert dense.attributes["activation"] == "linear"
        assert dense.attributes["source_activation"] in {"relu", "softmax"}
    for producer, activation in zip(result.graph.nodes[::2], result.graph.nodes[1::2]):
        assert activation.inputs == producer.outputs
    assert result.graph.outputs == result.graph.nodes[-1].outputs
    assert canonical_json(result.graph) == canonical_json(import_keras(str(source)).graph)


def test_h5_import_keeps_every_unsupported_cnn_layer_visible(tmp_path: Path) -> None:
    """Skipping an unsupported CNN prefix layer must fail this test."""
    from model2rtl.v2.importers.keras import import_keras

    source = tmp_path / "cnn.h5"
    _save_h5_cnn(source)

    result = import_keras(str(source))

    node_names = [node.name for node in result.graph.nodes]
    for layer_name in ("conv", "pool", "flatten", "features", "classes"):
        assert any(name == layer_name or name.startswith(layer_name + "/") for name in node_names)
    assert [node.op_type for node in result.graph.nodes] == [
        "Conv2D",
        "MaxPooling2D",
        "Flatten",
        "Dense",
        "ReLU",
        "Dense",
    ]
    tensor_by_id = {tensor.id: tensor for tensor in result.graph.tensors}
    assert tensor_by_id[result.graph.inputs[0]].layout is None
    assert tensor_by_id[result.graph.nodes[0].outputs[0]].layout == "NHWC"
    for node in result.graph.nodes:
        assert node.attributes["layer_config"]
        assert node.source_location["source_class"]


def test_rank4_keras_layout_requires_explicit_data_format_evidence(
    tmp_path: Path,
) -> None:
    """Rank alone must not label an input NHWC, while channels_first must stay NCHW."""
    from model2rtl.v2.importers.keras import import_keras

    source = tmp_path / "channels_first.keras"
    _save_channels_first_cnn(source)

    graph = import_keras(str(source)).graph
    tensor_by_id = {tensor.id: tensor for tensor in graph.tensors}
    conv = next(node for node in graph.nodes if node.op_type == "Conv2D")

    assert tensor_by_id[graph.inputs[0]].layout is None
    assert tensor_by_id[conv.outputs[0]].layout == "NCHW"


def test_functional_import_uses_actual_inbound_tensors_for_branches(
    tmp_path: Path,
) -> None:
    """Reconstructing a Functional model as a layer list must fail this test."""
    from model2rtl.v2.importers.keras import import_keras

    inputs = keras.Input(shape=(4,), name="features")
    left = keras.layers.Dense(3, name="left")(inputs)
    right = keras.layers.Dense(3, name="right")(inputs)
    outputs = keras.layers.Add(name="merge")([left, right])
    model = keras.Model(inputs, outputs, name="branched")
    _set_dense_weights(model.get_layer("left"), 1)
    _set_dense_weights(model.get_layer("right"), 101)
    source = tmp_path / "branched.keras"
    model.save(source)

    graph = import_keras(str(source)).graph

    merge = next(node for node in graph.nodes if node.name == "merge")
    dense_outputs = {
        node.outputs[0] for node in graph.nodes if node.op_type == "Dense"
    }
    assert set(merge.inputs) == dense_outputs
    assert len(merge.inputs) == 2


def test_import_keeps_a_registered_custom_layer_visible(tmp_path: Path) -> None:
    """Discarding a loadable unsupported custom layer must fail this test."""
    from model2rtl.v2.importers.keras import import_keras

    @keras.saving.register_keras_serializable(package="model2rtl_tests")
    class Scale(keras.layers.Layer):
        def __init__(self, factor: float, **kwargs: object) -> None:
            super().__init__(**kwargs)
            self.factor = factor

        def call(self, inputs: object) -> object:
            return inputs * self.factor

        def get_config(self) -> dict[str, object]:
            return {**super().get_config(), "factor": self.factor}

    inputs = keras.Input(shape=(4,), name="features")
    outputs = Scale(2.5, name="scale")(inputs)
    source = tmp_path / "custom.keras"
    keras.Model(inputs, outputs).save(source)

    graph = import_keras(str(source)).graph

    assert [node.op_type for node in graph.nodes] == ["Scale"]
    assert graph.nodes[0].name == "scale"
    assert graph.nodes[0].attributes["layer_config"]["factor"] == 2.5
    assert graph.nodes[0].source_location["source_class"] == "Scale"


def test_nested_functional_and_sequential_models_are_recursively_flattened(
    tmp_path: Path,
) -> None:
    """Opaque nested Model nodes would hide inner unsupported ops and graph edges."""
    from model2rtl.v2.importers.keras import import_keras

    sequence = keras.Sequential(
        [
            keras.Input(shape=(4,), name="sequence_input"),
            keras.layers.Dense(3, activation="relu", name="sequence_dense"),
            keras.layers.Dropout(0.2, name="sequence_dropout"),
        ],
        name="inner_sequence",
    )
    nested_input = keras.Input(shape=(4,), name="nested_input")
    sequence_output = sequence(nested_input)
    right = keras.layers.Dense(2, name="nested_right")(nested_input)
    merged = keras.layers.Concatenate(name="nested_concat")(
        [sequence_output, right]
    )
    nested_output = keras.layers.Dense(3, name="nested_projection")(merged)
    nested = keras.Model(
        nested_input, nested_output, name="inner_functional"
    )

    outer_input = keras.Input(shape=(4,), name="outer_input")
    prefix = keras.layers.Dense(4, name="outer_prefix")(outer_input)
    body = nested(prefix)
    outer_output = keras.layers.Dense(2, name="outer_output")(body)
    model = keras.Model(outer_input, outer_output, name="nested_model")
    source = tmp_path / "nested.keras"
    model.save(source)

    graph = import_keras(str(source)).graph

    assert not {"Functional", "Sequential"}.intersection(
        node.op_type for node in graph.nodes
    )

    def by_suffix(suffix: str) -> object:
        return next(
            node
            for node in graph.nodes
            if node.name == suffix or node.name.endswith("/" + suffix)
        )

    outer_prefix = by_suffix("outer_prefix")
    sequence_dense = by_suffix("sequence_dense")
    sequence_relu = by_suffix("sequence_dense/activation")
    sequence_dropout = by_suffix("sequence_dropout")
    nested_right = by_suffix("nested_right")
    nested_concat = by_suffix("nested_concat")
    nested_projection = by_suffix("nested_projection")
    outer_output_node = by_suffix("outer_output")

    assert nested_concat.op_type == "Concatenate"
    assert sequence_dense.inputs[0] == outer_prefix.outputs[0]
    assert sequence_dropout.inputs == sequence_relu.outputs
    assert nested_right.inputs[0] == outer_prefix.outputs[0]
    assert set(nested_concat.inputs) == {
        sequence_dropout.outputs[0],
        nested_right.outputs[0],
    }
    assert nested_projection.inputs[0] == nested_concat.outputs[0]
    assert outer_output_node.inputs[0] == nested_projection.outputs[0]
    assert graph.outputs == outer_output_node.outputs


def test_import_uses_tensorflow_nest_when_keras_tree_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requiring the Keras 3 tree namespace would break the Keras 2.15 floor."""
    from model2rtl.v2.importers import keras as importer

    source = tmp_path / "compat.keras"
    _save_keras_dense_chain(source)
    legacy_surface = SimpleNamespace(
        __version__=keras.__version__,
        activations=keras.activations,
        Model=keras.Model,
        models=keras.models,
        utils=keras.utils,
    )
    monkeypatch.setattr(importer, "keras", legacy_surface)

    graph = importer.import_keras(str(source)).graph

    assert [node.op_type for node in graph.nodes] == [
        "Dense",
        "ReLU",
        "Dense",
        "ReLU",
        "Dense",
        "Softmax",
    ]


def test_json_safe_uses_legacy_utils_when_keras_saving_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requiring the Keras 3 saving namespace would break config conversion."""
    from model2rtl.v2.importers import keras as importer

    token = object()
    legacy_surface = SimpleNamespace(
        utils=SimpleNamespace(
            serialize_keras_object=lambda value: {
                "class_name": "CompatToken",
                "config": {"matched": value is token},
            }
        )
    )
    monkeypatch.setattr(importer, "keras", legacy_surface)

    assert importer._json_safe(token) == {
        "class_name": "CompatToken",
        "config": {"matched": True},
    }


def test_imported_graph_contains_only_framework_neutral_values(tmp_path: Path) -> None:
    """Leaking Keras tensors or config objects anywhere in GraphIR must fail this test."""
    from model2rtl.v2.importers.keras import import_keras

    source = tmp_path / "model.keras"
    _save_keras_dense_chain(source)

    graph = import_keras(str(source)).graph
    graph.validate()

    for value in _walk(graph.to_dict()):
        module = type(value).__module__
        assert not module.startswith(("keras", "tensorflow")), (module, type(value))


def test_invalid_h5_reports_stable_preflight_diagnostic(tmp_path: Path) -> None:
    """Bypassing static preflight would expose version-specific loader text."""
    from model2rtl.v2.importers import ImporterError
    from model2rtl.v2.importers.keras import import_keras

    source = tmp_path / "broken.h5"
    source.write_bytes(b"not an hdf5 model")

    with pytest.raises(ImporterError) as raised:
        import_keras(str(source))

    message = str(raised.value)
    assert message.startswith("H5_INVALID:")
    assert str(source) in message
