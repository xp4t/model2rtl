"""Immutable records and structural validation for V2 GraphIR."""

from __future__ import annotations

import base64
import binascii
import hashlib
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple

import numpy as np


GRAPH_SCHEMA_VERSION = "model2rtl-graph-v1"


class GraphValidationError(ValueError):
    """A deterministic structural or representation error in GraphIR."""


def _freeze(value: Any) -> object:
    """Detach nested containers so frozen records cannot be mutated indirectly."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _json_value(value: Any, location: str) -> object:
    """Return a JSON-compatible copy or reject framework-specific leakage."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GraphValidationError(
                "{} must contain finite framework-neutral values".format(location)
            )
        return value
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise GraphValidationError(
                    "{} must contain framework-neutral string mapping keys".format(
                        location
                    )
                )
            result[key] = _json_value(item, "{}.{}".format(location, key))
        return result
    if isinstance(value, (list, tuple)):
        return [
            _json_value(item, "{}[{}]".format(location, index))
            for index, item in enumerate(value)
        ]
    raise GraphValidationError(
        "{} contains a non-framework-neutral value of type {}".format(
            location, type(value).__name__
        )
    )


def _require_nonempty_string(value: object, location: str) -> None:
    if not isinstance(value, str) or not value:
        raise GraphValidationError("{} must be a non-empty string".format(location))


def _require_string_tuple(value: object, location: str) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise GraphValidationError(
            "{} must be a tuple of non-empty strings".format(location)
        )


def _require_tensor_shape(shape: object, location: str) -> None:
    if not isinstance(shape, tuple):
        raise GraphValidationError("{} has an invalid shape".format(location))
    for dimension in shape:
        valid_integer = (
            isinstance(dimension, int)
            and not isinstance(dimension, bool)
            and dimension > 0
        )
        valid_symbol = isinstance(dimension, str) and bool(dimension)
        if dimension is not None and not valid_integer and not valid_symbol:
            raise GraphValidationError("{} has an invalid shape".format(location))


def _require_constant_shape(shape: object, location: str) -> int:
    if not isinstance(shape, tuple):
        raise GraphValidationError("{} has an invalid shape".format(location))
    element_count = 1
    for dimension in shape:
        if (
            isinstance(dimension, bool)
            or not isinstance(dimension, int)
            or dimension <= 0
        ):
            raise GraphValidationError("{} has an invalid shape".format(location))
        element_count *= dimension
    return element_count


def _dtype(dtype: object, location: str) -> np.dtype:
    _require_nonempty_string(dtype, location)
    try:
        result = np.dtype(dtype)
    except TypeError as error:
        raise GraphValidationError("{} is not a valid dtype".format(location)) from error
    if result.hasobject or result.fields is not None or result.subdtype is not None:
        raise GraphValidationError("{} is not a fixed-width scalar dtype".format(location))
    return result


def _constant_dtype(dtype: object, location: str) -> np.dtype:
    """Require serialized constants to declare native or little-endian values."""
    result = _dtype(dtype, location)
    if result.byteorder == ">":
        raise GraphValidationError("{} must be little-endian".format(location))
    return result


def _require_mapping(value: object, location: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GraphValidationError("{} must be a mapping".format(location))
    return value


@dataclass(frozen=True)
class TensorIR:
    """A framework-neutral tensor declaration."""

    id: str
    name: str
    shape: Optional[tuple]
    dtype: Optional[str]
    layout: Optional[str] = None
    quantization: Optional[str] = None

    def __post_init__(self) -> None:
        if self.shape is not None:
            object.__setattr__(self, "shape", tuple(self.shape))

    def to_dict(self) -> Mapping[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "shape": None if self.shape is None else list(self.shape),
            "dtype": self.dtype,
            "layout": self.layout,
            "quantization": self.quantization,
        }


@dataclass(frozen=True)
class NodeIR:
    """A framework-neutral operation in importer-provided topological order."""

    id: str
    name: str
    op_type: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    attributes: Mapping[str, object]
    source_location: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "outputs", tuple(self.outputs))
        object.__setattr__(self, "attributes", _freeze(self.attributes))
        object.__setattr__(self, "source_location", _freeze(self.source_location))

    def to_dict(self) -> Mapping[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "op_type": self.op_type,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "attributes": _json_value(self.attributes, "node.attributes"),
            "source_location": _json_value(
                self.source_location, "node.source_location"
            ),
        }


