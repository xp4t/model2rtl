"""Single source of truth for V2 operator capability decisions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Dict, Mapping, Optional, Tuple

from model2rtl.v2.ir import ConstantIR, GraphIR, NodeIR, TensorIR
from model2rtl.v2.model_contract import ModelContract

from .model import (
    CapabilityDecision,
    CapabilityEntry,
    InferenceAction,
    SupportClass,
)


@dataclass(frozen=True)
class _Context:
    tensor_by_id: Mapping[str, TensorIR]
    constant_by_id: Mapping[str, ConstantIR]
    producer_by_tensor: Mapping[str, NodeIR]
    contract: Optional[ModelContract]


@dataclass(frozen=True)
class _Validation:
    reason: str
    support_class: Optional[SupportClass] = None
    inference_action: Optional[InferenceAction] = None


Validator = Callable[[NodeIR, _Context], _Validation]


def _entry(
    op_type: str,
    support_class: SupportClass,
    inference_action: InferenceAction,
    validator_key: str,
    shape_rule_key: str,
    reason: str,
    roadmap_label: str,
    *,
    hooks: bool = False,
) -> CapabilityEntry:
    return CapabilityEntry(
        op_type,
        support_class,
        inference_action,
        validator_key,
        shape_rule_key,
        "int4_symmetric_per_output" if hooks else None,
        "dense_chain_v1" if hooks else None,
        "integer_oracle_v1" if hooks else None,
        reason,
        roadmap_label,
    )


def _supported(
    op_type: str, validator: str, shape_rule: str, reason: str
) -> CapabilityEntry:
    return _entry(
        op_type,
        SupportClass.SUPPORTED,
        InferenceAction.LOWER,
        validator,
        shape_rule,
        reason,
        "dense_v1",
        hooks=True,
    )


def _software(
    op_type: str, reason: str, roadmap: str, validator: str = "software"
) -> CapabilityEntry:
    return _entry(
        op_type,
        SupportClass.SOFTWARE_FALLBACK,
        InferenceAction.SOFTWARE,
        validator,
        "software_shape_preserved",
        reason,
        roadmap,
    )


_SUPPORTED_ENTRIES = (
    CapabilityEntry(
        "Constant",
        SupportClass.SUPPORTED,
        InferenceAction.REMOVE,
        "constant",
        "static_constant_payload",
        "static_constant_v1",
        "constant_payload_v1",
        "constant_payload_v1",
        "materialized Constant is a static tensor payload",
        "onnx_constant",
    ),
    _supported("Dense", "dense", "dense_static_rank2", "static Dense lowers"),
    _supported("Gemm", "gemm", "dense_static_rank2", "validated Gemm normalizes to Dense"),
    _supported("MatMul", "matmul", "dense_static_rank2", "constant MatMul normalizes to Dense"),
    _supported("BiasAdd", "bias_add", "static_bias_broadcast", "exact bias add fuses"),
    _supported("ReLU", "relu", "shape_preserving", "ReLU lowers"),
    _supported("Relu", "relu", "shape_preserving", "ReLU lowers"),
    _supported("Flatten", "shape_noop", "static_element_order", "static Flatten is transparent"),
    _supported("Reshape", "shape_noop", "static_element_order", "static Reshape is transparent"),
    _supported("Dropout", "dropout", "shape_preserving", "inference identity is removable"),
)

_SOFTWARE_ENTRIES = (
    _software("Softmax", "Softmax requires software unless argmax-elidable", "softmax_rtl", "softmax"),
    _software("Conv2D", "convolution remains in software", "conv_rtl"),
    _software("Conv", "convolution remains in software", "conv_rtl"),
    _software("MaxPooling2D", "pooling remains in software", "pool_rtl"),
    _software("AveragePooling2D", "pooling remains in software", "pool_rtl"),
    _software("GlobalAveragePooling2D", "pooling remains in software", "pool_rtl"),
    _software("MaxPool", "pooling remains in software", "pool_rtl"),
    _software("AveragePool", "pooling remains in software", "pool_rtl"),
    _software("GlobalAveragePool", "pooling remains in software", "pool_rtl"),
    _software("BatchNormalization", "batch normalization remains in software", "batchnorm_fold"),
    _software("BatchNorm", "batch normalization remains in software", "batchnorm_fold"),
    _entry(
        "Add",
        SupportClass.SOFTWARE_FALLBACK,
        InferenceAction.SOFTWARE,
        "add",
        "static_bias_broadcast",
        "Add remains in software unless it is an exact bias pattern",
        "elementwise_rtl",
        hooks=True,
    ),
    _software("Concat", "concatenation remains in software", "concat_rtl"),
    _software("Concatenate", "concatenation remains in software", "concat_rtl"),
    _software("Attention", "attention remains in software", "attention_rtl"),
    _software("MultiHeadAttention", "attention remains in software", "attention_rtl"),
    _software("LSTM", "recurrent computation remains in software", "recurrent_rtl"),
    _software("Sigmoid", "Sigmoid remains in software", "activation_rtl"),
    _software("Tanh", "Tanh remains in software", "activation_rtl"),
    _software("Activation", "non-ReLU activation remains in software", "activation_rtl"),
)

CAPABILITY_REGISTRY: Mapping[str, CapabilityEntry] = MappingProxyType(
    {entry.op_type: entry for entry in _SUPPORTED_ENTRIES + _SOFTWARE_ENTRIES}
)

_STANDARD_ONNX_DOMAINS = {"", "ai.onnx"}


def _shape(context: _Context, tensor_id: str) -> Optional[Tuple[int, ...]]:
    tensor = context.tensor_by_id.get(tensor_id)
    if tensor is None or tensor.shape is None:
        return None
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0
        for item in tensor.shape
    ):
        return None
    return tuple(tensor.shape)


def _dynamic_inputs(node: NodeIR, context: _Context) -> Tuple[str, ...]:
    return tuple(item for item in node.inputs if item not in context.constant_by_id)


def _constant_shape(context: _Context, tensor_id: object) -> Optional[Tuple[int, ...]]:
    if not isinstance(tensor_id, str) or tensor_id not in context.constant_by_id:
        return None
    return tuple(context.constant_by_id[tensor_id].shape)


def _fallback(reason: str) -> _Validation:
    return _Validation(
        reason, SupportClass.SOFTWARE_FALLBACK, InferenceAction.SOFTWARE
    )


def _validate_dense(node: NodeIR, context: _Context) -> _Validation:
    dynamic = _dynamic_inputs(node, context)
    input_shape = _shape(context, dynamic[0]) if len(dynamic) == 1 else None
    output_shape = _shape(context, node.outputs[0]) if len(node.outputs) == 1 else None
    kernel_shape = _constant_shape(context, node.attributes.get("kernel_tensor_id"))
    if input_shape is None or output_shape is None or kernel_shape is None:
        return _fallback("Dense weights and dimensions must be static")
    if (
        len(input_shape) < 2
        or len(output_shape) < 2
        or len(kernel_shape) != 2
        or input_shape[-1] != kernel_shape[0]
        or output_shape[-1] != kernel_shape[1]
    ):
        return _fallback("Dense dimensions do not match its rank-2 kernel")
    bias_id = node.attributes.get("bias_tensor_id")
    if bias_id is not None and _constant_shape(context, bias_id) != (kernel_shape[1],):
        return _fallback("Dense bias must be a static output-width vector")
    return _Validation("static Dense weights, bias, and dimensions validated")


def _validate_constant(node: NodeIR, context: _Context) -> _Validation:
    if node.inputs or len(node.outputs) != 1 or node.outputs[0] not in context.constant_by_id:
        return _Validation(
            "Constant requires one representable materialized static output",
            SupportClass.UNSUPPORTED,
            InferenceAction.REJECT,
        )
    return _Validation(
        "Constant is represented by its static tensor payload",
        inference_action=InferenceAction.REMOVE,
    )


def _constant_weight_pattern(
    node: NodeIR, context: _Context, *, gemm: bool
) -> _Validation:
    expected_arities = {2, 3} if gemm else {2}
    if len(node.inputs) not in expected_arities or len(node.outputs) != 1:
        return _fallback("operator requires dynamic A, static rank-2 B, and one output")
    data_id, weight_id = node.inputs[:2]
    if data_id in context.constant_by_id or weight_id not in context.constant_by_id:
        return _fallback("operator requires dynamic data operand A and static weight operand B")
    if gemm and len(node.inputs) == 3 and node.inputs[2] not in context.constant_by_id:
        return _fallback("Gemm bias operand C must be static")
    if gemm:
        alpha = node.attributes.get("alpha", 1.0)
        beta = node.attributes.get("beta", 1.0)
        trans_a = node.attributes.get("transA", 0)
        trans_b = node.attributes.get("transB", 0)
        valid_scale = lambda value: (
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value))
            and float(value) == 1.0
        )
        if (
            not valid_scale(alpha)
            or not valid_scale(beta)
            or type(trans_a) is not int
            or trans_a != 0
            or type(trans_b) is not int
            or trans_b not in {0, 1}
        ):
            return _fallback("Gemm alpha, beta, transA, or transB semantics are invalid")
    input_shape = _shape(context, data_id)
    output_shape = _shape(context, node.outputs[0])
    weight_shape = tuple(context.constant_by_id[weight_id].shape)
    if input_shape is None or output_shape is None or len(weight_shape) != 2:
        return _fallback("weight and activation dimensions must be static")
    trans_b = bool(node.attributes.get("transB", 0)) if gemm else False
    in_features = weight_shape[1] if trans_b else weight_shape[0]
    out_features = weight_shape[0] if trans_b else weight_shape[1]
    if input_shape[-1] != in_features or output_shape[-1] != out_features:
        return _fallback("activation dimensions do not match constant weights")
    if gemm and len(node.inputs) == 3 and tuple(context.constant_by_id[node.inputs[2]].shape) not in {
        (out_features,),
        (1, out_features),
    }:
        return _fallback("Gemm bias is not an exact output-width broadcast")
    return _Validation("constant-weight semantics validated as Dense")


def _validate_gemm(node: NodeIR, context: _Context) -> _Validation:
    return _constant_weight_pattern(node, context, gemm=True)


def _validate_matmul(node: NodeIR, context: _Context) -> _Validation:
    return _constant_weight_pattern(node, context, gemm=False)


def _validate_relu(node: NodeIR, context: _Context) -> _Validation:
    dynamic = _dynamic_inputs(node, context)
    if (
        len(dynamic) != 1
        or len(node.outputs) != 1
        or _shape(context, dynamic[0]) is None
        or _shape(context, dynamic[0]) != _shape(context, node.outputs[0])
    ):
        return _fallback("ReLU requires one statically shape-preserving edge")
    return _Validation("shape-preserving ReLU validated")


def _validate_shape_noop(node: NodeIR, context: _Context) -> _Validation:
    dynamic = _dynamic_inputs(node, context)
    source = _shape(context, dynamic[0]) if len(dynamic) == 1 else None
    target = _shape(context, node.outputs[0]) if len(node.outputs) == 1 else None
    if source is None or target is None or math.prod(source) != math.prod(target):
        return _fallback("shape operation is not a proven static hardware no-op")
    return _Validation("static element-order-preserving shape operation is transparent")


def _validate_dropout(node: NodeIR, context: _Context) -> _Validation:
    if node.attributes.get("inference_identity_proven") is not True:
        return _fallback("Dropout inference identity is not proven")
    dynamic = _dynamic_inputs(node, context)
    if len(dynamic) != 1 or len(node.outputs) != 1:
        return _fallback("Dropout identity requires one data input and one output")
    input_tensor = context.tensor_by_id.get(dynamic[0])
    output_tensor = context.tensor_by_id.get(node.outputs[0])
    if (
        input_tensor is None
        or output_tensor is None
        or input_tensor.shape is None
        or input_tensor.shape != output_tensor.shape
        or input_tensor.dtype is None
        or input_tensor.dtype != output_tensor.dtype
    ):
        return _fallback("Dropout identity requires equal input/output shape and dtype")
    return _Validation(
        "Dropout is proven to be an inference identity",
        inference_action=InferenceAction.REMOVE,
    )


def _validate_softmax(node: NodeIR, context: _Context) -> _Validation:
    output = None if context.contract is None else context.contract.output
    if len(node.inputs) != 1 or len(node.outputs) != 1:
        return _Validation("Softmax requires exactly one input and one output")
    input_tensor = context.tensor_by_id.get(node.inputs[0])
    output_tensor = context.tensor_by_id.get(node.outputs[0])
    if (
        input_tensor is None
        or output_tensor is None
        or input_tensor.shape is None
        or input_tensor.shape != output_tensor.shape
        or input_tensor.dtype is None
        or input_tensor.dtype != output_tensor.dtype
    ):
        return _Validation("Softmax input and output shape and dtype must match")
    rank = len(input_tensor.shape)
    if "axis" in node.attributes:
        axis = node.attributes["axis"]
    elif node.source_location.get("frontend") == "onnx" or "domain" in node.source_location:
        opset_version = node.source_location.get("opset_version")
        if (
            isinstance(opset_version, bool)
            or not isinstance(opset_version, int)
            or opset_version <= 0
        ):
            return _Validation(
                "Softmax default axis requires a valid per-node ONNX opset version"
            )
        axis = 1 if opset_version < 13 else -1
    else:
        axis = -1
    if isinstance(axis, bool) or not isinstance(axis, int):
        return _Validation("Softmax class axis must be the last axis")
    normalized_axis = axis + rank if axis < 0 else axis
    if rank == 0 or normalized_axis != rank - 1:
        return _Validation("Softmax class axis must be the last axis")
    if (
        output is not None
        and output.interpretation == "classification"
        and output.decision == "argmax"
    ):
        return _Validation(
            "Softmax is elided under the exact classification argmax contract",
            inference_action=InferenceAction.ELIDE,
        )
    return _Validation("Softmax probability semantics are preserved in software")


def _bias_pattern(node: NodeIR, context: _Context) -> bool:
    dynamic = _dynamic_inputs(node, context)
    constants = [item for item in node.inputs if item in context.constant_by_id]
    if len(dynamic) != 1 or len(constants) != 1 or len(node.outputs) != 1:
        return False
    producer = context.producer_by_tensor.get(dynamic[0])
    output_shape = _shape(context, node.outputs[0])
    return (
        producer is not None
        and producer.op_type in {"Dense", "Gemm", "MatMul"}
        and output_shape is not None
        and tuple(context.constant_by_id[constants[0]].shape) == (output_shape[-1],)
    )


def _validate_bias_add(node: NodeIR, context: _Context) -> _Validation:
    if not _bias_pattern(node, context):
        return _fallback("BiasAdd is not an exact static Dense bias broadcast")
    return _Validation("exact static Dense bias broadcast validated")


def _validate_add(node: NodeIR, context: _Context) -> _Validation:
    if not _bias_pattern(node, context):
        return _Validation("Add is preserved because it is not a Dense bias pattern")
    return _Validation(
        "Add is an exact static Dense bias broadcast",
        SupportClass.SUPPORTED,
        InferenceAction.LOWER,
    )


def _validate_software(node: NodeIR, context: _Context) -> _Validation:
    return _Validation("operator semantics are explicitly preserved in software")


_VALIDATORS: Mapping[str, Validator] = MappingProxyType(
    {
        "constant": _validate_constant,
        "dense": _validate_dense,
        "gemm": _validate_gemm,
        "matmul": _validate_matmul,
        "relu": _validate_relu,
        "shape_noop": _validate_shape_noop,
        "dropout": _validate_dropout,
        "softmax": _validate_softmax,
        "bias_add": _validate_bias_add,
        "add": _validate_add,
        "software": _validate_software,
    }
)


def _unknown_entry(op_type: str) -> CapabilityEntry:
    control_flow = op_type in {"If", "Loop", "Scan"}
    return _entry(
        op_type,
        SupportClass.UNSUPPORTED,
        InferenceAction.REJECT,
        "reject_unknown",
        "unknown_shape_semantics",
        (
            "control-flow operator {!r} cannot guarantee a safe handoff".format(op_type)
            if control_flow
            else "unknown operator {!r} is visible but rejected".format(op_type)
        ),
        "control_flow" if control_flow else "unknown_operator",
    )


def _nonstandard_onnx_domain_entry(node: NodeIR) -> Optional[CapabilityEntry]:
    if "domain" not in node.source_location:
        return None
    domain = node.source_location.get("domain")
    if isinstance(domain, str) and domain in _STANDARD_ONNX_DOMAINS:
        return None
    return _entry(
        node.op_type,
        SupportClass.UNSUPPORTED,
        InferenceAction.REJECT,
        "reject_onnx_domain",
        "unknown_domain_semantics",
        "ONNX domain {!r} cannot use the standard {!r} capability".format(
            domain, node.op_type
        ),
        "onnx_custom_domain",
    )


def _make_context(graph: GraphIR, contract: Optional[ModelContract]) -> _Context:
    producers: Dict[str, NodeIR] = {}
    for node in graph.nodes:
        for tensor_id in node.outputs:
            producers[tensor_id] = node
    return _Context(
        MappingProxyType({item.id: item for item in graph.tensors}),
        MappingProxyType({item.tensor_id: item for item in graph.constants}),
        MappingProxyType(producers),
        contract,
    )


def classify_graph(
    graph: GraphIR, contract: Optional[ModelContract] = None
) -> Tuple[CapabilityDecision, ...]:
    """Return one deterministic central-registry decision per source node."""
    graph.validate()
    context = _make_context(graph, contract)
    decisions = []
    for node in graph.nodes:
        entry = (
            _nonstandard_onnx_domain_entry(node)
            or CAPABILITY_REGISTRY.get(node.op_type)
            or _unknown_entry(node.op_type)
        )
        validation = (
            _Validation(entry.reason)
            if entry.support_class is SupportClass.UNSUPPORTED
            else _VALIDATORS[entry.validator_key](node, context)
        )
        decisions.append(
            CapabilityDecision(
                node.id,
                node.op_type,
                validation.support_class or entry.support_class,
                validation.inference_action or entry.inference_action,
                validation.reason,
                entry.validator_key,
                entry.shape_rule_key,
                entry.quantization_rule_key,
                entry.lowering_rule_key,
                entry.golden_rule_key,
                entry.roadmap_label,
            )
        )
    return tuple(decisions)
