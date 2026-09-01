"""Conservative largest-linear-Dense-suffix partitioning."""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Sequence, Set, Tuple

import numpy as np

from model2rtl.v2.capability import (
    CapabilityDecision,
    InferenceAction,
    SupportClass,
)
from model2rtl.v2.ir import GraphIR, NodeIR, TensorIR
from model2rtl.v2.model_contract import ModelContract

from .model import ExclusionReason, PartitionIR, TransformationRecord


_DENSE_OPS = {"Dense", "Gemm", "MatMul"}
_REGION_OPS = _DENSE_OPS | {
    "BiasAdd",
    "Add",
    "ReLU",
    "Relu",
    "Flatten",
    "Reshape",
    "Dropout",
    "Softmax",
}
_REGION_ACTIONS = {
    InferenceAction.LOWER,
    InferenceAction.REMOVE,
    InferenceAction.ELIDE,
}
_SUPPORTED_BOUNDARY_LAYOUTS = {"NC", "NCHW", "NHWC"}


def _maps(graph: GraphIR) -> Tuple[Mapping[str, NodeIR], Set[str]]:
    producers: Dict[str, NodeIR] = {}
    for node in graph.nodes:
        for tensor_id in node.outputs:
            producers[tensor_id] = node
    return producers, {item.tensor_id for item in graph.constants}


def _live_node_ids(
    outputs: Sequence[str],
    producer_by_tensor: Mapping[str, NodeIR],
    constant_ids: Set[str],
) -> Set[str]:
    live: Set[str] = set()
    pending = list(outputs)
    while pending:
        tensor_id = pending.pop()
        node = producer_by_tensor.get(tensor_id)
        if node is None or node.id in live:
            continue
        live.add(node.id)
        pending.extend(item for item in node.inputs if item not in constant_ids)
    return live


def _dynamic_inputs(node: NodeIR, constant_ids: Set[str]) -> Tuple[str, ...]:
    return tuple(item for item in node.inputs if item not in constant_ids)


def _is_representable_boundary(tensor: Optional[TensorIR]) -> bool:
    if tensor is None or tensor.dtype is None:
        return False
    try:
        dtype = np.dtype(tensor.dtype)
    except (TypeError, ValueError):
        return False
    return (
        dtype.kind in {"i", "u", "f"}
        and dtype.itemsize > 0
        and tensor.layout in _SUPPORTED_BOUNDARY_LAYOUTS
        and tensor.shape is not None
        and all(
            isinstance(item, int) and not isinstance(item, bool) and item > 0
            for item in tensor.shape
        )
    )


def _empty_partition(
    graph: GraphIR,
    mode: str,
    selected_output: str,
    live_ids: Set[str],
    reason: str,
    *,
    software_prefix: bool,
    decision_by_id: Mapping[str, CapabilityDecision],
) -> PartitionIR:
    prefix_ids = tuple(
        node.id for node in graph.nodes if software_prefix and node.id in live_ids
    )
    exclusions = []
    for node in graph.nodes:
        decision = decision_by_id[node.id]
        if node.id not in live_ids:
            exclusion = "node is not live for the selected output"
        elif decision.inference_action is InferenceAction.REJECT:
            exclusion = "operator rejected: {}".format(decision.reason)
        elif software_prefix:
            exclusion = "node remains in the software prefix: {}".format(
                decision.reason
            )
        else:
            exclusion = reason
        exclusions.append(ExclusionReason(node.id, exclusion))
    return PartitionIR(
        mode,
        selected_output,
        prefix_ids,
        (),
        (),
        (),
        (),
        (),
        tuple(exclusions),
        (reason,),
    )


def _transformation(
    node: NodeIR, decision: CapabilityDecision
) -> Optional[TransformationRecord]:
    if decision.inference_action in {InferenceAction.REMOVE, InferenceAction.ELIDE}:
        return TransformationRecord(
            node.id, decision.inference_action.value, decision.reason
        )
    if node.op_type in {"Flatten", "Reshape"}:
        return TransformationRecord(node.id, "transparent", decision.reason)
    if node.op_type in {"Gemm", "MatMul", "BiasAdd", "Add"}:
        return TransformationRecord(node.id, "normalize", decision.reason)
    return None


