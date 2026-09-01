"""Behavioral tests for conservative V2 suffix partitioning and costs."""

from __future__ import annotations

import pytest

from model2rtl.v2.capability import classify_graph
from model2rtl.v2.ir import (
    ConstantIR,
    GraphIR,
    GraphValidationError,
    NodeIR,
    TensorIR,
)
from model2rtl.v2.partition import estimate_partition_cost, partition_graph


def _tensor(
    tensor_id: str,
    shape: tuple[int | str | None, ...] | None,
    dtype: str | None = "float32",
    layout: str | None = "NC",
) -> TensorIR:
    return TensorIR(tensor_id, tensor_id, shape, dtype, layout)


def _constant(tensor_id: str, shape: tuple[int, ...]) -> ConstantIR:
    count = 1
    for dimension in shape:
        count *= dimension
    return ConstantIR.from_values(tensor_id, "float32", shape, [0.0] * count)


def _dense_node(
    node_id: str,
    input_id: str,
    output_id: str,
    weight_id: str,
    bias_id: str,
) -> NodeIR:
    return NodeIR(
        node_id,
        node_id,
        "Dense",
        (input_id,),
        (output_id,),
        {"kernel_tensor_id": weight_id, "bias_tensor_id": bias_id},
        {},
    )


def _dense_chain_graph() -> GraphIR:
    return GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("w1", (4, 5)),
            _tensor("b1", (5,)),
            _tensor("hidden_linear", (1, 5)),
            _tensor("hidden", (1, 5)),
            _tensor("w2", (5, 3)),
            _tensor("b2", (3,)),
            _tensor("output", (1, 3)),
        ),
        nodes=(
            _dense_node("dense1", "features", "hidden_linear", "w1", "b1"),
            NodeIR(
                "relu",
                "relu",
                "ReLU",
                ("hidden_linear",),
                ("hidden",),
                {},
                {},
            ),
            _dense_node("dense2", "hidden", "output", "w2", "b2"),
        ),
        constants=(
            _constant("w1", (4, 5)),
            _constant("b1", (5,)),
            _constant("w2", (5, 3)),
            _constant("b2", (3,)),
        ),
        metadata={},
    )


def _partition(graph: GraphIR):
    return partition_graph(graph, classify_graph(graph))


def test_full_dense_chain_selects_every_live_node_and_exact_boundaries() -> None:
    """Stopping after one Dense or omitting a live ReLU must shrink the safe suffix."""
    graph = _dense_chain_graph()

    partition = _partition(graph)

    assert partition.mode == "full_rtl"
    assert partition.software_prefix_node_ids == ()
    assert partition.rtl_node_ids == ("dense1", "relu", "dense2")
    assert partition.software_postfix_node_ids == ()
    assert partition.input_boundary_tensor_ids == ("features",)
    assert partition.output_boundary_tensor_ids == ("output",)
    assert partition.reasons == ()


def test_cnn_prefix_keeps_largest_dense_suffix_and_all_exclusions_explicit() -> None:
    """Selecting a separated CNN island or hiding prefix nodes would be unsafe."""
    graph = GraphIR(
        inputs=("image",),
        outputs=("output",),
        tensors=(
            _tensor("image", (1, 8, 8, 1), layout="NHWC"),
            _tensor("conv_out", (1, 6, 6, 2), layout="NHWC"),
            _tensor("pooled", (1, 3, 3, 2), layout="NHWC"),
            _tensor("flat", (1, 18)),
            _tensor("w1", (18, 4)),
            _tensor("b1", (4,)),
            _tensor("hidden_linear", (1, 4)),
            _tensor("hidden", (1, 4)),
            _tensor("w2", (4, 2)),
            _tensor("b2", (2,)),
            _tensor("output", (1, 2)),
        ),
        nodes=(
            NodeIR("conv", "conv", "Conv2D", ("image",), ("conv_out",), {}, {}),
            NodeIR("pool", "pool", "MaxPooling2D", ("conv_out",), ("pooled",), {}, {}),
            NodeIR("flatten", "flatten", "Flatten", ("pooled",), ("flat",), {}, {}),
            _dense_node("dense1", "flat", "hidden_linear", "w1", "b1"),
            NodeIR("relu", "relu", "ReLU", ("hidden_linear",), ("hidden",), {}, {}),
            _dense_node("dense2", "hidden", "output", "w2", "b2"),
        ),
        constants=(
            _constant("w1", (18, 4)),
            _constant("b1", (4,)),
            _constant("w2", (4, 2)),
            _constant("b2", (2,)),
        ),
        metadata={},
    )

    partition = _partition(graph)

    assert partition.mode == "hybrid"
    assert partition.software_prefix_node_ids == ("conv", "pool")
    assert partition.rtl_node_ids == ("flatten", "dense1", "relu", "dense2")
    assert partition.software_postfix_node_ids == ()
    assert partition.input_boundary_tensor_ids == ("pooled",)
    assert partition.output_boundary_tensor_ids == ("output",)
    assert tuple(item.node_id for item in partition.exclusion_reasons) == (
        "conv",
        "pool",
    )
    assert all("software prefix" in item.reason for item in partition.exclusion_reasons)


