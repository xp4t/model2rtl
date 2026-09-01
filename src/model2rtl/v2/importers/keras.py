"""Native, read-only Keras/HDF5 import into framework-neutral GraphIR."""

from __future__ import annotations

import hashlib
import math
import platform
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import h5py
import keras
import numpy as np
import tensorflow as tf

from model2rtl.v2.ir import ConstantIR, GraphIR, NodeIR, TensorIR

from .base import ImportReport, ImportResult, ImporterError
from .h5_metadata import H5Envelope, inspect_h5
from .keras_structural import structural_graph_from_h5


History = Tuple[str, int, int]
TensorSpec = Tuple[tuple, str]


def _flatten(value: object) -> List[object]:
    """Flatten Keras tensor structures across the Keras 2.15/3 API split."""
    tree = getattr(keras, "tree", None)
    flatten = getattr(tree, "flatten", None)
    if callable(flatten):
        return list(flatten(value))
    nest = getattr(tf, "nest", None)
    flatten = getattr(nest, "flatten", None)
    if callable(flatten):
        return list(flatten(value))
    raise ImporterError("Keras frontend has no compatible tensor-tree flatten API")


def _serialize_keras_object(value: object) -> object:
    """Serialize config objects using Keras 3, Keras 2.15, or tf.keras APIs."""
    namespaces = (
        getattr(keras, "saving", None),
        getattr(keras, "utils", None),
        getattr(getattr(tf, "keras", None), "utils", None),
    )
    for namespace in namespaces:
        serialize = getattr(namespace, "serialize_keras_object", None)
        if callable(serialize):
            return serialize(value)
    raise ImporterError("Keras frontend has no compatible config serialization API")


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: object) -> object:
    """Detach Keras configuration values into stable JSON primitives."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    serialized = _serialize_keras_object(value)
    if serialized is value:
        raise ImporterError(
            "Keras layer configuration contains an unserializable {}".format(
                type(value).__name__
            )
        )
    return _json_safe(serialized)


def _shape(value: object) -> tuple:
    if value is None:
        return ()
    dimensions = []
    for dimension in tuple(value):
        if dimension is None:
            dimensions.append(None)
        elif isinstance(dimension, str):
            dimensions.append(dimension)
        else:
            dimensions.append(int(dimension))
    return tuple(dimensions)


def _dtype_name(value: object) -> str:
    try:
        return np.dtype(str(value)).name
    except TypeError:
        return str(value)


def _layout(shape: tuple, layer_config: Optional[Mapping[str, object]] = None) -> Optional[str]:
    if len(shape) == 2:
        return "NC"
    if len(shape) != 4:
        return None
    data_format = None if layer_config is None else layer_config.get("data_format")
    if data_format == "channels_first":
        return "NCHW"
    if data_format == "channels_last":
        return "NHWC"
    return None


def _history(value: object) -> History:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ImporterError("Keras graph contains a malformed tensor history")
    name, node_index, tensor_index = value
    if not isinstance(name, str):
        raise ImporterError("Keras graph contains a malformed tensor history")
    return name, int(node_index), int(tensor_index)


def _declared_histories(value: object) -> List[History]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and isinstance(value[0], str)
    ):
        return [_history(value)]
    result: List[History] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            result.extend(_declared_histories(item))
    return result


def _tensor_descriptors(value: object) -> List[Mapping[str, object]]:
    result: List[Mapping[str, object]] = []
    if isinstance(value, Mapping):
        if value.get("class_name") == "__keras_tensor__":
            config = value.get("config")
            if isinstance(config, Mapping) and "keras_history" in config:
                result.append(config)
                return result
        for item in value.values():
            result.extend(_tensor_descriptors(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            result.extend(_tensor_descriptors(item))
    return result


def _tensor_spec(tensor: object) -> TensorSpec:
    return _shape(getattr(tensor, "shape")), _dtype_name(getattr(tensor, "dtype"))


def _record_name(record: Mapping[str, object]) -> str:
    name = record.get("name")
    if isinstance(name, str) and name:
        return name
    config = record.get("config")
    if isinstance(config, Mapping):
        configured_name = config.get("name")
        if isinstance(configured_name, str) and configured_name:
            return configured_name
    raise ImporterError("Keras model contains a layer without a stable name")


def _single_public_tensor(layer: object, attribute: str) -> Optional[object]:
    """Return one public layer tensor without requiring legacy metadata to exist."""
    try:
        value = getattr(layer, attribute)
    except (AttributeError, RuntimeError, ValueError):
        return None
    try:
        tensors = _flatten(value)
    except (AttributeError, RuntimeError, ValueError):
        return None
    if len(tensors) != 1:
        raise ImporterError(
            "Keras Sequential layer {!r} does not have one public {} tensor".format(
                getattr(layer, "name", "layer"), attribute
            )
        )
    return tensors[0]


def _serialized_build_input_spec(
    record: Mapping[str, object], layer: object
) -> Optional[TensorSpec]:
    """Recover a Sequential input spec from detached serialized build metadata."""
    build_config = record.get("build_config")
    if not isinstance(build_config, Mapping):
        return None
    input_shape = build_config.get("input_shape")
    if input_shape is None:
        return None
    shape = _shape(input_shape)
    dtype_value = getattr(layer, "compute_dtype", None)
    if dtype_value is None:
        dtype_value = getattr(layer, "dtype", "float32")
    return shape, _dtype_name(dtype_value)


def _sequential_graph_records(
    model: object,
    records: Sequence[object],
) -> Tuple[List[Mapping[str, object]], List[History], List[History]]:
    """Add explicit public tensor histories omitted by Sequential.get_config()."""
    normalized: List[Mapping[str, object]] = []
    previous: Optional[History] = None
    previous_output_spec: Optional[TensorSpec] = None
    loaded_by_name = {str(layer.name): layer for layer in model.layers}
    model_inputs = _flatten(model.inputs)
    input_history: Optional[History] = None
    for record_value in records:
        if not isinstance(record_value, Mapping):
            raise ImporterError("Keras model contains a malformed layer record")
        record = dict(record_value)
        layer_name = _record_name(record)
        record["name"] = layer_name
        source_class = str(record.get("class_name", "UnknownLayer"))
        if source_class == "InputLayer":
            record["inbound_nodes"] = []
            previous = (layer_name, 0, 0)
            input_history = previous
            if len(model_inputs) == 1:
                previous_output_spec = _tensor_spec(model_inputs[0])
            normalized.append(record)
            continue
        if previous is None:
            raise ImporterError("Keras Sequential model has no serialized input layer")
        layer = loaded_by_name.get(layer_name)
        if layer is None:
            raise ImporterError("Keras serialized layer {!r} is not loaded".format(layer_name))
        public_input = _single_public_tensor(layer, "input")
        if public_input is not None:
            input_spec = _tensor_spec(public_input)
        else:
            input_spec = _serialized_build_input_spec(record, layer)
        if input_spec is None:
            input_spec = previous_output_spec
        if input_spec is None:
            raise ImporterError(
                "Keras Sequential layer {!r} has no deterministic input tensor "
                "specification".format(layer_name)
            )
        shape, dtype = input_spec
        record["inbound_nodes"] = [
            {
                "args": [
                    {
                        "class_name": "__keras_tensor__",
                        "config": {
                            "shape": list(shape),
                            "dtype": dtype,
                            "keras_history": list(previous),
                        },
                    }
                ],
                "kwargs": {},
            }
        ]
        previous = (layer_name, 0, 0)
        public_output = _single_public_tensor(layer, "output")
        previous_output_spec = (
            _tensor_spec(public_output) if public_output is not None else None
        )
        normalized.append(record)
    if input_history is None or previous is None:
        raise ImporterError("Keras Sequential model has no importable graph")
    return normalized, [input_history], [previous]


def _call_name(layer_name: str, node_index: int, call_count: int) -> str:
    return layer_name if call_count == 1 else "{}/call_{}".format(layer_name, node_index)


def _activation_name(layer: object, layer_config: Mapping[str, object]) -> str:
    configured = layer_config.get("activation", "linear")
    if isinstance(configured, str):
        return configured.lower()
    activation = getattr(layer, "activation", None)
    if activation is None:
        return "linear"
    serialized = keras.activations.serialize(activation)
    if isinstance(serialized, str):
        return serialized.lower()
    if isinstance(serialized, Mapping):
        return str(serialized.get("class_name", "activation")).lower()
    return "activation"


def _activation_op(activation: str) -> str:
    return {
        "relu": "ReLU",
        "softmax": "Softmax",
        "sigmoid": "Sigmoid",
        "tanh": "Tanh",
    }.get(activation, "Activation")


def _source_location(
    source_index: int,
    node_index: int,
    source_class: str,
) -> Mapping[str, object]:
    return {
        "frontend": "keras",
        "source_index": source_index,
        "source_node_index": node_index,
        "source_class": source_class,
    }


def _weight_name(variable: object, weight_index: int) -> str:
    name = str(getattr(variable, "name", "weight_{}".format(weight_index)))
    return name.split(":", 1)[0].rsplit("/", 1)[-1]


def _layer_constants(
    layer: object,
    layer_index: int,
) -> Tuple[List[TensorIR], List[ConstantIR], Tuple[str, ...], Mapping[str, str]]:
    variables = list(getattr(layer, "weights", ()))
    values = list(layer.get_weights())
    tensor_records: List[TensorIR] = []
    constants: List[ConstantIR] = []
    tensor_ids: List[str] = []
    tensor_id_by_name: Dict[str, str] = {}
    for weight_index, array_value in enumerate(values):
        array = np.asarray(array_value)
        if not array.shape:
            array = array.reshape((1,))
        tensor_id = "constant_{:04d}_{:02d}".format(layer_index, weight_index)
        variable = variables[weight_index] if weight_index < len(variables) else None
        weight_name = _weight_name(variable, weight_index)
        tensor_records.append(
            TensorIR(
                id=tensor_id,
                name="{}/{}".format(getattr(layer, "name"), weight_name),
                shape=tuple(int(item) for item in array.shape),
                dtype=array.dtype.name,
            )
        )
        constants.append(
            ConstantIR.from_values(
                tensor_id=tensor_id,
                dtype=array.dtype.name,
                shape=tuple(int(item) for item in array.shape),
                values=array,
            )
        )
        tensor_ids.append(tensor_id)
        tensor_id_by_name.setdefault(weight_name, tensor_id)
    return tensor_records, constants, tuple(tensor_ids), tensor_id_by_name


def _is_model_layer(layer: object) -> bool:
    model_types = []
    for namespace in (keras, getattr(tf, "keras", None)):
        model_type = getattr(namespace, "Model", None)
        if isinstance(model_type, type) and model_type not in model_types:
            model_types.append(model_type)
    return bool(model_types) and isinstance(layer, tuple(model_types))


def _remap_tensor_attributes(
    attributes: Mapping[str, object],
    tensor_id_map: Mapping[str, str],
) -> Mapping[str, object]:
    remapped: Dict[str, object] = {}
    for key, value in attributes.items():
        if key.endswith("_tensor_id") and isinstance(value, str):
            remapped[key] = tensor_id_map.get(value, value)
        elif key.endswith("_tensor_ids") and isinstance(value, (list, tuple)):
            remapped[key] = [
                tensor_id_map.get(item, item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            remapped[key] = value
    return remapped


def _append_nested_graph(
    nested: GraphIR,
    external_inputs: Tuple[str, ...],
    external_outputs: Tuple[str, ...],
    namespace: str,
    name_prefix: str,
    tensors: List[TensorIR],
    constants: List[ConstantIR],
    nodes: List[NodeIR],
) -> None:
    if len(nested.inputs) != len(external_inputs):
        raise ImporterError(
            "nested Keras model {!r} input count does not match its call".format(
                name_prefix
            )
        )
    if len(nested.outputs) != len(external_outputs):
        raise ImporterError(
            "nested Keras model {!r} output count does not match its call".format(
                name_prefix
            )
        )

    tensor_id_map = {
        tensor_id: external_id
        for tensor_id, external_id in zip(nested.inputs, external_inputs)
    }
    for tensor_id, external_id in zip(nested.outputs, external_outputs):
        if tensor_id in tensor_id_map and tensor_id_map[tensor_id] != external_id:
            raise ImporterError(
                "nested Keras identity model {!r} requires an explicit boundary node".format(
                    name_prefix
                )
            )
        tensor_id_map[tensor_id] = external_id
    for tensor in nested.tensors:
        tensor_id_map.setdefault(
            tensor.id, "{}_{}".format(namespace, tensor.id)
        )

    boundary_ids = set(nested.inputs).union(nested.outputs)
    for tensor in nested.tensors:
        if tensor.id in boundary_ids:
            continue
        tensors.append(
            TensorIR(
                id=tensor_id_map[tensor.id],
                name="{}/{}".format(name_prefix, tensor.name),
                shape=tensor.shape,
                dtype=tensor.dtype,
                layout=tensor.layout,
                quantization=tensor.quantization,
            )
        )
    for constant in nested.constants:
        constants.append(
            ConstantIR(
                tensor_id=tensor_id_map[constant.tensor_id],
                dtype=constant.dtype,
                shape=constant.shape,
                little_endian_data_base64=constant.little_endian_data_base64,
                data_sha256=constant.data_sha256,
            )
        )
    for node in nested.nodes:
        source_location = dict(node.source_location)
        existing_path = source_location.get("nested_path")
        source_location["nested_path"] = (
            "{}/{}".format(name_prefix, existing_path)
            if isinstance(existing_path, str) and existing_path
            else name_prefix
        )
        nodes.append(
            NodeIR(
                id="{}_{}".format(namespace, node.id),
                name="{}/{}".format(name_prefix, node.name),
                op_type=node.op_type,
                inputs=tuple(tensor_id_map[item] for item in node.inputs),
                outputs=tuple(tensor_id_map[item] for item in node.outputs),
                attributes=_remap_tensor_attributes(
                    node.attributes, tensor_id_map
                ),
                source_location=source_location,
            )
        )


def _graph_from_model(model: object, source_format: str, source_sha256: str) -> GraphIR:
    model_config_value = model.get_config()
    if not isinstance(model_config_value, Mapping):
        raise ImporterError("Keras model configuration is not a mapping")
    model_config = model_config_value
    layer_records_value = model_config.get("layers")
    if not isinstance(layer_records_value, (list, tuple)):
        raise ImporterError("Keras model configuration has no serialized layers")
    layer_records: List[Mapping[str, object]]
    declared_inputs = _declared_histories(model_config.get("input_layers", ()))
    declared_outputs = _declared_histories(model_config.get("output_layers", ()))
    if declared_inputs or declared_outputs:
        layer_records = []
        for record_value in layer_records_value:
            if not isinstance(record_value, Mapping):
                raise ImporterError("Keras model contains a malformed layer record")
            layer_records.append(record_value)
        input_histories = declared_inputs
        output_histories = declared_outputs
    else:
        layer_records, input_histories, output_histories = _sequential_graph_records(
            model, layer_records_value
        )
    model_inputs = _flatten(model.inputs)
    model_outputs = _flatten(model.outputs)
    if len(input_histories) != len(model_inputs):
        raise ImporterError("Keras graph input histories do not match model inputs")
    if len(output_histories) != len(model_outputs):
        raise ImporterError("Keras graph output histories do not match model outputs")

    specs: Dict[History, TensorSpec] = {}
    inbound_by_call: Dict[Tuple[str, int], Tuple[History, ...]] = {}
    referenced = set(input_histories + output_histories)
    for record_value in layer_records:
        if not isinstance(record_value, Mapping):
            raise ImporterError("Keras model contains a malformed layer record")
        layer_name = _record_name(record_value)
        inbound_nodes = record_value.get("inbound_nodes", ())
        if not isinstance(inbound_nodes, (list, tuple)):
            raise ImporterError("Keras layer {!r} has malformed inbound nodes".format(layer_name))
        for node_index, inbound_node in enumerate(inbound_nodes):
            descriptors = _tensor_descriptors(inbound_node)
            histories: List[History] = []
            for descriptor in descriptors:
                history = _history(descriptor["keras_history"])
                histories.append(history)
                referenced.add(history)
                specs[history] = (
                    _shape(descriptor.get("shape")),
                    _dtype_name(descriptor.get("dtype", "float32")),
                )
            inbound_by_call[(layer_name, node_index)] = tuple(histories)

    for history, tensor in zip(input_histories, model_inputs):
        specs[history] = _tensor_spec(tensor)
    for history, tensor in zip(output_histories, model_outputs):
        specs[history] = _tensor_spec(tensor)

    outputs_by_call: Dict[Tuple[str, int], List[int]] = {}
    for layer_name, node_index, tensor_index in referenced:
        outputs_by_call.setdefault((layer_name, node_index), []).append(tensor_index)
    for indexes in outputs_by_call.values():
        indexes.sort()

    tensors: List[TensorIR] = []
    constants: List[ConstantIR] = []
    nodes: List[NodeIR] = []
    history_to_tensor_id: Dict[History, str] = {}

    for input_index, (history, tensor) in enumerate(zip(input_histories, model_inputs)):
        tensor_id = "input_{:04d}".format(input_index)
        shape, dtype = specs[history]
        history_to_tensor_id[history] = tensor_id
        tensors.append(
            TensorIR(
                id=tensor_id,
                name=str(getattr(tensor, "name", history[0])),
                shape=shape,
                dtype=dtype,
                layout=_layout(shape),
            )
        )

    layer_by_name = {str(layer.name): layer for layer in model.layers}
    for layer_index, record_value in enumerate(layer_records):
        assert isinstance(record_value, Mapping)
        layer_name = _record_name(record_value)
        source_class = str(record_value.get("class_name", "UnknownLayer"))
        if source_class == "InputLayer":
            continue
        layer = layer_by_name.get(layer_name)
        if layer is None:
            raise ImporterError("Keras serialized layer {!r} is not loaded".format(layer_name))
        raw_layer_config = record_value.get("config", {})
        if not isinstance(raw_layer_config, Mapping):
            raise ImporterError("Keras layer {!r} has malformed configuration".format(layer_name))
        layer_config = _json_safe(raw_layer_config)
        assert isinstance(layer_config, Mapping)
        inbound_nodes = record_value.get("inbound_nodes", ())
        assert isinstance(inbound_nodes, (list, tuple))
        call_count = len(inbound_nodes)

        nested_graph = None
        if _is_model_layer(layer):
            nested_graph = _graph_from_model(
                layer, source_format, source_sha256
            )
            weight_ids: Tuple[str, ...] = ()
            weight_id_by_name: Mapping[str, str] = {}
        else:
            (
                weight_tensors,
                layer_constants,
                weight_ids,
                weight_id_by_name,
            ) = _layer_constants(layer, layer_index)
            tensors.extend(weight_tensors)
            constants.extend(layer_constants)

        for node_index, _inbound_node in enumerate(inbound_nodes):
            histories = inbound_by_call.get((layer_name, node_index), ())
            try:
                data_inputs = tuple(history_to_tensor_id[item] for item in histories)
            except KeyError as error:
                raise ImporterError(
                    "Keras layer {!r} references a tensor before its producer".format(
                        layer_name
                    )
                ) from error

            output_indexes = outputs_by_call.get((layer_name, node_index), [0])
            output_ids: List[str] = []
            for tensor_index in output_indexes:
                history = (layer_name, node_index, tensor_index)
                spec = specs.get(history)
                if spec is None:
                    raise ImporterError(
                        "Keras layer {!r} output {} has no public tensor specification".format(
                            layer_name, tensor_index
                        )
                    )
                tensor_id = "tensor_{:04d}_{:02d}_{:02d}".format(
                    layer_index, node_index, tensor_index
                )
                history_to_tensor_id[history] = tensor_id
                output_ids.append(tensor_id)
                shape, dtype = spec
                tensors.append(
                    TensorIR(
                        id=tensor_id,
                        name="{}:{}".format(layer_name, tensor_index),
                        shape=shape,
                        dtype=dtype,
                        layout=_layout(shape, raw_layer_config),
                    )
                )

            base_id = "node_{:04d}_{:02d}".format(layer_index, node_index)
            node_name = _call_name(layer_name, node_index, call_count)
            source_location = _source_location(layer_index, node_index, source_class)
            if nested_graph is not None:
                _append_nested_graph(
                    nested=nested_graph,
                    external_inputs=data_inputs,
                    external_outputs=tuple(output_ids),
                    namespace=base_id,
                    name_prefix=node_name,
                    tensors=tensors,
                    constants=constants,
                    nodes=nodes,
                )
                continue
            attributes: Dict[str, object] = {
                "layer_config": layer_config,
                "weight_tensor_ids": list(weight_ids),
            }
            node_inputs = data_inputs + weight_ids

            if source_class == "Dense":
                activation = _activation_name(layer, raw_layer_config)
                attributes.update(
                    {
                        "activation": "linear",
                        "source_activation": activation,
                        "units": int(getattr(layer, "units")),
                        "use_bias": bool(getattr(layer, "use_bias")),
                    }
                )
                kernel_id = weight_id_by_name.get("kernel")
                if kernel_id is None:
                    raise ImporterError("Keras Dense layer {!r} has no kernel".format(layer_name))
                attributes["kernel_tensor_id"] = kernel_id
                bias_id = weight_id_by_name.get("bias")
                if bias_id is not None:
                    attributes["bias_tensor_id"] = bias_id

                dense_outputs = tuple(output_ids)
                if activation != "linear":
                    if len(output_ids) != 1:
                        raise ImporterError(
                            "Keras Dense layer {!r} has multiple activated outputs".format(
                                layer_name
                            )
                        )
                    output_tensor = next(item for item in tensors if item.id == output_ids[0])
                    linear_id = output_ids[0] + "_linear"
                    tensors.append(
                        TensorIR(
                            id=linear_id,
                            name=node_name + "/linear:0",
                            shape=output_tensor.shape,
                            dtype=output_tensor.dtype,
                            layout=output_tensor.layout,
                        )
                    )
                    dense_outputs = (linear_id,)
                nodes.append(
                    NodeIR(
                        id=base_id,
                        name=node_name,
                        op_type="Dense",
                        inputs=node_inputs,
                        outputs=dense_outputs,
                        attributes=attributes,
                        source_location=source_location,
                    )
                )
                if activation != "linear":
                    nodes.append(
                        NodeIR(
                            id=base_id + "_activation",
                            name=node_name + "/activation",
                            op_type=_activation_op(activation),
                            inputs=dense_outputs,
                            outputs=tuple(output_ids),
                            attributes={
                                "activation": activation,
                                "layer_config": layer_config,
                            },
                            source_location=source_location,
                        )
                    )
                continue

            if source_class == "Dropout":
                attributes["inference_identity_proven"] = True
                attributes["rate"] = float(getattr(layer, "rate"))
            elif source_class in {"Flatten", "Reshape"} and output_ids:
                output_tensor = next(item for item in tensors if item.id == output_ids[0])
                attributes["target_shape"] = list(output_tensor.shape[1:])

            nodes.append(
                NodeIR(
                    id=base_id,
                    name=node_name,
                    op_type=source_class,
                    inputs=node_inputs,
                    outputs=tuple(output_ids),
                    attributes=attributes,
                    source_location=source_location,
                )
            )

    try:
        graph_outputs = tuple(history_to_tensor_id[item] for item in output_histories)
    except KeyError as error:
        raise ImporterError("Keras graph output has no imported producer") from error
    graph = GraphIR(
        inputs=tuple(history_to_tensor_id[item] for item in input_histories),
        outputs=graph_outputs,
        tensors=tuple(tensors),
        nodes=tuple(nodes),
        constants=tuple(constants),
        metadata={
            "importer": {
                "frontend": "keras",
                "frontend_version": str(keras.__version__),
                "source_format": source_format,
                "source_sha256": source_sha256,
            },
            "model": {
                "name": str(getattr(model, "name", "model")),
                "source_class": type(model).__name__,
            },
            "keras_recovery": {
                "mode": "native_executable",
                "executable": True,
                "weights_verified": True,
                "unsafe_code_blocked": False,
            },
        },
    )
    graph.validate()
    return graph


def _loader_error(path: Path, error: Exception) -> ImporterError:
    return ImporterError(
        "Keras frontend failed to load {!s}: {}: {} "
        "[Python {}; Keras {}; TensorFlow {}; h5py {}]".format(
            path,
            type(error).__name__,
            error,
            platform.python_version(),
            keras.__version__,
            tf.__version__,
            h5py.__version__,
        )
    )


def import_keras(path: str) -> ImportResult:
    """Load one native ``.h5`` or ``.keras`` model without modifying it."""
    source = Path(path)
    if not source.exists():
        raise ImporterError("model source does not exist: {}".format(source))
    if not source.is_file() or source.suffix.lower() not in {".h5", ".keras"}:
        raise ImporterError("Keras frontend expects a .h5 or .keras model file: {}".format(source))
    source_format = "h5" if source.suffix.lower() == ".h5" else "keras"
    envelope: Optional[H5Envelope] = None
    if source_format == "h5":
        envelope = inspect_h5(source)
        source_digest = envelope.source_sha256
        if envelope.unsafe_class_names:
            graph = structural_graph_from_h5(envelope)
            return ImportResult(
                graph=graph,
                report=ImportReport(
                    frontend="keras",
                    frontend_version=str(keras.__version__),
                    source_format=source_format,
                    source_sha256=source_digest,
                ),
            )
    else:
        source_digest = _source_sha256(source)
    try:
        model = keras.models.load_model(source, compile=False)
    except Exception as error:
        if envelope is not None:
            native_loader_error = "{}: {}".format(type(error).__name__, error)
            graph = structural_graph_from_h5(
                envelope, native_loader_error=native_loader_error
            )
            return ImportResult(
                graph=graph,
                report=ImportReport(
                    frontend="keras",
                    frontend_version=str(keras.__version__),
                    source_format=source_format,
                    source_sha256=source_digest,
                ),
            )
        raise _loader_error(source, error) from error
    try:
        graph = _graph_from_model(model, source_format, source_digest)
    except ImporterError as error:
        if envelope is None:
            raise
        native_graph_error = "{}: {}".format(type(error).__name__, error)
        graph = structural_graph_from_h5(
            envelope, native_loader_error=native_graph_error
        )
    return ImportResult(
        graph=graph,
        report=ImportReport(
            frontend="keras",
            frontend_version=str(keras.__version__),
            source_format=source_format,
            source_sha256=source_digest,
        ),
    )


__all__ = ["import_keras"]
