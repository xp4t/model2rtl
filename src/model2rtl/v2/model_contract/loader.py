"""Strict YAML loading and deterministic normalization for model contracts."""

from __future__ import annotations

import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple

import yaml

from .schema import (
    CONTRACT_SCHEMA_VERSION,
    ContractError,
    InputContract,
    ModelContract,
    OutputContract,
    PathContract,
    PreprocessingContract,
)


class _DuplicateDetectingSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys at every depth."""


def _construct_mapping(
    loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> Mapping[object, object]:
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise ContractError("YAML mapping keys must be strings") from error
        if duplicate:
            raise ContractError("duplicate YAML key: {!r}".format(key))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateDetectingSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_contract(path: str) -> ModelContract:
    """Load and validate a V2 YAML model contract from *path*."""
    source_path = Path(path).resolve()
    try:
        with source_path.open("r", encoding="utf-8") as source:
            document = yaml.load(source, Loader=_DuplicateDetectingSafeLoader)
    except ContractError:
        raise
    except (OSError, yaml.YAMLError) as error:
        raise ContractError("unable to load contract: {}".format(error)) from error

    _require_json_value(document)
    root = _mapping(document, "contract")
    _reject_unknown(root, {"schema_version", "input", "output", "labels", "calibration", "preprocessing"}, "contract")

    schema_version = root.get("schema_version")
    if schema_version != CONTRACT_SCHEMA_VERSION:
        raise ContractError(
            "unknown schema_version: {!r}; expected {!r}".format(
                schema_version, CONTRACT_SCHEMA_VERSION
            )
        )

    input_contract = _load_input(_mapping(_required(root, "input", "contract"), "input"))
    output_contract = _load_output(_mapping(_required(root, "output", "contract"), "output"))
    contract_dir = source_path.parent
    labels = _load_path_section(root.get("labels"), "labels", contract_dir)
    calibration = _load_path_section(root.get("calibration"), "calibration", contract_dir)
    preprocessing = _load_preprocessing(root.get("preprocessing"))
    return ModelContract(
        input=input_contract,
        output=output_contract,
        labels=labels,
        calibration=calibration,
        preprocessing=preprocessing,
    )


def _load_input(section: Mapping[str, object]) -> InputContract:
    _reject_unknown(section, {"name", "shape", "dtype", "layout", "provenance"}, "input")
    name = _nonempty_string(_required(section, "name", "input"), "input.name")
    dtype = _nonempty_string(_required(section, "dtype", "input"), "input.dtype")
    layout = _nonempty_string(_required(section, "layout", "input"), "input.layout")
    if layout not in {"N", "NC", "NCHW", "NHWC"}:
        raise ContractError("input.layout must be one of: N, NC, NCHW, NHWC")
    shape_value = _required(section, "shape", "input")
    if not isinstance(shape_value, Sequence) or isinstance(shape_value, (str, bytes)):
        raise ContractError("input.shape must be a list of positive integers")
    shape = tuple(shape_value)
    if not shape or any(isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 0 for dimension in shape):
        raise ContractError("input.shape must be a list of positive integers")
    return InputContract(
        name=name,
        shape=shape,
        dtype=dtype,
        layout=layout,
        provenance=_provenance(section, "input"),
    )


def _load_output(section: Mapping[str, object]) -> OutputContract:
    _reject_unknown(section, {"interpretation", "decision", "provenance"}, "output")
    return OutputContract(
        interpretation=_nonempty_string(
            _required(section, "interpretation", "output"), "output.interpretation"
        ),
        decision=_nonempty_string(_required(section, "decision", "output"), "output.decision"),
        provenance=_provenance(section, "output"),
    )


def _load_path_section(
    value: object, section_name: str, contract_dir: Path
) -> Optional[PathContract]:
    if value is None:
        return None
    section = _mapping(value, section_name)
    _reject_unknown(section, {"path", "provenance"}, section_name)
    raw_path = _nonempty_string(_required(section, "path", section_name), section_name + ".path")
    runtime_path = (contract_dir / raw_path).resolve()
    try:
        relative_path = runtime_path.relative_to(contract_dir).as_posix()
    except ValueError as error:
        raise ContractError(section_name + ".path must resolve within the contract directory") from error
    return PathContract(
        path=runtime_path,
        relative_path=relative_path,
        provenance=_provenance(section, section_name),
    )


def _load_preprocessing(value: object) -> Optional[PreprocessingContract]:
    if value is None:
        return None
    section = _mapping(value, "preprocessing")
    _reject_unknown(
        section,
        {"resize", "interpolation", "channels", "operations", "provenance"},
        "preprocessing",
    )
    values = {key: _freeze_json(item) for key, item in section.items() if key != "provenance"}
    if "operations" in values:
        operations = values["operations"]
        if not isinstance(operations, tuple) or not all(isinstance(item, Mapping) for item in operations):
            raise ContractError("preprocessing.operations must be a list of mappings")
    return PreprocessingContract(
        values=MappingProxyType(values), provenance=_provenance(section, "preprocessing")
    )


def _mapping(value: object, location: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ContractError(location + " must be a mapping")
    return value


def _required(mapping: Mapping[str, object], key: str, location: str) -> object:
    if key not in mapping:
        raise ContractError(location + "." + key + " is required")
    return mapping[key]


def _nonempty_string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(location + " must be a non-empty string")
    return value


def _provenance(section: Mapping[str, object], location: str) -> str:
    value = section.get("provenance", "user_provided")
    if value not in {"user_provided", "embedded_model", "historical_recovered"}:
        raise ContractError(location + ".provenance is invalid")
    return str(value)


def _reject_unknown(mapping: Mapping[str, object], allowed: set, location: str) -> None:
    unknown = sorted(set(mapping).difference(allowed))
    if unknown:
        raise ContractError(location + " contains unknown keys: " + ", ".join(unknown))


def _require_json_value(value: object, location: str = "") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError("non-finite number at " + location)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("non-JSON mapping key at " + location)
            child = str(key) if not location else location + "." + str(key)
            _require_json_value(item, child)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_json_value(item, "{}[{}]".format(location, index))
        return
    raise ContractError(
        "non-JSON value at {}: {}".format(location or "contract", type(value).__name__)
    )


def _freeze_json(value: Any) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value