@dataclass(frozen=True)
class ConstantIR:
    """A static tensor payload normalized to canonical little-endian bytes."""

    tensor_id: str
    dtype: str
    shape: Tuple[int, ...]
    little_endian_data_base64: str
    data_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape", tuple(self.shape))

    @classmethod
    def from_values(
        cls,
        tensor_id: str,
        dtype: str,
        shape: Tuple[int, ...],
        values: object,
    ) -> "ConstantIR":
        """Build a constant from values using canonical little-endian storage."""
        dtype_value = _dtype(dtype, "constant dtype")
        shape_value = tuple(shape)
        expected_elements = _require_constant_shape(shape_value, "constant")
        little_dtype = dtype_value.newbyteorder("<")
        try:
            array = np.asarray(values, dtype=little_dtype)
        except (TypeError, ValueError, OverflowError) as error:
            raise GraphValidationError(
                "constant values cannot be represented as {}".format(dtype)
            ) from error
        if array.size != expected_elements:
            raise GraphValidationError(
                "constant value count does not match its shape"
            )
        data = array.reshape(shape_value).tobytes(order="C")
        return cls(
            tensor_id=tensor_id,
            dtype=dtype_value.name,
            shape=shape_value,
            little_endian_data_base64=base64.b64encode(data).decode("ascii"),
            data_sha256=hashlib.sha256(data).hexdigest(),
        )

    def to_dict(self) -> Mapping[str, object]:
        return {
            "tensor_id": self.tensor_id,
            "dtype": self.dtype,
            "shape": list(self.shape),
            "little_endian_data_base64": self.little_endian_data_base64,
            "data_sha256": self.data_sha256,
        }


