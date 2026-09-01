"""Behavioral tests for centralized V2 capability decisions."""

from __future__ import annotations

import pytest

from model2rtl.v2.capability import (
    CAPABILITY_REGISTRY,
    InferenceAction,
    SupportClass,
    classify_graph,
)
from model2rtl.v2.ir import ConstantIR, GraphIR, NodeIR, TensorIR
from model2rtl.v2.model_contract.schema import (
    InputContract,
    ModelContract,
    OutputContract,
)


def _tensor(tensor_id: str, shape: tuple[int, ...]) -> TensorIR:
    return TensorIR(tensor_id, tensor_id, shape, "float32", "NC")


def _constant(tensor_id: str, shape: tuple[int, ...]) -> ConstantIR:
    count = 1
    for dimension in shape:
        count *= dimension
    return ConstantIR.from_values(tensor_id, "float32", shape, [0.0] * count)


def _dense_graph(extra_nodes: tuple[NodeIR, ...] = ()) -> GraphIR:
    nodes = (
        NodeIR(
            "dense",
            "dense",
            "Dense",
            ("features",),
            ("logits",),
            {"kernel_tensor_id": "weights", "bias_tensor_id": "bias"},
            {},
        ),
    ) + extra_nodes
    output_id = extra_nodes[-1].outputs[0] if extra_nodes else "logits"
    extra_tensors = tuple(
        _tensor(node.outputs[0], (1, 3))
        for node in extra_nodes
        if node.outputs[0] != "logits"
    )
    return GraphIR(
        inputs=("features",),
        outputs=(output_id,),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("weights", (4, 3)),
            _tensor("bias", (3,)),
            _tensor("logits", (1, 3)),
        )
        + extra_tensors,
        nodes=nodes,
        constants=(
            _constant("weights", (4, 3)),
            _constant("bias", (3,)),
        ),
        metadata={},
    )


def _argmax_contract() -> ModelContract:
    return ModelContract(
        input=InputContract("features", (1, 4), "float32", "NC"),
        output=OutputContract("classification", "argmax"),
    )


def test_registry_supported_entries_have_every_required_hook() -> None:
    """Removing any required supported-op hook must invalidate registry coverage."""
    supported = [
        entry
        for entry in CAPABILITY_REGISTRY.values()
        if entry.support_class is SupportClass.SUPPORTED
    ]

    assert supported
    for entry in supported:
        assert entry.validator_key
        assert entry.shape_rule_key
        assert entry.quantization_rule_key
        assert entry.lowering_rule_key
        assert entry.golden_rule_key


def test_classification_emits_one_ordered_decision_per_source_node() -> None:
    """Skipping or duplicating a source node must break the analysis inventory."""
    graph = _dense_graph(
        (
            NodeIR("relu", "relu", "ReLU", ("logits",), ("activated",), {}, {}),
            NodeIR(
                "custom",
                "custom",
                "VendorControlFlow",
                ("activated",),
                ("result",),
                {},
                {},
            ),
        )
    )

    decisions = classify_graph(graph)

    assert tuple(decision.node_id for decision in decisions) == (
        "dense",
        "relu",
        "custom",
    )
    assert decisions[0].support_class is SupportClass.SUPPORTED
    assert decisions[0].inference_action is InferenceAction.LOWER
    assert decisions[1].support_class is SupportClass.SUPPORTED
    assert decisions[1].inference_action is InferenceAction.LOWER
    assert decisions[2].support_class is SupportClass.UNSUPPORTED
    assert decisions[2].inference_action is InferenceAction.REJECT
    assert decisions[2].node_id == graph.nodes[2].id
    assert "unknown" in decisions[2].reason.lower()


