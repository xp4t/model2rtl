"""Behavioral tests for deterministic, framework-neutral V2 GraphIR."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from model2rtl.v2.ir import (
    ConstantIR,
    GraphIR,
    GraphValidationError,
    NodeIR,
    TensorIR,
    canonical_json,
    graph_sha256,
)


def graph_with_two_nodes(reverse_tensor_order: bool = False) -> GraphIR:
    tensors = (
        TensorIR("input", "input", (1, 8), "float32", "NC"),
        TensorIR("hidden", "hidden", (1, 8), "float32", "NC"),
        TensorIR("output", "output", (1, 8), "float32", "NC"),
    )
    if reverse_tensor_order:
        tensors = tuple(reversed(tensors))
    first_attributes = {"alpha": 0.5, "tags": ("stable", "v2")}
    if reverse_tensor_order:
        first_attributes = {"tags": ("stable", "v2"), "alpha": 0.5}
    return GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=tensors,
        nodes=(
            NodeIR("relu-1", "relu-1", "Relu", ("input",), ("hidden",), first_attributes, {}),
            NodeIR("relu-2", "relu-2", "Relu", ("hidden",), ("output",), {}, {}),
        ),
        constants=(),
        metadata={"importer": {"name": "fixture", "source_index": 0}},
    )


def test_canonical_graph_serialization_is_stable_for_equivalent_records() -> None:
    """Changing harmless mapping or tensor insertion order must not change the digest."""
    graph_a = graph_with_two_nodes()
    graph_b = graph_with_two_nodes(reverse_tensor_order=True)

    assert canonical_json(graph_a) == canonical_json(graph_b)
    assert graph_sha256(graph_a) == graph_sha256(graph_b)
    assert json.loads(canonical_json(graph_a))["schema_version"] == "model2rtl-graph-v1"


def test_graph_validation_rejects_duplicate_ids() -> None:
    """Allowing two tensor records with the same ID must fail validation."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=(
            TensorIR("input", "input", (1,), "float32"),
            TensorIR("output", "first", (1,), "float32"),
            TensorIR("output", "second", (1,), "float32"),
        ),
        nodes=(NodeIR("node", "node", "Identity", ("input",), ("output",), {}, {}),),
        constants=(),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="duplicate tensor ID"):
        graph.validate()


def test_graph_validation_rejects_missing_producer() -> None:
    """An edge from an unproduced tensor must not be accepted as valid GraphIR."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=(
            TensorIR("input", "input", (1,), "float32"),
            TensorIR("output", "output", (1,), "float32"),
        ),
        nodes=(NodeIR("node", "node", "Identity", ("missing",), ("output",), {}, {}),),
        constants=(),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="missing producer"):
        graph.validate()


def test_graph_validation_rejects_multiple_producers() -> None:
    """Two nodes producing one tensor ID would make dataflow ambiguous."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=(
            TensorIR("input", "input", (1,), "float32"),
            TensorIR("output", "output", (1,), "float32"),
        ),
        nodes=(
            NodeIR("first", "first", "Identity", ("input",), ("output",), {}, {}),
            NodeIR("second", "second", "Identity", ("input",), ("output",), {}, {}),
        ),
        constants=(),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="multiple producers"):
        graph.validate()


def test_graph_validation_rejects_cycles() -> None:
    """A cyclic dataflow graph is invalid even when every tensor is declared."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("second",),
        tensors=(
            TensorIR("input", "input", (1,), "float32"),
            TensorIR("first", "first", (1,), "float32"),
            TensorIR("second", "second", (1,), "float32"),
        ),
        nodes=(
            NodeIR("first", "first", "Identity", ("second",), ("first",), {}, {}),
            NodeIR("second", "second", "Identity", ("first",), ("second",), {}, {}),
        ),
        constants=(),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="cycle"):
        graph.validate()


def test_graph_validation_rejects_dangling_outputs() -> None:
    """A declared output without any source must not pass graph validation."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=(TensorIR("input", "input", (1,), "float32"),),
        nodes=(),
        constants=(),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="dangling graph output"):
        graph.validate()


def test_graph_validation_rejects_malformed_constant_byte_counts() -> None:
    """Changing the byte-count check permits a corrupt float32 constant."""
    data = b"\x00\x00\x00\x00"
    graph = GraphIR(
        inputs=(),
        outputs=("weights",),
        tensors=(TensorIR("weights", "weights", (2,), "float32"),),
        nodes=(),
        constants=(
            ConstantIR(
                "weights",
                "float32",
                (2,),
                base64.b64encode(data).decode("ascii"),
                hashlib.sha256(data).hexdigest(),
            ),
        ),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="byte count"):
        graph.validate()


def test_constant_from_values_normalizes_to_little_endian_bytes() -> None:
    """Using host-endian packing would change this canonical constant payload."""
    constant = ConstantIR.from_values("weights", "uint16", (2,), (1, 513))

    assert constant.little_endian_data_base64 == base64.b64encode(
        b"\x01\x00\x01\x02"
    ).decode("ascii")
    assert constant.data_sha256 == hashlib.sha256(b"\x01\x00\x01\x02").hexdigest()


