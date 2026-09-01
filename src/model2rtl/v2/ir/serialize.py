"""Canonical JSON and semantic digests for V2 GraphIR."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from .graph import GraphIR, GraphValidationError


def _canonical_value(value: Any) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GraphValidationError(
                "canonical GraphIR contains a non-finite number"
            )
        return value.hex()
    if isinstance(value, Mapping):
        return {
            key: _canonical_value(value[key])
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    raise GraphValidationError(
        "canonical GraphIR contains a non-framework-neutral value"
    )


def canonical_json(graph: GraphIR) -> str:
    """Return canonical UTF-8 JSON text with exactly one trailing newline."""
    if not isinstance(graph, GraphIR):
        raise TypeError("graph must be a GraphIR")
    graph.validate()
    document = _canonical_value(graph.to_dict())
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"


def graph_sha256(graph: GraphIR) -> str:
    """Return the SHA-256 digest of the canonical GraphIR document."""
    return hashlib.sha256(canonical_json(graph).encode("utf-8")).hexdigest()

