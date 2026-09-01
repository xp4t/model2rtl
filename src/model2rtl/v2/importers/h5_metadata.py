"""Detached, non-executing metadata inspection for complete-model HDF5 files."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Optional, Tuple

import h5py

from .base import ImporterError


_HASH_BLOCK_BYTES = 1024 * 1024
_UNSAFE_CLASS_NAMES = frozenset(("Lambda", "TFOpLambda"))


@dataclass(frozen=True)
class H5Envelope:
    """Static complete-model HDF5 metadata detached from its source file."""

    path: Path
    source_sha256: str
    model_config: Mapping[str, object]
    keras_version: Optional[str]
    backend: Optional[str]
    root_keys: Tuple[str, ...]
    root_attributes: Tuple[str, ...]
    class_names: Tuple[str, ...]
    unsafe_class_names: Tuple[str, ...]


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(_HASH_BLOCK_BYTES), b""):
                digest.update(block)
    except OSError as error:
        raise ImporterError("H5_INVALID: cannot read HDF5 source {!s}".format(path)) from error
    return digest.hexdigest()


def _decode_utf8(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    raise TypeError("HDF5 attribute is not text")


def _optional_text(value: object) -> Optional[str]:
    try:
        return _decode_utf8(value)
    except (TypeError, UnicodeDecodeError):
        return None


def _reject_nonstandard_json(value: str) -> object:
    raise ValueError("non-standard JSON value {!r}".format(value))


def _object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> Mapping[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key {!r}".format(key))
        result[key] = value
    return result


def _model_config(value: object) -> Mapping[str, object]:
    try:
        decoded = _decode_utf8(value)
        parsed = json.loads(
            decoded,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonstandard_json,
        )
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ImporterError(
            "H5_MODEL_CONFIG_INVALID: model_config must be valid UTF-8 JSON"
        ) from error
    if not isinstance(parsed, Mapping):
        raise ImporterError(
            "H5_MODEL_CONFIG_INVALID: model_config must be a JSON object"
        )
    return parsed


def _collect_class_names(value: object, names: list[str]) -> None:
    if isinstance(value, Mapping):
        class_name = value.get("class_name")
        if isinstance(class_name, str):
            names.append(class_name)
        for item in value.values():
            _collect_class_names(item, names)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_class_names(item, names)


def inspect_h5(path: Path) -> H5Envelope:
    """Read static HDF5 topology metadata without importing Keras or TensorFlow."""
    source = Path(path)
    source_sha256 = _source_sha256(source)
    try:
        with h5py.File(source, "r") as handle:
            root_keys = tuple(sorted(str(key) for key in handle.keys()))
            root_attributes = tuple(sorted(str(key) for key in handle.attrs.keys()))
            if "model_config" not in handle.attrs:
                raise ImporterError(
                    "H5_MODEL_CONFIG_MISSING: HDF5 file has no complete-model "
                    "architecture (model_config); weights-only files require the "
                    "original model architecture and cannot be analyzed or compiled "
                    "independently"
                )
            model_config = _model_config(handle.attrs["model_config"])
            keras_version = _optional_text(handle.attrs.get("keras_version"))
            backend = _optional_text(handle.attrs.get("backend"))
    except ImporterError:
        raise
    except (OSError, ValueError, TypeError) as error:
        raise ImporterError(
            "H5_INVALID: cannot inspect HDF5 source {!s}".format(source)
        ) from error

    class_names: list[str] = []
    _collect_class_names(model_config, class_names)
    unsafe_class_names = tuple(
        class_name for class_name in class_names if class_name in _UNSAFE_CLASS_NAMES
    )
    return H5Envelope(
        path=source,
        source_sha256=source_sha256,
        model_config=model_config,
        keras_version=keras_version,
        backend=backend,
        root_keys=root_keys,
        root_attributes=root_attributes,
        class_names=tuple(class_names),
        unsafe_class_names=unsafe_class_names,
    )


__all__ = ["H5Envelope", "inspect_h5"]