@pytest.mark.parametrize(
    ("metadata", "attributes", "source_location", "message"),
    (
        (None, {}, {}, "graph.metadata must be a mapping"),
        ({}, None, {}, "node 'node'.attributes must be a mapping"),
        ({}, {}, None, "node 'node'.source_location must be a mapping"),
    ),
)
def test_graph_validation_requires_mapping_at_each_metadata_boundary(
    metadata: object,
    attributes: object,
    source_location: object,
    message: str,
) -> None:
    """Allowing null at a map boundary makes GraphIR metadata ambiguous."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=(
            TensorIR("input", "input", (1,), "float32"),
            TensorIR("output", "output", (1,), "float32"),
        ),
        nodes=(
            NodeIR(
                "node",
                "node",
                "Identity",
                ("input",),
                ("output",),
                attributes,
                source_location,
            ),
        ),
        constants=(),
        metadata=metadata,
    )

    with pytest.raises(GraphValidationError, match="^" + message + "$"):
        graph.validate()


def test_graph_validation_rejects_explicit_big_endian_constant_dtype() -> None:
    """Accepting big-endian constant bytes breaks the little-endian wire format."""
    data = b"\x00\x01"
    graph = GraphIR(
        inputs=(),
        outputs=("weights",),
        tensors=(TensorIR("weights", "weights", (1,), ">u2"),),
        nodes=(),
        constants=(
            ConstantIR(
                "weights",
                ">u2",
                (1,),
                base64.b64encode(data).decode("ascii"),
                hashlib.sha256(data).hexdigest(),
            ),
        ),
        metadata={},
    )

    with pytest.raises(
        GraphValidationError,
        match=r"^constant 'weights' dtype must be little-endian$",
    ):
        graph.validate()


def test_graph_validation_rejects_recursive_framework_object_leakage() -> None:
    """Permitting arbitrary nested objects would leak importer framework values."""

    class FrameworkObject:
        pass

    graph = GraphIR(
        inputs=("input",),
        outputs=("output",),
        tensors=(
            TensorIR("input", "input", (1,), "float32"),
            TensorIR("output", "output", (1,), "float32"),
        ),
        nodes=(
            NodeIR(
                "node",
                "node",
                "Identity",
                ("input",),
                ("output",),
                {"nested": [FrameworkObject()]},
                {},
            ),
        ),
        constants=(),
        metadata={},
    )

    with pytest.raises(GraphValidationError, match="framework-neutral"):
        graph.validate()


def test_canonical_json_serializes_finite_floats_as_hexadecimal() -> None:
    """Replacing hexadecimal float encoding with decimal JSON loses this invariant."""
    document = json.loads(canonical_json(graph_with_two_nodes()))

    assert document["nodes"][0]["attributes"]["alpha"] == 0.5.hex()


def test_graph_validation_preserves_explicitly_unknown_tensor_metadata() -> None:
    """Forcing a semantic dtype or scalar shape would misdescribe analysis-only values."""
    graph = GraphIR(
        inputs=("input",),
        outputs=("opaque",),
        tensors=(
            TensorIR("input", "input", (1, 2), "float32"),
            TensorIR("opaque", "opaque", None, None),
        ),
        nodes=(
            NodeIR(
                "custom",
                "custom",
                "CustomOperator",
                ("input",),
                ("opaque",),
                {},
                {},
            ),
        ),
        constants=(),
        metadata={},
    )

    graph.validate()
    opaque = next(
        tensor for tensor in graph.to_dict()["tensors"] if tensor["id"] == "opaque"
    )
    assert opaque["shape"] is None
    assert opaque["dtype"] is None


def test_graph_validation_rejects_unknown_metadata_for_a_constant() -> None:
    """A byte-bearing constant must never use analysis-only unknown metadata."""
    data = b"\x00\x00\x00\x00"
    graph = GraphIR(
        inputs=(),
        outputs=("weights",),
        tensors=(TensorIR("weights", "weights", None, None),),
        nodes=(),
        constants=(
            ConstantIR(
                "weights",
                "float32",
                (1,),
                base64.b64encode(data).decode("ascii"),
                hashlib.sha256(data).hexdigest(),
            ),
        ),
        metadata={},
    )

    with pytest.raises(
        GraphValidationError,
        match=r"^constant 'weights' requires known tensor shape and dtype$",
    ):
        graph.validate()


def test_constant_node_may_own_the_tensor_carrying_its_static_payload() -> None:
    """Counting ConstantIR as a second producer must not reject ONNX Constant nodes."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            TensorIR("features", "features", (1, 2), "float32", "NC"),
            TensorIR("weights", "weights", (2, 1), "float32", "NC"),
            TensorIR("output", "output", (1, 1), "float32", "NC"),
        ),
        nodes=(
            NodeIR("constant", "constant", "Constant", (), ("weights",), {}, {}),
            NodeIR(
                "matmul",
                "matmul",
                "MatMul",
                ("features", "weights"),
                ("output",),
                {},
                {},
            ),
        ),
        constants=(
            ConstantIR.from_values(
                "weights", "float32", (2, 1), [[1.0], [2.0]]
            ),
        ),
        metadata={},
    )

    graph.validate()
