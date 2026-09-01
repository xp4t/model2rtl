"""Framework-free structural recovery tests for complete-model HDF5 metadata."""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import pytest

from model2rtl.v2.capability import SupportClass, classify_graph
from model2rtl.v2.importers.h5_metadata import inspect_h5
from model2rtl.v2.ir import canonical_json


def _write_h5(tmp_path: Path, name: str, model_config: object) -> Path:
    source = tmp_path / name
    with h5py.File(source, "w") as handle:
        handle.attrs["model_config"] = json.dumps(model_config)
        handle.attrs["keras_version"] = "2.15.0"
        handle.attrs["backend"] = "tensorflow"
    return source


def _input(name: str, shape: list[object], dtype: str = "float32") -> dict[str, object]:
    return {
        "class_name": "InputLayer",
        "config": {
            "name": name,
            "batch_input_shape": shape,
            "dtype": dtype,
        },
    }


@pytest.fixture
def legacy_lstm_h5(tmp_path: Path) -> Path:
    return _write_h5(
        tmp_path,
        "legacy_lstm.h5",
        {
            "class_name": "Sequential",
            "config": {
                "name": "legacy_lstm",
                "layers": [
                    _input("tokens", [None, 12], "int32"),
                    {
                        "class_name": "Embedding",
                        "config": {"name": "embedding", "input_dim": 32, "output_dim": 8},
                    },
                    {
                        "class_name": "LSTM",
                        "config": {"name": "lstm", "units": 4, "time_major": True},
                    },
                    {
                        "class_name": "Dense",
                        "config": {"name": "scores", "units": 2, "activation": "linear"},
                    },
                ],
            },
        },
    )


@pytest.fixture
def functional_h5(tmp_path: Path) -> Path:
    return _write_h5(
        tmp_path,
        "functional.h5",
        {
            "class_name": "Functional",
            "config": {
                "name": "merge_model",
                "layers": [
                    _input("left", [None, 4]),
                    _input("right", [None, 4]),
                    {
                        "class_name": "Concatenate",
                        "config": {"name": "merge", "axis": -1},
                        "inbound_nodes": [
                            [["left", 0, 0, {}], ["right", 0, 0, {}]]
                        ],
                    },
                ],
                "input_layers": [["left", 0, 0], ["right", 0, 0]],
                "output_layers": [["merge", 0, 0]],
            },
        },
    )


@pytest.fixture
def lambda_h5(tmp_path: Path) -> Path:
    return _write_h5(
        tmp_path,
        "lambda.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    _input("features", [None, 4]),
                    {"class_name": "Lambda", "config": {"name": "unsafe"}},
                ]
            },
        },
    )


@pytest.fixture
def dense_h5(tmp_path: Path) -> Path:
    return _write_h5(
        tmp_path,
        "dense.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    _input("features", [None, 4]),
                    {
                        "class_name": "Dense",
                        "config": {"name": "hidden", "units": 3, "activation": "relu"},
                    },
                ]
            },
        },
    )


def test_structural_sequential_preserves_every_operator(legacy_lstm_h5: Path) -> None:
    """A legacy loader failure still yields each serialized inference operator."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    graph = structural_graph_from_h5(inspect_h5(legacy_lstm_h5), "time_major")

    assert [node.op_type for node in graph.nodes] == ["Embedding", "LSTM", "Dense"]
    assert graph.metadata["keras_recovery"] == {
        "mode": "structural_analysis",
        "executable": False,
        "weights_verified": False,
        "unsafe_code_blocked": False,
        "native_loader_error": "time_major",
    }
    assert graph.constants == ()
    embedding = graph.nodes[0]
    embedding_output = next(
        tensor for tensor in graph.tensors if tensor.id == embedding.outputs[0]
    )
    assert embedding_output.dtype is None
    graph.validate()


def test_structural_functional_uses_declared_histories(functional_h5: Path) -> None:
    """Legacy Keras list histories must retain both inputs to a merge node."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    graph = structural_graph_from_h5(inspect_h5(functional_h5), "native failed")

    merge = next(node for node in graph.nodes if node.op_type == "Concatenate")
    assert len(merge.inputs) == 2
    assert graph.outputs == merge.outputs
    graph.validate()


def test_structural_keras3_tensor_descriptors_preserve_input_spec(tmp_path: Path) -> None:
    """Keras 3 descriptor histories supply shapes without a framework object."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    descriptor = {
        "class_name": "__keras_tensor__",
        "config": {
            "shape": [None, 5],
            "dtype": "float32",
            "keras_history": ["features", 0, 0],
        },
    }
    source = _write_h5(
        tmp_path,
        "keras3.h5",
        {
            "class_name": "Functional",
            "config": {
                "layers": [
                    _input("features", [None, 5]),
                    {
                        "class_name": "Dense",
                        "config": {"name": "projection", "units": 2, "activation": "linear"},
                        "inbound_nodes": [{"args": [descriptor], "kwargs": {}}],
                    },
                ],
                "input_layers": [["features", 0, 0]],
                "output_layers": [["projection", 0, 0]],
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))

    assert graph.tensors[0].shape == (None, 5)
    assert graph.tensors[0].dtype == "float32"
    assert graph.nodes[0].inputs == graph.inputs
    graph.validate()


def test_structural_input_uses_record_build_config_shape(tmp_path: Path) -> None:
    """Keras 3 stores some input shapes beside, rather than inside, layer config."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    source = _write_h5(
        tmp_path,
        "build-config.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    {
                        "class_name": "InputLayer",
                        "config": {"name": "features", "dtype": "float32"},
                        "build_config": {"input_shape": [None, 7]},
                    },
                    {
                        "class_name": "Dense",
                        "config": {"name": "projection", "units": 3},
                    },
                ]
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))

    assert graph.tensors[0].shape == (None, 7)
    assert graph.nodes[0].outputs[0] in {tensor.id for tensor in graph.tensors}