@dataclass(frozen=True)
class GraphIR:
    """A deterministic, immutable, directed dataflow graph."""

    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    tensors: Tuple[TensorIR, ...]
    nodes: Tuple[NodeIR, ...]
    constants: Tuple[ConstantIR, ...]
    metadata: Mapping[str, object]
    schema_version: str = GRAPH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "outputs", tuple(self.outputs))
        object.__setattr__(self, "tensors", tuple(self.tensors))
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "constants", tuple(self.constants))
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> Mapping[str, object]:
        """Return the JSON-compatible semantic graph document."""
        return {
            "schema_version": self.schema_version,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "tensors": [
                tensor.to_dict() for tensor in sorted(self.tensors, key=lambda item: item.id)
            ],
            "nodes": [node.to_dict() for node in self.nodes],
            "constants": [
                constant.to_dict()
                for constant in sorted(self.constants, key=lambda item: item.tensor_id)
            ],
            "metadata": _json_value(self.metadata, "graph.metadata"),
        }

    def validate(self) -> None:
        """Reject malformed, ambiguous, cyclic, or non-neutral graph data."""
        if self.schema_version != GRAPH_SCHEMA_VERSION:
            raise GraphValidationError(
                "unknown graph schema_version: {!r}".format(self.schema_version)
            )
        _require_string_tuple(self.inputs, "graph.inputs")
        _require_string_tuple(self.outputs, "graph.outputs")
        _require_mapping(self.metadata, "graph.metadata")
        _json_value(self.metadata, "graph.metadata")

        tensor_by_id = {}
        for tensor in self.tensors:
            if not isinstance(tensor, TensorIR):
                raise GraphValidationError("graph tensors must be TensorIR records")
            _require_nonempty_string(tensor.id, "tensor.id")
            if tensor.id in tensor_by_id:
                raise GraphValidationError("duplicate tensor ID: {!r}".format(tensor.id))
            _require_nonempty_string(tensor.name, "tensor.name")
            if tensor.shape is not None:
                _require_tensor_shape(tensor.shape, "tensor {!r}".format(tensor.id))
            if tensor.dtype is not None:
                _dtype(tensor.dtype, "tensor {!r} dtype".format(tensor.id))
            if tensor.layout is not None:
                _require_nonempty_string(tensor.layout, "tensor.layout")
            if tensor.quantization is not None:
                _require_nonempty_string(tensor.quantization, "tensor.quantization")
            tensor_by_id[tensor.id] = tensor

        node_by_id = {}
        for node in self.nodes:
            if not isinstance(node, NodeIR):
                raise GraphValidationError("graph nodes must be NodeIR records")
            _require_nonempty_string(node.id, "node.id")
            if node.id in node_by_id:
                raise GraphValidationError("duplicate node ID: {!r}".format(node.id))
            _require_nonempty_string(node.name, "node.name")
            _require_nonempty_string(node.op_type, "node.op_type")
            _require_string_tuple(node.inputs, "node.inputs")
            _require_string_tuple(node.outputs, "node.outputs")
            _require_mapping(
                node.attributes, "node {!r}.attributes".format(node.id)
            )
            _require_mapping(
                node.source_location, "node {!r}.source_location".format(node.id)
            )
            _json_value(node.attributes, "node {!r}.attributes".format(node.id))
            _json_value(
                node.source_location, "node {!r}.source_location".format(node.id)
            )
            node_by_id[node.id] = node

        if len(set(self.inputs)) != len(self.inputs):
            raise GraphValidationError("duplicate graph input tensor ID")
        if len(set(self.outputs)) != len(self.outputs):
            raise GraphValidationError("duplicate graph output tensor ID")
        for tensor_id in self.inputs:
            if tensor_id not in tensor_by_id:
                raise GraphValidationError(
                    "graph input tensor {!r} is not declared".format(tensor_id)
                )

        producer = {tensor_id: ("input", None) for tensor_id in self.inputs}
        constant_ids = set()
        for constant in self.constants:
            if not isinstance(constant, ConstantIR):
                raise GraphValidationError(
                    "graph constants must be ConstantIR records"
                )
            _require_nonempty_string(constant.tensor_id, "constant.tensor_id")
            if constant.tensor_id in constant_ids:
                raise GraphValidationError(
                    "duplicate constant tensor ID: {!r}".format(constant.tensor_id)
                )
            constant_ids.add(constant.tensor_id)
            tensor = tensor_by_id.get(constant.tensor_id)
            if tensor is None:
                raise GraphValidationError(
                    "constant tensor {!r} is not declared".format(constant.tensor_id)
                )
            if tensor.shape is None or tensor.dtype is None:
                raise GraphValidationError(
                    "constant {!r} requires known tensor shape and dtype".format(
                        constant.tensor_id
                    )
                )
            constant_dtype = _constant_dtype(
                constant.dtype, "constant {!r} dtype".format(constant.tensor_id)
            )
            tensor_dtype = _dtype(
                tensor.dtype, "tensor {!r} dtype".format(tensor.id)
            )
            if constant_dtype != tensor_dtype:
                raise GraphValidationError(
                    "constant {!r} dtype does not match its tensor".format(
                        constant.tensor_id
                    )
                )
            element_count = _require_constant_shape(
                constant.shape, "constant {!r}".format(constant.tensor_id)
            )
            if tuple(constant.shape) != tuple(tensor.shape):
                raise GraphValidationError(
                    "constant {!r} shape does not match its tensor".format(
                        constant.tensor_id
                    )
                )
            try:
                data = base64.b64decode(
                    constant.little_endian_data_base64, validate=True
                )
            except (binascii.Error, ValueError, TypeError) as error:
                raise GraphValidationError(
                    "constant {!r} has malformed base64 data".format(
                        constant.tensor_id
                    )
                ) from error
            expected_bytes = element_count * constant_dtype.itemsize
            if len(data) != expected_bytes:
                raise GraphValidationError(
                    "constant {!r} byte count is {}, expected {}".format(
                        constant.tensor_id, len(data), expected_bytes
                    )
                )
            if hashlib.sha256(data).hexdigest() != constant.data_sha256:
                raise GraphValidationError(
                    "constant {!r} data SHA-256 mismatch".format(
                        constant.tensor_id
                    )
                )
            if constant.tensor_id in producer:
                raise GraphValidationError(
                    "multiple producers for tensor {!r}".format(constant.tensor_id)
                )
            producer[constant.tensor_id] = ("constant", None)

        for index, node in enumerate(self.nodes):
            for tensor_id in node.outputs:
                if tensor_id not in tensor_by_id:
                    raise GraphValidationError(
                        "node {!r} output tensor {!r} is not declared".format(
                            node.id, tensor_id
                        )
                    )
                existing_producer = producer.get(tensor_id)
                constant_payload_owner = (
                    existing_producer is not None
                    and existing_producer[0] == "constant"
                    and node.op_type == "Constant"
                    and not node.inputs
                    and len(node.outputs) == 1
                )
                if existing_producer is not None and not constant_payload_owner:
                    raise GraphValidationError(
                        "multiple producers for tensor {!r}".format(tensor_id)
                    )
                producer[tensor_id] = ("node", index)

        dependencies = [set() for _node in self.nodes]
        consumers = [set() for _node in self.nodes]
        for consumer_index, node in enumerate(self.nodes):
            for tensor_id in node.inputs:
                source = producer.get(tensor_id)
                if source is None:
                    raise GraphValidationError(
                        "missing producer for tensor {!r} used by node {!r}".format(
                            tensor_id, node.id
                        )
                    )
                if tensor_id not in tensor_by_id:
                    raise GraphValidationError(
                        "missing producer declaration for tensor {!r}".format(tensor_id)
                    )
                if source[0] == "node":
                    producer_index = source[1]
                    assert producer_index is not None
                    dependencies[consumer_index].add(producer_index)
                    consumers[producer_index].add(consumer_index)

        for tensor_id in self.outputs:
            if tensor_id not in tensor_by_id or tensor_id not in producer:
                raise GraphValidationError(
                    "dangling graph output tensor {!r}".format(tensor_id)
                )

        indegree = [len(items) for items in dependencies]
        ready = [index for index, degree in enumerate(indegree) if degree == 0]
        visited = 0
        while ready:
            current = ready.pop()
            visited += 1
            for consumer_index in consumers[current]:
                indegree[consumer_index] -= 1
                if indegree[consumer_index] == 0:
                    ready.append(consumer_index)
        if visited != len(self.nodes):
            raise GraphValidationError("graph contains a cycle")

        for consumer_index, producer_indexes in enumerate(dependencies):
            if any(index >= consumer_index for index in producer_indexes):
                raise GraphValidationError(
                    "nodes are not in importer-provided topological order"
                )