def test_probability_softmax_is_an_explicit_software_postfix() -> None:
    """Calling logits probabilities or silently deleting Softmax breaks the output contract."""
    base = _dense_chain_graph()
    graph = GraphIR(
        inputs=base.inputs,
        outputs=("probabilities",),
        tensors=base.tensors + (_tensor("probabilities", (1, 3)),),
        nodes=base.nodes
        + (
            NodeIR(
                "softmax",
                "softmax",
                "Softmax",
                ("output",),
                ("probabilities",),
                {"axis": -1},
                {},
            ),
        ),
        constants=base.constants,
        metadata={},
    )

    partition = _partition(graph)

    assert partition.mode == "hybrid"
    assert partition.rtl_node_ids == ("dense1", "relu", "dense2")
    assert partition.software_prefix_node_ids == ()
    assert partition.software_postfix_node_ids == ("softmax",)
    assert partition.input_boundary_tensor_ids == ("features",)
    assert partition.output_boundary_tensor_ids == ("output",)
    assert partition.exclusion_reasons[0].node_id == "softmax"
    assert "software postfix" in partition.exclusion_reasons[0].reason


def test_live_unknown_operator_makes_compilation_unavailable() -> None:
    """Downgrading unknown live semantics to software would claim an unsafe handoff."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(_tensor("features", (1, 4)), _tensor("output", (1, 4))),
        nodes=(
            NodeIR(
                "mystery",
                "mystery",
                "VendorUnknown",
                ("features",),
                ("output",),
                {},
                {},
            ),
        ),
        constants=(),
        metadata={},
    )

    partition = _partition(graph)

    assert partition.mode == "compile_unavailable"
    assert partition.rtl_node_ids == ()
    assert partition.software_prefix_node_ids == ()
    assert partition.software_postfix_node_ids == ()
    assert "live unsupported node mystery" in partition.reasons[0]
    assert partition.exclusion_reasons[0].node_id == "mystery"
    assert "rejected" in partition.exclusion_reasons[0].reason


def test_software_only_graph_is_analysis_only_with_reasons() -> None:
    """A graph without a Dense suffix must not be mislabeled as hybrid compilation."""
    graph = GraphIR(
        inputs=("image",),
        outputs=("output",),
        tensors=(
            _tensor("image", (1, 8, 8, 1), layout="NHWC"),
            _tensor("output", (1, 6, 6, 2), layout="NHWC"),
        ),
        nodes=(NodeIR("conv", "conv", "Conv2D", ("image",), ("output",), {}, {}),),
        constants=(),
        metadata={},
    )

    partition = _partition(graph)

    assert partition.mode == "analysis_only"
    assert partition.software_prefix_node_ids == ("conv",)
    assert partition.rtl_node_ids == ()
    assert "no safe linear Dense suffix" in partition.reasons[0]


def test_multiple_live_outputs_and_unknown_boundary_dtype_are_rejected() -> None:
    """A suffix without one representable output or entry cannot have a safe boundary."""
    base = _dense_chain_graph()
    branched = GraphIR(
        inputs=base.inputs,
        outputs=("left", "right"),
        tensors=base.tensors
        + (_tensor("left", (1, 3)), _tensor("right", (1, 3))),
        nodes=base.nodes
        + (
            NodeIR("left_relu", "left_relu", "ReLU", ("output",), ("left",), {}, {}),
            NodeIR("right_relu", "right_relu", "ReLU", ("output",), ("right",), {}, {}),
        ),
        constants=base.constants,
        metadata={},
    )
    invalid_entry = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4), dtype=None),
            _tensor("weights", (4, 3)),
            _tensor("bias", (3,)),
            _tensor("output", (1, 3)),
        ),
        nodes=(_dense_node("dense", "features", "output", "weights", "bias"),),
        constants=(_constant("weights", (4, 3)), _constant("bias", (3,))),
        metadata={},
    )

    multiple = _partition(branched)
    invalid = _partition(invalid_entry)

    assert multiple.mode == "compile_unavailable"
    assert "exactly one selected output" in multiple.reasons[0]
    assert invalid.mode == "compile_unavailable"
    assert "representable" in invalid.reasons[0]


def test_boundary_rejects_missing_or_ambiguous_layout() -> None:
    """Static shape and dtype alone cannot define a software/RTL tensor handoff."""
    base = _dense_chain_graph()

    for layout in (None, "ANY"):
        graph = GraphIR(
            inputs=base.inputs,
            outputs=base.outputs,
            tensors=(
                TensorIR("features", "features", (1, 4), "float32", layout),
            )
            + base.tensors[1:],
            nodes=base.nodes,
            constants=base.constants,
            metadata={},
        )

        partition = _partition(graph)

        assert partition.mode == "compile_unavailable"
        assert "representable" in partition.reasons[0]


@pytest.mark.parametrize(
    "dtype",
    [
        "int8",
        "uint8",
        "int16",
        "uint16",
        "int32",
        "uint32",
        "int64",
        "uint64",
        "float16",
        "float32",
        "float64",
    ],
)
def test_boundary_accepts_defined_real_numeric_calibration_dtypes(dtype: str) -> None:
    """Narrowing boundaries to one training dtype must reject valid calibration data."""
    base = _dense_chain_graph()
    graph = GraphIR(
        inputs=base.inputs,
        outputs=base.outputs,
        tensors=(TensorIR("features", "features", (1, 4), dtype, "NC"),)
        + base.tensors[1:],
        nodes=base.nodes,
        constants=base.constants,
        metadata={},
    )

    partition = _partition(graph)

    assert partition.mode == "full_rtl"


@pytest.mark.parametrize("dtype", [None, "bool", "S4", "U4", "complex64"])
def test_boundary_rejects_unknown_or_non_real_numeric_dtypes(
    dtype: str | None,
) -> None:
    """Accepting bool, text, complex, or unknown boundaries creates an invalid handoff."""
    base = _dense_chain_graph()
    graph = GraphIR(
        inputs=base.inputs,
        outputs=base.outputs,
        tensors=(TensorIR("features", "features", (1, 4), dtype, "NC"),)
        + base.tensors[1:],
        nodes=base.nodes,
        constants=base.constants,
        metadata={},
    )

    partition = _partition(graph)

    assert partition.mode == "compile_unavailable"
    assert "representable" in partition.reasons[0]


def test_object_boundary_dtype_is_rejected_by_graph_validation() -> None:
    """Object references must never cross into framework-neutral GraphIR boundaries."""
    base = _dense_chain_graph()
    graph = GraphIR(
        inputs=base.inputs,
        outputs=base.outputs,
        tensors=(TensorIR("features", "features", (1, 4), "object", "NC"),)
        + base.tensors[1:],
        nodes=base.nodes,
        constants=base.constants,
        metadata={},
    )

    with pytest.raises(
        GraphValidationError,
        match=r"^tensor 'features' dtype is not a fixed-width scalar dtype$",
    ):
        _partition(graph)


def test_costs_are_literal_graph_derived_values_for_tile_32() -> None:
    """Hard-coded model dimensions or a wrong tile formula must change these values."""
    graph = _dense_chain_graph()
    partition = _partition(graph)

    cost = estimate_partition_cost(graph, partition, output_tile=32)

    assert cost.boundary_transfer_bytes == 28
    assert cost.dense_macs == 35
    assert cost.weight_bits_4bit == 140
    assert cost.bias_bits == 256
    assert cost.parameter_bits == 396
    assert cost.activation_bytes == 52
    assert cost.estimated_cycles == 9
    assert cost.compute_to_transfer_ratio == 1.25
    assert cost.compilable_not_recommended is True
    assert cost.threshold_version == "model2rtl-cost-thresholds-v1"
    assert "transfer" in cost.reasons[0]


def test_wide_dense_cycles_use_ceiling_output_tiles() -> None:
    """Flooring 65 outputs to two tiles would undercount a required third tile."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 64)),
            _tensor("weights", (64, 65)),
            _tensor("bias", (65,)),
            _tensor("output", (1, 65)),
        ),
        nodes=(_dense_node("dense", "features", "output", "weights", "bias"),),
        constants=(_constant("weights", (64, 65)), _constant("bias", (65,))),
        metadata={},
    )

    cost = estimate_partition_cost(graph, _partition(graph), output_tile=32)

    assert cost.boundary_transfer_bytes == 516
    assert cost.dense_macs == 4160
    assert cost.weight_bits_4bit == 16640
    assert cost.bias_bits == 2080
    assert cost.parameter_bits == 18720
    assert cost.activation_bytes == 260
    assert cost.estimated_cycles == 192