def test_structural_mixed_dtype_policy_degrades_to_unknown(tmp_path: Path) -> None:
    """A Keras policy name is not a GraphIR fixed-width scalar NumPy dtype."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    source = _write_h5(
        tmp_path,
        "mixed-policy.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    {
                        "class_name": "InputLayer",
                        "config": {
                            "name": "features",
                            "batch_input_shape": [None, 4],
                            "dtype": {
                                "class_name": "DTypePolicy",
                                "config": {"name": "mixed_float16"},
                            },
                        },
                    },
                    {
                        "class_name": "Dense",
                        "config": {"name": "projection", "units": 2},
                    },
                ]
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))

    assert graph.tensors[0].dtype is None
    assert graph.validate() is None


def test_structural_flatten_without_output_evidence_has_unknown_shape(
    tmp_path: Path,
) -> None:
    """A shape-changing Flatten cannot be called a no-op from input shape alone."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    source = _write_h5(
        tmp_path,
        "flatten.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    _input("features", [1, 2, 3]),
                    {"class_name": "Flatten", "config": {"name": "flatten"}},
                ]
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))
    flatten = graph.nodes[0]
    flattened = next(tensor for tensor in graph.tensors if tensor.id == flatten.outputs[0])

    assert flattened.shape is None
    assert classify_graph(graph)[0].support_class is SupportClass.SOFTWARE_FALLBACK


def test_unknown_operator_output_shape_does_not_inherit_input_dtype(
    tmp_path: Path,
) -> None:
    """Declared shape alone does not prove an unknown layer's output element type."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    source = _write_h5(
        tmp_path,
        "unknown-output.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    _input("features", [None, 4]),
                    {
                        "class_name": "OpaqueLayer",
                        "config": {
                            "name": "opaque",
                            "output_shape": [None, 3],
                        },
                    },
                ]
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))
    opaque = graph.nodes[0]
    output = next(tensor for tensor in graph.tensors if tensor.id == opaque.outputs[0])

    assert output.shape == (None, 3)
    assert output.dtype is None
    graph.validate()


def test_structural_reshape_uses_explicit_target_shape(tmp_path: Path) -> None:
    """A serialized Reshape target establishes a new shape instead of copying input."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    source = _write_h5(
        tmp_path,
        "reshape.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    _input("features", [1, 2, 3]),
                    {
                        "class_name": "Reshape",
                        "config": {"name": "reshape", "target_shape": [6]},
                    },
                ]
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))
    reshape = graph.nodes[0]
    reshaped = next(tensor for tensor in graph.tensors if tensor.id == reshape.outputs[0])

    assert reshaped.shape == (1, 6)
    assert reshaped.shape != graph.tensors[0].shape


def test_lambda_is_visible_and_marked_blocked(lambda_h5: Path) -> None:
    """Unsafe serialized code stays visible but structural recovery never executes it."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    graph = structural_graph_from_h5(inspect_h5(lambda_h5))

    assert any(node.op_type == "Lambda" for node in graph.nodes)
    assert graph.metadata["keras_recovery"]["unsafe_code_blocked"] is True
    graph.validate()


def test_structural_dense_without_constants_is_software_fallback(dense_h5: Path) -> None:
    """Structural topology alone must never promote Dense into the RTL partition."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    graph = structural_graph_from_h5(inspect_h5(dense_h5))
    decisions = classify_graph(graph, None)
    dense = next(item for item in decisions if item.op_type == "Dense")

    assert dense.support_class is SupportClass.SOFTWARE_FALLBACK
    assert graph.constants == ()


def test_structural_dense_splits_recognized_activation_without_weights(
    dense_h5: Path,
) -> None:
    """A fused serialized ReLU must become an explicit node without constants."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    graph = structural_graph_from_h5(inspect_h5(dense_h5))

    assert [node.op_type for node in graph.nodes] == ["Dense", "ReLU"]
    assert graph.nodes[0].attributes["weight_tensor_ids"] == ()
    assert graph.nodes[0].attributes["source_activation"] == "relu"
    assert graph.nodes[1].inputs == graph.nodes[0].outputs
    assert graph.outputs == graph.nodes[1].outputs


def test_nested_model_containers_remain_visible(tmp_path: Path) -> None:
    """Structural recovery must not flatten an unverified nested model body."""
    from model2rtl.v2.importers.keras_structural import structural_graph_from_h5

    source = _write_h5(
        tmp_path,
        "nested.h5",
        {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    _input("features", [None, 4]),
                    {
                        "class_name": "Functional",
                        "config": {
                            "name": "nested_backbone",
                            "layers": [_input("nested_input", [None, 4])],
                        },
                    },
                ]
            },
        },
    )

    graph = structural_graph_from_h5(inspect_h5(source))

    assert [node.op_type for node in graph.nodes] == ["Functional"]
    assert graph.nodes[0].source_location["source_class"] == "Functional"
    graph.validate()


def test_structural_translation_is_deterministic_and_framework_free(
    functional_h5: Path,
) -> None:
    """Detached model JSON must produce stable GraphIR without framework bindings."""
    import model2rtl.v2.importers.keras_structural as structural

    first = structural.structural_graph_from_h5(inspect_h5(functional_h5))
    second = structural.structural_graph_from_h5(inspect_h5(functional_h5))

    assert canonical_json(first) == canonical_json(second)
    assert "keras" not in structural.__dict__
    assert "tensorflow" not in structural.__dict__
    assert "tf" not in structural.__dict__
