"""Framework-neutral result records and errors shared by V2 importers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from model2rtl.v2.ir import GraphIR


class ImporterError(ValueError):
    """A stable, user-facing model frontend failure."""


def infer_onnx_layout(shape: Optional[Tuple[object, ...]]) -> Optional[str]:
    """Return only layouts implied by ONNX tensor rank without channel guesses."""
    if shape is None:
        return None
    if len(shape) == 1:
        return "N"
    if len(shape) == 2:
        return "NC"
    return None


@dataclass(frozen=True)
class ImportReport:
    """Stable provenance and diagnostics emitted by one frontend."""

    frontend: str
    frontend_version: str
    source_format: str
    source_sha256: str
    diagnostics: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def to_dict(self) -> Mapping[str, object]:
        return {
            "frontend": self.frontend,
            "frontend_version": self.frontend_version,
            "source_format": self.source_format,
            "source_sha256": self.source_sha256,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class ImportResult:
    """Validated GraphIR paired with its importer report."""

    graph: GraphIR
    report: ImportReport
