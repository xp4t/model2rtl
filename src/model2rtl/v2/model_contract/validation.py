"""Reconcile a user model contract with imported GraphIR evidence."""

from __future__ import annotations

from typing import List, Mapping

from model2rtl.v2.ir import GraphIR, TensorIR

from .schema import ContractError, ModelContract


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _embedded_preprocessing(graph: GraphIR) -> List[Mapping[str, object]]:
    sections: List[Mapping[str, object]] = []
    metadata = graph.metadata.get("preprocessing")
    if metadata is not None:
        if not isinstance(metadata, Mapping):
            raise ContractError("embedded model preprocessing must be a mapping")
        sections.append(metadata)

    operations = []
    for node in graph.nodes:
        config = node.attributes.get("layer_config")
        if not isinstance(config, Mapping):
            continue
        if node.op_type == "Resizing":
            height = config.get("height")
            width = config.get("width")
            if type(height) is int and type(width) is int:
                section = {"resize": [height, width]}
                interpolation = config.get("interpolation")
                if isinstance(interpolation, str):
                    section["interpolation"] = interpolation
                sections.append(section)
        elif node.op_type == "Rescaling":
            scale = config.get("scale")
            offset = config.get("offset", 0.0)
            if isinstance(scale, (int, float)) and not isinstance(scale, bool):
                operation = {"scale": scale}
                if offset != 0.0:
                    operation["offset"] = offset
                operations.append(operation)
    if operations:
        sections.append({"operations": operations})
    return sections


def _validate_preprocessing(graph: GraphIR, contract: ModelContract) -> None:
    if contract.preprocessing is None:
        return
    declared = contract.preprocessing.values
    for embedded in _embedded_preprocessing(graph):
        for key in sorted(set(declared).intersection(embedded).difference({"provenance"})):
            if _plain(declared[key]) != _plain(embedded[key]):
                raise ContractError(
                    "contract preprocessing.{} conflicts with embedded model preprocessing".format(
                        key
                    )
                )


def validate_contract_against_graph(
    graph: GraphIR, contract: ModelContract
) -> TensorIR:
    """Return the named GraphIR input or raise a stable exact mismatch error."""
    graph.validate()
    tensor_by_id = {tensor.id: tensor for tensor in graph.tensors}
    matches = [
        tensor_by_id[tensor_id]
        for tensor_id in graph.inputs
        if tensor_by_id[tensor_id].name == contract.input.name
    ]
    if not matches:
        raise ContractError(
            "contract input.name {!r} does not match any GraphIR input".format(
                contract.input.name
            )
        )
    if len(matches) != 1:
        raise ContractError(
            "contract input.name {!r} matches multiple GraphIR inputs".format(
                contract.input.name
            )
        )
    selected = matches[0]
    if selected.shape != contract.input.shape:
        raise ContractError(
            "contract input.shape {} does not match GraphIR input {!r} shape {}".format(
                list(contract.input.shape),
                selected.name,
                None if selected.shape is None else list(selected.shape),
            )
        )
    if selected.dtype != contract.input.dtype:
        raise ContractError(
            "contract input.dtype {!r} does not match GraphIR input {!r} dtype {!r}".format(
                contract.input.dtype, selected.name, selected.dtype
            )
        )
    if selected.layout != contract.input.layout:
        raise ContractError(
            "contract input.layout {!r} does not match GraphIR input {!r} layout {!r}".format(
                contract.input.layout, selected.name, selected.layout
            )
        )
    _validate_preprocessing(graph, contract)
    return selected


__all__ = ["validate_contract_against_graph"]
