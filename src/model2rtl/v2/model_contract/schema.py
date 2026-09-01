"""Immutable, framework-neutral V2 model-contract records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple


CONTRACT_SCHEMA_VERSION = "model2rtl-contract-v1"


class ContractError(ValueError):
    """A deterministic validation error in an external model contract."""


@dataclass(frozen=True)
class InputContract:
    """The exact external tensor presented to a compiled model."""

    name: str
    shape: Tuple[int, ...]
    dtype: str
    layout: str
    provenance: str = "user_provided"

    def to_dict(self) -> Mapping[str, object]:
        return {
            "name": self.name,
            "shape": list(self.shape),
            "dtype": self.dtype,
            "layout": self.layout,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class OutputContract:
    """The model's externally declared result semantics."""

    interpretation: str
    decision: str
    provenance: str = "user_provided"

    def to_dict(self) -> Mapping[str, object]:
        return {
            "interpretation": self.interpretation,
            "decision": self.decision,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class PathContract:
    """A runtime-resolved path with a contract-relative canonical form."""

    path: Path
    relative_path: str
    provenance: str = "user_provided"

    def to_dict(self) -> Mapping[str, object]:
        return {"path": self.relative_path, "provenance": self.provenance}


@dataclass(frozen=True)
class PreprocessingContract:
    """Declared deterministic preprocessing metadata and operations."""

    values: Mapping[str, object]
    provenance: str = "user_provided"

    def to_dict(self) -> Mapping[str, object]:
        result = _json_value(self.values)
        assert isinstance(result, dict)
        result["provenance"] = self.provenance
        return result


@dataclass(frozen=True)
class ModelContract:
    """A validated V2 model contract without source-machine-specific paths."""

    input: InputContract
    output: OutputContract
    labels: Optional[PathContract] = None
    calibration: Optional[PathContract] = None
    preprocessing: Optional[PreprocessingContract] = None
    schema_version: str = CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Mapping[str, object]:
        result = {
            "schema_version": self.schema_version,
            "input": self.input.to_dict(),
            "output": self.output.to_dict(),
        }
        if self.preprocessing is not None:
            result["preprocessing"] = self.preprocessing.to_dict()
        if self.labels is not None:
            result["labels"] = self.labels.to_dict()
        if self.calibration is not None:
            result["calibration"] = self.calibration.to_dict()
        return result

    def canonical_json(self) -> str:
        """Return stable UTF-8 JSON without absolute source paths or timestamps."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"

    @property
    def sha256(self) -> str:
        """Return the SHA-256 digest of the contract's canonical semantics."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _json_value(value: Any) -> object:
    """Return a detached JSON-compatible copy of an already validated value."""
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value