def test_proven_dropout_is_removed_but_unproven_dropout_stays_software() -> None:
    """Treating training Dropout as an identity would change inference semantics."""
    graph = _dense_graph(
        (
            NodeIR(
                "dropout",
                "dropout",
                "Dropout",
                ("logits",),
                ("after_dropout",),
                {"inference_identity_proven": True},
                {},
            ),
        )
    )
    unproven = GraphIR(
        inputs=graph.inputs,
        outputs=graph.outputs,
        tensors=graph.tensors,
        nodes=(
            graph.nodes[0],
            NodeIR(
                "dropout",
                "dropout",
                "Dropout",
                ("logits",),
                ("after_dropout",),
                {"inference_identity_proven": False},
                {},
            ),
        ),
        constants=graph.constants,
        metadata={},
    )

    assert classify_graph(graph)[1].inference_action is InferenceAction.REMOVE
    decision = classify_graph(unproven)[1]
    assert decision.support_class is SupportClass.SOFTWARE_FALLBACK
    assert decision.inference_action is InferenceAction.SOFTWARE
    assert "not proven" in decision.reason.lower()


def test_proven_dropout_with_shape_or_dtype_change_stays_software() -> None:
    """An inference identity proof cannot erase a representation-changing edge."""
    base = _dense_graph()
    invalid_outputs = (((1, 4), "float32"), ((1, 3), "float64"))

    for output_shape, output_dtype in invalid_outputs:
        graph = GraphIR(
            inputs=base.inputs,
            outputs=("after_dropout",),
            tensors=base.tensors
            + (
                TensorIR(
                    "after_dropout",
                    "after_dropout",
                    output_shape,
                    output_dtype,
                    "NC",
                ),
            ),
            nodes=base.nodes
            + (
                NodeIR(
                    "dropout",
                    "dropout",
                    "Dropout",
                    ("logits",),
                    ("after_dropout",),
                    {"inference_identity_proven": True},
                    {},
                ),
            ),
            constants=base.constants,
            metadata={},
        )

        decision = classify_graph(graph)[1]

        assert decision.support_class is SupportClass.SOFTWARE_FALLBACK
        assert decision.inference_action is InferenceAction.SOFTWARE


def test_softmax_elision_requires_exact_argmax_classification_contract() -> None:
    """Eliding probability Softmax without an argmax contract is incorrect."""
    graph = _dense_graph(
        (
            NodeIR(
                "softmax",
                "softmax",
                "Softmax",
                ("logits",),
                ("probabilities",),
                {"axis": -1},
                {},
            ),
        )
    )

    without_contract = classify_graph(graph)[1]
    with_contract = classify_graph(graph, _argmax_contract())[1]

    assert without_contract.support_class is SupportClass.SOFTWARE_FALLBACK
    assert without_contract.inference_action is InferenceAction.SOFTWARE
    assert with_contract.inference_action is InferenceAction.ELIDE
    assert "argmax" in with_contract.reason.lower()


def test_softmax_elision_rejects_invalid_structure_or_class_axis() -> None:
    """Contract metadata must not elide a structurally invalid class Softmax."""
    base = _dense_graph()
    invalid_cases = (
        (("logits", "bias"), ("probabilities",), (1, 3), "float32", -1),
        (("logits",), ("probabilities", "extra"), (1, 3), "float32", -1),
        (("logits",), ("probabilities",), (1, 4), "float32", -1),
        (("logits",), ("probabilities",), (1, 3), "float64", -1),
        (("logits",), ("probabilities",), (1, 3), "float32", 0),
        (("logits",), ("probabilities",), (1, 3), "float32", -3),
    )

    for inputs, outputs, output_shape, output_dtype, axis in invalid_cases:
        output_tensors = tuple(
            TensorIR(item, item, output_shape, output_dtype, "NC")
            for item in outputs
        )
        graph = GraphIR(
            inputs=base.inputs,
            outputs=(outputs[0],),
            tensors=base.tensors + output_tensors,
            nodes=base.nodes
            + (
                NodeIR(
                    "softmax",
                    "softmax",
                    "Softmax",
                    inputs,
                    outputs,
                    {"axis": axis},
                    {},
                ),
            ),
            constants=base.constants,
            metadata={},
        )

        decision = classify_graph(graph, _argmax_contract())[1]

        assert decision.support_class is SupportClass.SOFTWARE_FALLBACK
        assert decision.inference_action is InferenceAction.SOFTWARE


