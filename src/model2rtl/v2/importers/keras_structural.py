"""Conservative, framework-free structural translation of legacy HDF5 topology."""

from __future__ import annotations

import math
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from model2rtl.v2.ir import GraphIR, NodeIR, TensorIR

from .base import ImporterError
from .h5_metadata import H5Envelope


History = Tuple[str, int, int]
TensorSpec = Tuple[Optional[tuple], Optional[str]]
_PURE_ACTIVATIONS = {"relu": "ReLU", "softmax": "Softmax", "sigmoid": "Sigmoid", "tanh": "Tanh"}
_DTYPE_PRESERVING_OPERATORS = frozenset(
    {"Dense", "Dropout", "Activation", "ReLU", "Reshape", "Flatten"}
)


def _unsupported(message: str) -> ImporterError:
    return ImporterError("H5_MODEL_CONFIG_UNSUPPORTED: {}".format(message))


def _mapping(value: object, description: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _unsupported("{} must be a JSON object".format(description))
    return value


def _record_name(record: Mapping[str, object], index: int) -> str:
    for value in (record.get("name"), _mapping_or_empty(record.get("config")).get("name")):
        if isinstance(value, str) and value:
            return value
    return "layer_{:04d}".format(index)


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _class_name(record: Mapping[str, object]) -> str:
    value = record.get("class_name")
    return value if isinstance(value, str) and value else "UnknownLayer"


def _integer(value: object) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


def _shape(value: object) -> Optional[tuple]:
    if not isinstance(value, (list, tuple)):
        return None
    dimensions: List[object] = []
    for dimension in value:
        if dimension is None:
            dimensions.append(None)
        elif isinstance(dimension, str) and dimension:
            dimensions.append(dimension)
        else:
            integer = _integer(dimension)
            if integer is None or integer <= 0:
                return None
            dimensions.append(integer)
    return tuple(dimensions)


def _dtype(value: object) -> Optional[str]:
    candidate = None
    if isinstance(value, str) and value:
        candidate = value
    elif isinstance(value, Mapping):
        config = value.get("config")
        if isinstance(config, Mapping):
            name = config.get("name")
            if isinstance(name, str) and name:
                candidate = name
    if candidate is None:
        return None
    try:
        dtype = np.dtype(candidate)
    except TypeError:
        return None
    if dtype.hasobject or dtype.fields is not None or dtype.subdtype is not None:
        return None
    return dtype.name


def _layout(shape: Optional[tuple], config: Mapping[str, object]) -> Optional[str]:
    if shape is None:
        return None
    if len(shape) == 2:
        return "NC"
    if len(shape) != 4:
        return None
    if config.get("data_format") == "channels_first":
        return "NCHW"
    if config.get("data_format") == "channels_last":
        return "NHWC"
    return None


def _history(value: object) -> Optional[History]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    name, node_index, tensor_index = value[:3]
    if not isinstance(name, str) or not name:
        return None
    node = _integer(node_index)
    tensor = _integer(tensor_index)
    if node is None or tensor is None or node < 0 or tensor < 0:
        return None
    return name, node, tensor


def _declared_histories(value: object) -> List[History]:
    direct = _history(value)
    if direct is not None:
        return [direct]
    result: List[History] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            result.extend(_declared_histories(item))
    return result


def _tensor_descriptors(value: object) -> List[Tuple[History, TensorSpec]]:
    result: List[Tuple[History, TensorSpec]] = []
    if isinstance(value, Mapping):
        if value.get("class_name") == "__keras_tensor__":
            config = value.get("config")
            if isinstance(config, Mapping):
                history = _history(config.get("keras_history"))
                if history is not None:
                    result.append(
                        (history, (_shape(config.get("shape")), _dtype(config.get("dtype"))))
                    )
                    return result
        for item in value.values():
            result.extend(_tensor_descriptors(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            result.extend(_tensor_descriptors(item))
    return result


def _inbound_histories(value: object) -> Tuple[History, ...]:
    descriptors = _tensor_descriptors(value)
    if descriptors:
        return tuple(item[0] for item in descriptors)
    return tuple(_declared_histories(value))


def _input_spec(
    config: Mapping[str, object], record_build_config: object = None
) -> TensorSpec:
    for key in ("batch_shape", "batch_input_shape", "input_shape"):
        shape = _shape(config.get(key))
        if shape is not None:
            return shape, _dtype(config.get("dtype"))
    build_config = record_build_config
    if not isinstance(build_config, Mapping):
        build_config = config.get("build_config")
    if isinstance(build_config, Mapping):
        shape = _shape(build_config.get("input_shape"))
        if shape is not None:
            return shape, _dtype(config.get("dtype"))
    return None, _dtype(config.get("dtype"))


def _activation(config: Mapping[str, object]) -> str:
    value = config.get("activation", "linear")
    if isinstance(value, str) and value:
        return value.lower()
    if isinstance(value, Mapping):
        class_name = value.get("class_name")
        if isinstance(class_name, str) and class_name:
            return class_name.lower()
    return "unknown"


def _output_spec(
    source_class: str,
    config: Mapping[str, object],
    inputs: Sequence[TensorSpec],
    record_build_config: object,
) -> TensorSpec:
    if not inputs:
        return None, _dtype(config.get("dtype"))
    shape, dtype = inputs[0]
    output_shape = _shape(config.get("output_shape"))
    build_config = record_build_config
    if not isinstance(build_config, Mapping):
        build_config = config.get("build_config")
    if output_shape is None and isinstance(build_config, Mapping):
        output_shape = _shape(build_config.get("output_shape"))
    if output_shape is not None:
        output_dtype = _dtype(config.get("dtype"))
        if output_dtype is None and source_class in _DTYPE_PRESERVING_OPERATORS:
            output_dtype = dtype
        return output_shape, output_dtype
    if source_class == "Dense" and shape is not None and shape:
        units = _integer(config.get("units"))
        if units is not None and units > 0:
            return shape[:-1] + (units,), _dtype(config.get("dtype")) or dtype
    if source_class in {"Dropout", "Activation", "ReLU"}:
        return shape, dtype
    if source_class == "Reshape":
        target_shape = _shape(config.get("target_shape"))
        if shape is not None and shape and target_shape is not None:
            source_features = shape[1:]
            if all(isinstance(item, int) for item in source_features) and (
                math.prod(source_features) != math.prod(target_shape)
            ):
                return None, dtype
            return (shape[0],) + target_shape, dtype
        return None, dtype
    if source_class == "Flatten":
        return None, dtype
    return None, _dtype(config.get("dtype"))


def _dropout_identity(config: Mapping[str, object]) -> bool:
    rate = config.get("rate")
    return (
        isinstance(rate, (int, float))
        and not isinstance(rate, bool)
        and math.isfinite(float(rate))
        and 0.0 <= float(rate) < 1.0
    )


def _source_location(index: int, node_index: int, source_class: str) -> Mapping[str, object]:
    return {
        "frontend": "keras_structural",
        "source_index": index,
        "source_node_index": node_index,
        "source_class": source_class,
    }


def _node_name(layer_name: str, node_index: int, call_count: int) -> str:
    return layer_name if call_count == 1 else "{}/call_{}".format(layer_name, node_index)


def _records(envelope: H5Envelope) -> Tuple[str, Mapping[str, object], Sequence[Mapping[str, object]]]:
    top_class = envelope.model_config.get("class_name")
    if not isinstance(top_class, str) or not top_class:
        raise _unsupported("model topology has no class_name")
    config = _mapping(envelope.model_config.get("config"), "model config")
    layers = config.get("layers")
    if not isinstance(layers, (list, tuple)):
        raise _unsupported("model topology has no serialized layers")
    normalized: List[Mapping[str, object]] = []
    for index, record in enumerate(layers):
        normalized.append(_mapping(record, "layer {}".format(index)))
    return top_class, config, tuple(normalized)


def structural_graph_from_h5(
    envelope: H5Envelope,
    native_loader_error: Optional[str] = None,
) -> GraphIR:
    """Translate detached complete-model HDF5 JSON into analysis-only GraphIR.

    This function intentionally neither imports nor instantiates a model framework.
    It records topology only; it does not inspect weight datasets or attach constants.
    """
    if not isinstance(envelope, H5Envelope):
        raise TypeError("envelope must be an H5Envelope")
    top_class, model_config, records = _records(envelope)
    sequential = top_class == "Sequential"

    record_details: List[
        Tuple[str, str, Mapping[str, object], Sequence[object], object]
    ] = []
    layer_names = set()
    input_histories: List[History] = []
    input_specs: Dict[History, TensorSpec] = {}
    for index, record in enumerate(records):
        name = _record_name(record, index)
        source_class = _class_name(record)
        config = _mapping_or_empty(record.get("config"))
        inbound = record.get("inbound_nodes", ())
        if not isinstance(inbound, (list, tuple)):
            raise _unsupported("layer {!r} has malformed inbound_nodes".format(name))
        if name in layer_names:
            raise _unsupported("duplicate serialized layer name {!r}".format(name))
        layer_names.add(name)
        record_details.append(
            (name, source_class, config, inbound, record.get("build_config"))
        )
        if source_class == "InputLayer":
            history = (name, 0, 0)
            input_histories.append(history)
            input_specs[history] = _input_spec(config, record.get("build_config"))

    declared_inputs = _declared_histories(model_config.get("input_layers"))
    declared_outputs = _declared_histories(model_config.get("output_layers"))
    if declared_inputs:
        input_histories = declared_inputs
    if not input_histories and sequential:
        input_histories = [("__structural_input__", 0, 0)]
        input_specs[input_histories[0]] = (None, None)
    if not input_histories:
        raise _unsupported("model topology has no declared input")

    specs: Dict[History, TensorSpec] = dict(input_specs)
    for _name, _source_class, _config, inbound, _build_config in record_details:
        for inbound_node in inbound:
            for history, spec in _tensor_descriptors(inbound_node):
                specs.setdefault(history, spec)

    tensors: List[TensorIR] = []
    nodes: List[NodeIR] = []
    history_to_tensor_id: Dict[History, str] = {}
    for index, history in enumerate(input_histories):
        shape, dtype = specs.get(history, (None, None))
        tensor_id = "input_{:04d}".format(index)
        history_to_tensor_id[history] = tensor_id
        tensors.append(
            TensorIR(
                id=tensor_id,
                name=history[0],
                shape=shape,
                dtype=dtype,
                layout=_layout(shape, {}),
            )
        )

    referenced: Dict[Tuple[str, int], List[int]] = {}
    for history in declared_outputs:
        referenced.setdefault((history[0], history[1]), []).append(history[2])
    for _name, _source_class, _config, inbound, _build_config in record_details:
        for inbound_node in inbound:
            for history in _inbound_histories(inbound_node):
                referenced.setdefault((history[0], history[1]), []).append(history[2])

    previous: Optional[History] = input_histories[0] if sequential else None
    last_output: Optional[History] = None
    for layer_index, (
        layer_name,
        source_class,
        config,
        inbound,
        record_build_config,
    ) in enumerate(record_details):
        if source_class == "InputLayer":
            if sequential:
                previous = (layer_name, 0, 0)
            continue
        calls: List[Tuple[History, ...]] = []
        if inbound:
            calls = [tuple(_inbound_histories(item)) for item in inbound]
        elif sequential and previous is not None:
            calls = [(previous,)]
        else:
            calls = [()]

        for node_index, histories in enumerate(calls):
            try:
                data_inputs = tuple(history_to_tensor_id[item] for item in histories)
            except KeyError as error:
                raise _unsupported(
                    "layer {!r} references a tensor before its producer".format(layer_name)
                ) from error
            input_specs_for_node = [specs.get(item, (None, None)) for item in histories]
            output_indexes = sorted(set(referenced.get((layer_name, node_index), [0])))
            output_ids: List[str] = []
            output_histories: List[History] = []
            output_spec = _output_spec(
                source_class,
                config,
                input_specs_for_node,
                record_build_config,
            )
            for tensor_index in output_indexes:
                history = (layer_name, node_index, tensor_index)
                shape, dtype = specs.get(history, output_spec)
                tensor_id = "tensor_{:04d}_{:02d}_{:02d}".format(
                    layer_index, node_index, tensor_index
                )
                history_to_tensor_id[history] = tensor_id
                output_histories.append(history)
                output_ids.append(tensor_id)
                tensors.append(
                    TensorIR(
                        id=tensor_id,
                        name="{}:{}".format(layer_name, tensor_index),
                        shape=shape,
                        dtype=dtype,
                        layout=_layout(shape, config),
                    )
                )

            base_id = "node_{:04d}_{:02d}".format(layer_index, node_index)
            node_name = _node_name(layer_name, node_index, len(calls))
            source_location = _source_location(layer_index, node_index, source_class)
            attributes: Dict[str, object] = {
                "layer_config": config,
                "weight_tensor_ids": [],
            }
            node_outputs = tuple(output_ids)
            if source_class == "Dense":
                activation = _activation(config)
                attributes.update(
                    {
                        "activation": "linear" if activation in _PURE_ACTIVATIONS else activation,
                        "source_activation": activation,
                    }
                )
                units = _integer(config.get("units"))
                if units is not None and units > 0:
                    attributes["units"] = units
                use_bias = config.get("use_bias")
                if isinstance(use_bias, bool):
                    attributes["use_bias"] = use_bias
                if activation in _PURE_ACTIVATIONS:
                    if len(output_ids) != 1:
                        raise _unsupported(
                            "Dense layer {!r} has multiple activated outputs".format(layer_name)
                        )
                    public_tensor = tensors[-1]
                    linear_id = output_ids[0] + "_linear"
                    tensors.append(
                        TensorIR(
                            id=linear_id,
                            name=node_name + "/linear:0",
                            shape=public_tensor.shape,
                            dtype=public_tensor.dtype,
                            layout=public_tensor.layout,
                        )
                    )
                    node_outputs = (linear_id,)
                nodes.append(
                    NodeIR(
                        id=base_id,
                        name=node_name,
                        op_type="Dense",
                        inputs=data_inputs,
                        outputs=node_outputs,
                        attributes=attributes,
                        source_location=source_location,
                    )
                )
                if activation in _PURE_ACTIVATIONS:
                    nodes.append(
                        NodeIR(
                            id=base_id + "_activation",
                            name=node_name + "/activation",
                            op_type=_PURE_ACTIVATIONS[activation],
                            inputs=node_outputs,
                            outputs=tuple(output_ids),
                            attributes={
                                "activation": activation,
                                "layer_config": config,
                            },
                            source_location=source_location,
                        )
                    )
            else:
                if source_class == "Dropout":
                    attributes["inference_identity_proven"] = _dropout_identity(config)
                    rate = config.get("rate")
                    if isinstance(rate, (int, float)) and not isinstance(rate, bool):
                        attributes["rate"] = float(rate)
                nodes.append(
                    NodeIR(
                        id=base_id,
                        name=node_name,
                        op_type=source_class,
                        inputs=data_inputs,
                        outputs=tuple(output_ids),
                        attributes=attributes,
                        source_location=source_location,
                    )
                )
            if output_histories:
                previous = output_histories[0]
                last_output = output_histories[0]

    if declared_outputs:
        try:
            graph_outputs = tuple(history_to_tensor_id[item] for item in declared_outputs)
        except KeyError as error:
            raise _unsupported("model output has no imported producer") from error
    elif last_output is not None:
        graph_outputs = (history_to_tensor_id[last_output],)
    else:
        raise _unsupported("model topology has no non-input output")

    graph = GraphIR(
        inputs=tuple(history_to_tensor_id[item] for item in input_histories),
        outputs=graph_outputs,
        tensors=tuple(tensors),
        nodes=tuple(nodes),
        constants=(),
        metadata={
            "importer": {
                "frontend": "keras",
                "frontend_version": envelope.keras_version,
                "source_format": "h5",
                "source_sha256": envelope.source_sha256,
            },
            "model": {
                "name": str(model_config.get("name", top_class)),
                "source_class": top_class,
            },
            "keras_recovery": {
                "mode": "structural_analysis",
                "executable": False,
                "weights_verified": False,
                "unsafe_code_blocked": bool(envelope.unsafe_class_names),
                "native_loader_error": native_loader_error,
            },
        },
    )
    graph.validate()
    return graph


__all__ = ["structural_graph_from_h5"]
