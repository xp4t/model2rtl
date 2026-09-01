"""Versioned, advisory, graph-derived partition cost estimates."""

from __future__ import annotations

import math
from typing import Dict, Mapping, Optional, Set, Tuple

import numpy as np

from model2rtl.v2.ir import ConstantIR, GraphIR, NodeIR, TensorIR

from .model import CostEstimate, CostThresholds, PartitionIR


DEFAULT_COST_THRESHOLDS = CostThresholds()


def _elements(shape: Tuple[int, ...]) -> int:
    return math.prod(shape)


def _tensor_bytes(tensor: TensorIR) -> int:
    if tensor.shape is None or tensor.dtype is None or any(
        isinstance(item, bool) or not isinstance(item, int) or item <= 0
        for item in tensor.shape
    ):
        raise ValueError("cost model requires static tensor shape and dtype")
    return _elements(tuple(tensor.shape)) * np.dtype(tensor.dtype).itemsize


def _constant_bits(constant: ConstantIR) -> int:
    return _elements(tuple(constant.shape)) * np.dtype(constant.dtype).itemsize * 8


def _dense_parameters(
    node: NodeIR,
    tensor_by_id: Mapping[str, TensorIR],
    constant_by_id: Mapping[str, ConstantIR],
) -> Tuple[int, int, int, Optional[str]]:
    """Return in features, out features, vectors, and bias ID."""
    constants = [item for item in node.inputs if item in constant_by_id]
    dynamic = [item for item in node.inputs if item not in constant_by_id]
    if node.op_type == "Dense":
        weight_id = node.attributes.get("kernel_tensor_id")
        bias_id = node.attributes.get("bias_tensor_id")
    else:
        weight_id = constants[0] if constants else None
        bias_id = constants[1] if node.op_type == "Gemm" and len(constants) > 1 else None
    if not isinstance(weight_id, str) or weight_id not in constant_by_id:
        raise ValueError("selected Dense node has no graph constant weights")
    weight_shape = tuple(constant_by_id[weight_id].shape)
    if len(weight_shape) != 2 or len(dynamic) != 1:
        raise ValueError("selected Dense node is not a static rank-2 pattern")
    trans_b = bool(node.attributes.get("transB", 0)) if node.op_type == "Gemm" else False
    in_features = weight_shape[1] if trans_b else weight_shape[0]
    out_features = weight_shape[0] if trans_b else weight_shape[1]
    input_tensor = tensor_by_id[dynamic[0]]
    if input_tensor.shape is None:
        raise ValueError("selected Dense input shape is not static")
    vectors = _elements(tuple(input_tensor.shape[:-1])) or 1
    return in_features, out_features, vectors, bias_id if isinstance(bias_id, str) else None


def estimate_partition_cost(
    graph: GraphIR, partition: PartitionIR, output_tile: int = 32
) -> CostEstimate:
    """Estimate costs without changing whether the partition is compilable."""
    if isinstance(output_tile, bool) or not isinstance(output_tile, int) or output_tile <= 0:
        raise ValueError("output_tile must be a positive integer")
    graph.validate()
    thresholds = DEFAULT_COST_THRESHOLDS
    if not partition.rtl_node_ids:
        return CostEstimate(
            thresholds.version,
            output_tile,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0.0,
            False,
            (),
        )

    tensor_by_id: Dict[str, TensorIR] = {item.id: item for item in graph.tensors}
    constant_by_id: Dict[str, ConstantIR] = {
        item.tensor_id: item for item in graph.constants
    }
    node_by_id = {item.id: item for item in graph.nodes}
    selected = [node_by_id[item] for item in partition.rtl_node_ids]

    transfer_bytes = sum(
        _tensor_bytes(tensor_by_id[item])
        for item in partition.input_boundary_tensor_ids
        + partition.output_boundary_tensor_ids
    )
    dense_macs = 0
    weight_bits = 0
    bias_bits = 0
    cycles = 0
    dense_count = 0
    counted_biases: Set[str] = set()
    for node in selected:
        if node.op_type not in {"Dense", "Gemm", "MatMul"}:
            continue
        in_features, out_features, vectors, bias_id = _dense_parameters(
            node, tensor_by_id, constant_by_id
        )
        dense_count += 1
        weights = in_features * out_features
        dense_macs += vectors * weights
        weight_bits += weights * 4
        cycles += vectors * in_features * math.ceil(out_features / output_tile)
        if bias_id is not None and bias_id not in counted_biases:
            bias_bits += _constant_bits(constant_by_id[bias_id])
            counted_biases.add(bias_id)

    for node in selected:
        if node.op_type not in {"Add", "BiasAdd"}:
            continue
        for tensor_id in node.inputs:
            if tensor_id in constant_by_id and tensor_id not in counted_biases:
                bias_bits += _constant_bits(constant_by_id[tensor_id])
                counted_biases.add(tensor_id)

    # Transparent/removal/elision nodes allocate no additional activation storage.
    activation_ops = {"Dense", "Gemm", "MatMul", "ReLU", "Relu", "Add", "BiasAdd"}
    activation_bytes = sum(
        _tensor_bytes(tensor_by_id[tensor_id])
        for node in selected
        if node.op_type in activation_ops
        for tensor_id in node.outputs
    )
    parameter_bits = weight_bits + bias_bits
    ratio = dense_macs / transfer_bytes if transfer_bytes else float("inf")
    reasons = []
    if ratio < thresholds.minimum_compute_to_transfer_ratio:
        reasons.append(
            "boundary transfer dominates compute under {} (ratio {:.6g} < {:.6g})".format(
                thresholds.version,
                ratio,
                thresholds.minimum_compute_to_transfer_ratio,
            )
        )
    if dense_count == 1 and dense_macs <= thresholds.trivial_output_layer_max_macs:
        reasons.append(
            "the RTL suffix is only a trivial output layer under {}".format(
                thresholds.version
            )
        )
    return CostEstimate(
        thresholds.version,
        output_tile,
        transfer_bytes,
        dense_macs,
        weight_bits,
        bias_bits,
        parameter_bits,
        activation_bytes,
        cycles,
        ratio,
        bool(reasons),
        tuple(reasons),
    )