def partition_graph(
    graph: GraphIR,
    decisions: Sequence[CapabilityDecision],
    contract: Optional[ModelContract] = None,
) -> PartitionIR:
    """Select one conservative Dense/ReLU suffix with explicit handoff records."""
    graph.validate()
    expected_ids = tuple(node.id for node in graph.nodes)
    actual_ids = tuple(item.node_id for item in decisions)
    if actual_ids != expected_ids:
        raise ValueError(
            "capability decisions must contain exactly one ordered decision per graph node"
        )
    decision_by_id = {item.node_id: item for item in decisions}
    producer_by_tensor, constant_ids = _maps(graph)
    live_ids = _live_node_ids(graph.outputs, producer_by_tensor, constant_ids)
    selected_output = graph.outputs[0] if graph.outputs else ""

    if len(graph.outputs) != 1:
        return _empty_partition(
            graph,
            "compile_unavailable",
            selected_output,
            live_ids,
            "partition requires exactly one selected output",
            software_prefix=False,
            decision_by_id=decision_by_id,
        )

    unsupported = [
        node.id
        for node in graph.nodes
        if node.id in live_ids
        and decision_by_id[node.id].support_class is SupportClass.UNSUPPORTED
    ]
    if unsupported:
        return _empty_partition(
            graph,
            "compile_unavailable",
            selected_output,
            live_ids,
            "live unsupported node {} blocks compilation".format(unsupported[0]),
            software_prefix=False,
            decision_by_id=decision_by_id,
        )

    anchor_tensor = selected_output
    postfix_ids: Tuple[str, ...] = ()
    output_producer = producer_by_tensor.get(anchor_tensor)
    if output_producer is not None:
        output_decision = decision_by_id[output_producer.id]
        dynamic = _dynamic_inputs(output_producer, constant_ids)
        if (
            output_producer.op_type == "Softmax"
            and output_decision.inference_action is InferenceAction.SOFTWARE
            and len(dynamic) == 1
            and len(output_producer.outputs) == 1
        ):
            postfix_ids = (output_producer.id,)
            anchor_tensor = dynamic[0]

    candidate_reversed = []
    current_tensor = anchor_tensor
    while True:
        node = producer_by_tensor.get(current_tensor)
        if node is None or node.id not in live_ids or node.id in postfix_ids:
            break
        decision = decision_by_id[node.id]
        dynamic = _dynamic_inputs(node, constant_ids)
        if (
            node.op_type not in _REGION_OPS
            or decision.inference_action not in _REGION_ACTIONS
            or len(dynamic) != 1
            or len(node.outputs) != 1
            or node.outputs[0] != current_tensor
        ):
            break
        candidate_reversed.append(node.id)
        current_tensor = dynamic[0]

    candidate_set = set(candidate_reversed)
    if not any(
        node.id in candidate_set and node.op_type in _DENSE_OPS
        for node in graph.nodes
    ):
        return _empty_partition(
            graph,
            "analysis_only",
            selected_output,
            live_ids,
            "no safe linear Dense suffix reaches the selected output",
            software_prefix=True,
            decision_by_id=decision_by_id,
        )

    rtl_ids = tuple(node.id for node in graph.nodes if node.id in candidate_set)
    prefix_ids = tuple(
        node.id
        for node in graph.nodes
        if node.id in live_ids and node.id not in candidate_set and node.id not in postfix_ids
    )
    input_boundary = current_tensor
    output_boundary = anchor_tensor

    # Removed/elided terminal identities have no materialized hardware output.
    while True:
        node = producer_by_tensor.get(output_boundary)
        if node is None or node.id not in candidate_set:
            break
        decision = decision_by_id[node.id]
        if decision.inference_action not in {
            InferenceAction.REMOVE,
            InferenceAction.ELIDE,
        }:
            break
        dynamic = _dynamic_inputs(node, constant_ids)
        if len(dynamic) != 1:
            break
        output_boundary = dynamic[0]

    tensor_by_id = {item.id: item for item in graph.tensors}
    if not _is_representable_boundary(tensor_by_id.get(input_boundary)) or not _is_representable_boundary(
        tensor_by_id.get(output_boundary)
    ):
        return _empty_partition(
            graph,
            "compile_unavailable",
            selected_output,
            live_ids,
            "RTL suffix requires one static representable input and output boundary",
            software_prefix=False,
            decision_by_id=decision_by_id,
        )

    transformations = tuple(
        record
        for node in graph.nodes
        if node.id in candidate_set
        for record in (_transformation(node, decision_by_id[node.id]),)
        if record is not None
    )
    exclusions = []
    for node in graph.nodes:
        if node.id in candidate_set:
            continue
        decision = decision_by_id[node.id]
        if node.id in prefix_ids:
            reason = "node remains in the software prefix: {}".format(decision.reason)
        elif node.id in postfix_ids:
            reason = "node remains in the software postfix: {}".format(decision.reason)
        else:
            reason = "node is not live for the selected output"
        exclusions.append(ExclusionReason(node.id, reason))

    mode = "full_rtl" if not prefix_ids and not postfix_ids else "hybrid"
    return PartitionIR(
        mode,
        selected_output,
        prefix_ids,
        rtl_ids,
        postfix_ids,
        (input_boundary,),
        (output_boundary,),
        transformations,
        tuple(exclusions),
        (),
    )