def test_matmul_and_gemm_reject_reversed_data_and_weight_operands() -> None:
    """Constness must not erase the required dynamic-A/static-B operand roles."""
    for op_type in ("MatMul", "Gemm"):
        graph = GraphIR(
            inputs=("features",),
            outputs=("output",),
            tensors=(
                _tensor("features", (1, 4)),
                _tensor("weights", (4, 3)),
                _tensor("output", (1, 3)),
            ),
            nodes=(
                NodeIR(
                    "product",
                    "product",
                    op_type,
                    ("weights", "features"),
                    ("output",),
                    {},
                    {},
                ),
            ),
            constants=(_constant("weights", (4, 3)),),
            metadata={},
        )

        decision = classify_graph(graph)[0]

        assert decision.support_class is SupportClass.SOFTWARE_FALLBACK
        assert decision.inference_action is InferenceAction.SOFTWARE


def test_every_supported_decision_carries_all_required_hook_keys() -> None:
    """Dynamic promotion must not create a supported decision with fallback hooks."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("weights", (4, 3)),
            _tensor("product", (1, 3)),
            _tensor("bias", (3,)),
            _tensor("output", (1, 3)),
        ),
        nodes=(
            NodeIR(
                "matmul",
                "matmul",
                "MatMul",
                ("features", "weights"),
                ("product",),
                {},
                {},
            ),
            NodeIR(
                "bias_add",
                "bias_add",
                "Add",
                ("product", "bias"),
                ("output",),
                {},
                {},
            ),
        ),
        constants=(
            _constant("weights", (4, 3)),
            _constant("bias", (3,)),
        ),
        metadata={},
    )

    supported = [
        decision
        for decision in classify_graph(graph)
        if decision.support_class is SupportClass.SUPPORTED
    ]

    assert tuple(item.node_id for item in supported) == ("matmul", "bias_add")
    for decision in supported:
        assert decision.validator_key
        assert decision.shape_rule_key
        assert decision.quantization_rule_key
        assert decision.lowering_rule_key
        assert decision.golden_rule_key


def test_conv_and_pool_are_explicit_software_fallbacks() -> None:
    """Accidentally promoting CNN operators would overstate Dense-only support."""
    graph = GraphIR(
        inputs=("image",),
        outputs=("pooled",),
        tensors=(
            TensorIR("image", "image", (1, 8, 8, 1), "float32", "NHWC"),
            TensorIR("conv_out", "conv_out", (1, 6, 6, 2), "float32", "NHWC"),
            TensorIR("pooled", "pooled", (1, 3, 3, 2), "float32", "NHWC"),
        ),
        nodes=(
            NodeIR("conv", "conv", "Conv2D", ("image",), ("conv_out",), {}, {}),
            NodeIR(
                "pool",
                "pool",
                "MaxPooling2D",
                ("conv_out",),
                ("pooled",),
                {},
                {},
            ),
        ),
        constants=(),
        metadata={},
    )

    decisions = classify_graph(graph)

    assert tuple(item.support_class for item in decisions) == (
        SupportClass.SOFTWARE_FALLBACK,
        SupportClass.SOFTWARE_FALLBACK,
    )
    assert all(item.inference_action is InferenceAction.SOFTWARE for item in decisions)


def test_known_control_flow_is_rejected_and_remains_visible() -> None:
    """Treating control flow as an ordinary fallback cannot guarantee a safe handoff."""
    graph = GraphIR(
        inputs=("condition",),
        outputs=("result",),
        tensors=(
            TensorIR("condition", "condition", (1,), "bool"),
            TensorIR("result", "result", (1,), "float32"),
        ),
        nodes=(NodeIR("if", "if", "If", ("condition",), ("result",), {}, {}),),
        constants=(),
        metadata={},
    )

    decision = classify_graph(graph)[0]

    assert decision.node_id == "if"
    assert decision.support_class is SupportClass.UNSUPPORTED
    assert decision.inference_action is InferenceAction.REJECT
    assert decision.roadmap_label == "control_flow"


@pytest.mark.parametrize("op_type", ["Gemm", "MatMul", "Relu", "Add", "Softmax"])
def test_nonstandard_onnx_domains_cannot_borrow_standard_operator_capabilities(
    op_type: str,
) -> None:
    """Removing the ONNX-domain gate must never promote a vendor operator by name."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("output", (1, 4)),
        ),
        nodes=(
            NodeIR(
                "vendor",
                "vendor",
                op_type,
                ("features",),
                ("output",),
                {},
                {
                    "frontend": "onnx",
                    "domain": "com.example.accelerator",
                    "opset_version": 1,
                },
            ),
        ),
        constants=(),
        metadata={},
    )

    decision = classify_graph(graph)[0]

    assert decision.support_class is SupportClass.UNSUPPORTED
    assert decision.inference_action is InferenceAction.REJECT
    assert "domain" in decision.reason.lower()


