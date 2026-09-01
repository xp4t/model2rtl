"""Read-only optional ONNX import into framework-neutral GraphIR."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import onnx
from onnx import numpy_helper

from model2rtl.v2.ir import ConstantIR, GraphIR, NodeIR, TensorIR

from .base import ImportReport, ImportResult, ImporterError, infer_onnx_layout


TensorSpec = Tuple[Optional[tuple], Optional[str]]


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frontend_error(stage: str, path: Path, error: Exception) -> ImporterError:
    return ImporterError(
        "ONNX frontend failed during {} for {!s}: {}: {}".format(
            stage, path, type(error).__name__, error
        )
    )


def _dtype_name(element_type: int, location: str) -> str:
    try:
        dtype = np.dtype(onnx.helper.tensor_dtype_to_np_dtype(element_type))
    except (KeyError, TypeError, ValueError) as error:
        raise ImporterError(
            "ONNX frontend cannot represent {} element type {}".format(
                location, element_type
            )
        ) from error
    if dtype.hasobject or dtype.fields is not None or dtype.subdtype is not None:
        raise ImporterError(
            "ONNX frontend cannot represent {} dtype {}".format(location, dtype)
        )
    return dtype.name


def _shape(value_info: object, location: str) -> Optional[tuple]:
    tensor_type = value_info.type.tensor_type
    if not tensor_type.HasField("shape"):
        return None
    dimensions = []
    for index, dimension in enumerate(tensor_type.shape.dim):
        if dimension.HasField("dim_value"):
            value = int(dimension.dim_value)
            if value <= 0:
                raise ImporterError(
                    "ONNX frontend cannot represent {} dimension {} of size {}".format(
                        location, index, value
                    )
                )
            dimensions.append(value)
        elif dimension.HasField("dim_param") and dimension.dim_param:
            dimensions.append(str(dimension.dim_param))
        else:
            dimensions.append(None)
    return tuple(dimensions)


def _value_info_spec(value_info: object) -> TensorSpec:
    name = str(value_info.name)
    if not name:
        raise ImporterError("ONNX graph contains an unnamed value declaration")
    tensor_type = value_info.type.tensor_type
    if not value_info.type.HasField("tensor_type") or not tensor_type.elem_type:
        raise ImporterError(
            "ONNX frontend cannot represent value {!r} without a tensor element type".format(
                name
            )
        )
    return _shape(value_info, "value {!r}".format(name)), _dtype_name(
        int(tensor_type.elem_type), "value {!r}".format(name)
    )


def _constant_snapshot(array_value: object, location: str) -> Mapping[str, object]:
    array = np.asarray(array_value)
    constant = ConstantIR.from_values(
        tensor_id="attribute",
        dtype=array.dtype.name,
        shape=tuple(int(item) for item in array.shape),
        values=array,
    )
    return {
        "dtype": constant.dtype,
        "shape": list(constant.shape),
        "little_endian_data_base64": constant.little_endian_data_base64,
        "data_sha256": constant.data_sha256,
        "source_location": location,
    }


def _sparse_array(sparse_tensor: object) -> np.ndarray:
    shape = tuple(int(item) for item in sparse_tensor.dims)
    if any(item <= 0 for item in shape):
        raise ImporterError("ONNX sparse initializer has an unsupported empty shape")
    values = np.asarray(numpy_helper.to_array(sparse_tensor.values))
    indices = np.asarray(numpy_helper.to_array(sparse_tensor.indices))
    if not np.issubdtype(indices.dtype, np.integer):
        raise ImporterError("ONNX sparse initializer indices must be integers")
    dense = np.zeros(shape, dtype=values.dtype)
    try:
        if indices.ndim == 1:
            if indices.size != values.size:
                raise ValueError("linear index count does not match value count")
            dense.reshape(-1)[indices.astype(np.int64)] = values
        elif indices.ndim == 2:
            if indices.shape != (values.size, len(shape)):
                raise ValueError("coordinate index shape does not match sparse values")
            dense[tuple(indices.astype(np.int64).T)] = values
        else:
            raise ValueError("indices must have rank one or two")
    except (IndexError, TypeError, ValueError) as error:
        raise ImporterError(
            "ONNX sparse initializer has invalid indices: {}".format(error)
        ) from error
    return dense


def _decode_string(value: bytes, location: str) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ImporterError(
            "ONNX frontend cannot decode UTF-8 {}".format(location)
        ) from error


def _opaque_proto(value: object) -> Mapping[str, object]:
    data = value.SerializeToString()
    return {
        "protobuf_base64": base64.b64encode(data).decode("ascii"),
        "protobuf_sha256": hashlib.sha256(data).hexdigest(),
    }


def _embedded_graph(graph: object) -> Mapping[str, object]:
    return {
        "name": str(graph.name),
        "inputs": [str(value.name) for value in graph.input],
        "outputs": [str(value.name) for value in graph.output],
        "initializers": [
            _constant_snapshot(numpy_helper.to_array(value), "initializer")
            for value in graph.initializer
        ]
        + [
            _constant_snapshot(_sparse_array(value), "sparse_initializer")
            for value in graph.sparse_initializer
        ],
        "nodes": [
            {
                "name": str(node.name),
                "op_type": str(node.op_type),
                "domain": str(node.domain),
                "inputs": [str(value) for value in node.input if value],
                "outputs": [str(value) for value in node.output if value],
                "attributes": _attributes(node.attribute),
            }
            for node in graph.node
        ],
    }


def _attribute_value(attribute: object) -> object:
    attribute_type = int(attribute.type)
    if attribute_type == onnx.AttributeProto.UNDEFINED:
        return None
    if attribute_type == onnx.AttributeProto.FLOAT:
        return float(attribute.f)
    if attribute_type == onnx.AttributeProto.INT:
        return int(attribute.i)
    if attribute_type == onnx.AttributeProto.STRING:
        return _decode_string(attribute.s, "attribute {!r}".format(attribute.name))
    if attribute_type == onnx.AttributeProto.TENSOR:
        return _constant_snapshot(
            numpy_helper.to_array(attribute.t), "attribute {!r}".format(attribute.name)
        )
    if attribute_type == onnx.AttributeProto.GRAPH:
        return _embedded_graph(attribute.g)
    if attribute_type == onnx.AttributeProto.SPARSE_TENSOR:
        return _opaque_proto(attribute.sparse_tensor)
    if attribute_type == onnx.AttributeProto.TYPE_PROTO:
        return _opaque_proto(attribute.tp)
    if attribute_type == onnx.AttributeProto.FLOATS:
        return [float(value) for value in attribute.floats]
    if attribute_type == onnx.AttributeProto.INTS:
        return [int(value) for value in attribute.ints]
    if attribute_type == onnx.AttributeProto.STRINGS:
        return [
            _decode_string(value, "attribute {!r}".format(attribute.name))
            for value in attribute.strings
        ]
    if attribute_type == onnx.AttributeProto.TENSORS:
        return [
            _constant_snapshot(
                numpy_helper.to_array(value), "attribute {!r}".format(attribute.name)
            )
            for value in attribute.tensors
        ]
    if attribute_type == onnx.AttributeProto.GRAPHS:
        return [_embedded_graph(value) for value in attribute.graphs]
    if attribute_type == onnx.AttributeProto.SPARSE_TENSORS:
        return [_opaque_proto(value) for value in attribute.sparse_tensors]
    if attribute_type == onnx.AttributeProto.TYPE_PROTOS:
        return [_opaque_proto(value) for value in attribute.type_protos]
    raise ImporterError(
        "ONNX frontend cannot represent attribute {!r} with type {}".format(
            attribute.name, attribute_type
        )
    )


def _attributes(attributes: Sequence[object]) -> Mapping[str, object]:
    result: Dict[str, object] = {}
    for attribute in attributes:
        name = str(attribute.name)
        if not name or name in result:
            raise ImporterError("ONNX node contains a duplicate or unnamed attribute")
        value = _attribute_value(attribute)
        if attribute.ref_attr_name:
            value = {"value": value, "ref_attr_name": str(attribute.ref_attr_name)}
        result[name] = value
    return result


def _constant_node_array(node: object) -> Optional[np.ndarray]:
    attributes = {str(attribute.name): attribute for attribute in node.attribute}
    array: Optional[np.ndarray] = None
    if "value" in attributes:
        attribute = attributes["value"]
        if int(attribute.type) == onnx.AttributeProto.TENSOR:
            array = np.asarray(numpy_helper.to_array(attribute.t))
    elif "sparse_value" in attributes:
        attribute = attributes["sparse_value"]
        if int(attribute.type) == onnx.AttributeProto.SPARSE_TENSOR:
            array = _sparse_array(attribute.sparse_tensor)
    elif "value_float" in attributes:
        array = np.asarray(attributes["value_float"].f, dtype=np.float32)
    elif "value_floats" in attributes:
        array = np.asarray(attributes["value_floats"].floats, dtype=np.float32)
    elif "value_int" in attributes:
        array = np.asarray(attributes["value_int"].i, dtype=np.int64)
    elif "value_ints" in attributes:
        array = np.asarray(attributes["value_ints"].ints, dtype=np.int64)
    if array is None:
        return None
    dtype = np.dtype(array.dtype)
    if (
        dtype.hasobject
        or dtype.fields is not None
        or dtype.subdtype is not None
        or any(int(dimension) <= 0 for dimension in array.shape)
    ):
        return None
    return array


def _opset_metadata(model: object) -> Tuple[List[Mapping[str, object]], Mapping[str, int]]:
    opsets: List[Mapping[str, object]] = []
    versions: Dict[str, int] = {}
    for opset in model.opset_import:
        domain = str(opset.domain)
        version = int(opset.version)
        if version <= 0 or domain in versions:
            raise ImporterError(
                "ONNX model contains a duplicate domain or invalid opset import"
            )
        versions[domain] = version
        opsets.append({"domain": domain, "version": version})
    standard_versions = {
        version for domain, version in versions.items() if domain in {"", "ai.onnx"}
    }
    if len(standard_versions) > 1:
        raise ImporterError("ONNX model declares conflicting standard-domain opsets")
    return opsets, versions


def _applicable_opset(domain: str, versions: Mapping[str, int]) -> int:
    if domain in versions:
        return versions[domain]
    if domain in {"", "ai.onnx"}:
        for alias in ("", "ai.onnx"):
            if alias in versions:
                return versions[alias]
    raise ImporterError(
        "ONNX node domain {!r} has no applicable opset import".format(domain)
    )


def _graph_from_model(model: object, source_sha256: str) -> GraphIR:
    graph = model.graph
    opsets, opset_versions = _opset_metadata(model)
    initializer_arrays: Dict[str, np.ndarray] = {}

    def add_initializer(name: str, array: np.ndarray) -> None:
        if not name or name in initializer_arrays:
            raise ImporterError("ONNX graph contains a duplicate or unnamed initializer")
        initializer_arrays[name] = array

    for initializer in graph.initializer:
        add_initializer(
            str(initializer.name), np.asarray(numpy_helper.to_array(initializer))
        )
    for initializer in graph.sparse_initializer:
        add_initializer(str(initializer.values.name), _sparse_array(initializer))

    constant_node_arrays: Dict[str, np.ndarray] = {}
    for node in graph.node:
        if (
            str(node.op_type) != "Constant"
            or str(node.domain) not in {"", "ai.onnx"}
        ):
            continue
        array = _constant_node_array(node)
        if array is None:
            continue
        outputs = [str(value) for value in node.output if value]
        if len(outputs) != 1:
            raise ImporterError(
                "ONNX Constant with a materialized payload requires one output"
            )
        name = outputs[0]
        if name in initializer_arrays or name in constant_node_arrays:
            raise ImporterError(
                "ONNX graph contains duplicate static tensor {!r}".format(name)
            )
        constant_node_arrays[name] = array
    static_arrays = dict(initializer_arrays)
    static_arrays.update(constant_node_arrays)

    value_specs: Dict[str, TensorSpec] = {}
    for value_info in tuple(graph.input) + tuple(graph.output) + tuple(graph.value_info):
        name = str(value_info.name)
        spec = _value_info_spec(value_info)
        previous = value_specs.setdefault(name, spec)
        if previous != spec:
            raise ImporterError(
                "ONNX graph declares incompatible metadata for value {!r}".format(name)
            )

    tensor_ids: Dict[str, str] = {}
    tensors: List[TensorIR] = []

    def tensor_id(name: str) -> str:
        if not name:
            raise ImporterError("ONNX graph contains an empty required tensor name")
        known = tensor_ids.get(name)
        if known is not None:
            return known
        array = static_arrays.get(name)
        if array is not None:
            shape = tuple(int(item) for item in array.shape)
            dtype = np.dtype(array.dtype).name
        else:
            shape, dtype = value_specs.get(name, (None, None))
        result = "tensor_{:04d}".format(len(tensors))
        tensor_ids[name] = result
        tensors.append(
            TensorIR(
                id=result,
                name=name,
                shape=shape,
                dtype=dtype,
                layout=infer_onnx_layout(shape),
            )
        )
        return result

    graph_inputs = tuple(
        tensor_id(str(value.name))
        for value in graph.input
        if str(value.name) not in initializer_arrays
    )
    graph_outputs = tuple(tensor_id(str(value.name)) for value in graph.output)
    for value_info in graph.value_info:
        tensor_id(str(value_info.name))
    constants = []
    for name, array in static_arrays.items():
        identifier = tensor_id(name)
        constants.append(
            ConstantIR.from_values(
                tensor_id=identifier,
                dtype=np.dtype(array.dtype).name,
                shape=tuple(int(item) for item in array.shape),
                values=array,
            )
        )

    nodes = []
    for index, node in enumerate(graph.node):
        node_inputs = tuple(tensor_id(str(value)) for value in node.input if value)
        node_outputs = tuple(tensor_id(str(value)) for value in node.output if value)
        op_type = str(node.op_type)
        if not op_type:
            raise ImporterError("ONNX graph contains a node without an operator type")
        domain = str(node.domain)
        nodes.append(
            NodeIR(
                id="node_{:04d}".format(index),
                name=str(node.name) or "{}_{}".format(op_type, index),
                op_type=op_type,
                inputs=node_inputs,
                outputs=node_outputs,
                attributes=_attributes(node.attribute),
                source_location={
                    "frontend": "onnx",
                    "source_index": index,
                    "domain": domain,
                    "opset_version": _applicable_opset(domain, opset_versions),
                },
            )
        )

    domains = sorted(
        {str(model.domain)}
        | {str(opset.domain) for opset in model.opset_import}
        | {str(node.domain) for node in graph.node}
    )
    result = GraphIR(
        inputs=graph_inputs,
        outputs=graph_outputs,
        tensors=tuple(tensors),
        nodes=tuple(nodes),
        constants=tuple(constants),
        metadata={
            "importer": {
                "frontend": "onnx",
                "frontend_version": str(onnx.__version__),
                "source_format": "onnx",
                "source_sha256": source_sha256,
            },
            "model": {
                "name": str(graph.name),
                "ir_version": int(model.ir_version),
                "producer_name": str(model.producer_name),
                "producer_version": str(model.producer_version),
                "domain": str(model.domain),
                "model_version": int(model.model_version),
                "doc_string": str(model.doc_string),
            },
            "opsets": opsets,
            "domains": domains,
        },
    )
    result.validate()
    return result


def import_onnx(path: str) -> ImportResult:
    """Validate and convert one ONNX model without retaining ONNX objects."""
    source = Path(path)
    if not source.exists():
        raise ImporterError("model source does not exist: {}".format(source))
    if not source.is_file() or source.suffix.lower() != ".onnx":
        raise ImporterError("ONNX frontend expects a .onnx model file: {}".format(source))
    source_digest = _source_sha256(source)
    try:
        model = onnx.load(str(source))
    except Exception as error:
        raise _frontend_error("load", source, error) from error
    try:
        onnx.checker.check_model(model)
    except Exception as error:
        raise _frontend_error("checker validation", source, error) from error
    try:
        inferred_model = onnx.shape_inference.infer_shapes(model)
    except Exception as error:
        raise _frontend_error("shape inference", source, error) from error
    try:
        graph = _graph_from_model(inferred_model, source_digest)
    except ImporterError:
        raise
    except Exception as error:
        raise _frontend_error("GraphIR conversion", source, error) from error
    return ImportResult(
        graph=graph,
        report=ImportReport(
            frontend="onnx",
            frontend_version=str(onnx.__version__),
            source_format="onnx",
            source_sha256=source_digest,
        ),
    )


__all__ = ["import_onnx"]