@pytest.mark.parametrize("domain", ["", "ai.onnx"])
def test_standard_onnx_domains_retain_standard_operator_capabilities(
    domain: str,
) -> None:
    """Rejecting either spelling of the standard ONNX domain breaks valid models."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("output", (1, 4)),
        ),
        nodes=(
            NodeIR(
                "relu",
                "relu",
                "Relu",
                ("features",),
                ("output",),
                {},
                {"frontend": "onnx", "domain": domain, "opset_version": 13},
            ),
        ),
        constants=(),
        metadata={},
    )

    decision = classify_graph(graph)[0]

    assert decision.support_class is SupportClass.SUPPORTED
    assert decision.inference_action is InferenceAction.LOWER


@pytest.mark.parametrize(
    ("opset_version", "shape", "expected_action"),
    [
        (11, (1, 3), InferenceAction.ELIDE),
        (11, (1, 2, 3), InferenceAction.SOFTWARE),
        (13, (1, 2, 3), InferenceAction.ELIDE),
    ],
)
def test_onnx_softmax_default_axis_is_resolved_from_the_node_opset_before_elision(
    opset_version: int,
    shape: tuple[int, ...],
    expected_action: InferenceAction,
) -> None:
    """Hard-coding the modern axis default must not elide legacy rank-3 Softmax."""
    layout = "NC" if len(shape) == 2 else "NCHW"
    graph = GraphIR(
        inputs=("logits",),
        outputs=("probabilities",),
        tensors=(
            TensorIR("logits", "logits", shape, "float32", layout),
            TensorIR(
                "probabilities", "probabilities", shape, "float32", layout
            ),
        ),
        nodes=(
            NodeIR(
                "softmax",
                "softmax",
                "Softmax",
                ("logits",),
                ("probabilities",),
                {},
                {
                    "frontend": "onnx",
                    "domain": "",
                    "opset_version": opset_version,
                },
            ),
        ),
        constants=(),
        metadata={},
    )

    decision = classify_graph(graph, _argmax_contract())[0]

    assert decision.inference_action is expected_action


def test_constant_nodes_feed_static_matmul_and_add_capability_patterns() -> None:
    """Treating Constant payloads as dynamic must break the Dense normalization path."""
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("weights", (4, 3)),
            _tensor("product", (1, 3)),
            _tensor("bias", (3,)),
            _tensor("output", (1, 3)),
        ),
        nodes=(
            NodeIR("weights_node", "weights", "Constant", (), ("weights",), {}, {}),
            NodeIR("bias_node", "bias", "Constant", (), ("bias",), {}, {}),
            NodeIR(
                "matmul",
                "matmul",
                "MatMul",
                ("features", "weights"),
                ("product",),
                {},
                {},
            ),
            NodeIR(
                "add",
                "add",
                "Add",
                ("product", "bias"),
                ("output",),
                {},
                {},
            ),
        ),
        constants=(
            _constant("weights", (4, 3)),
            _constant("bias", (3,)),
        ),
        metadata={},
    )

    decisions = classify_graph(graph)

    assert decisions[0].support_class is SupportClass.SUPPORTED
    assert decisions[0].inference_action is InferenceAction.REMOVE
    assert decisions[1].support_class is SupportClass.SUPPORTED
    assert decisions[1].inference_action is InferenceAction.REMOVE
    assert decisions[2].support_class is SupportClass.SUPPORTED
    assert decisions[2].inference_action is InferenceAction.LOWER
    assert decisions[3].support_class is SupportClass.SUPPORTED
    assert decisions[3].inference_action is InferenceAction.LOWER
