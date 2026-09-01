"""Lazy selection of V2 model frontends from source paths."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable, Tuple

from .base import ImportResult, ImporterError


_FRONTENDS = {
    ".h5": ("keras", "model2rtl.v2.importers.keras", "import_keras"),
    ".keras": ("keras", "model2rtl.v2.importers.keras", "import_keras"),
    ".onnx": ("onnx", "model2rtl.v2.importers.onnx", "import_onnx"),
}

_MISSING_FRONTEND_MESSAGES = {
    "keras": (
        "Keras/HDF5 model import requires the optional Keras importer.\n\n"
        "Install with:\n"
        '    pip install "model2rtl[keras]"'
    ),
    "onnx": (
        "ONNX model import requires the optional ONNX importer.\n\n"
        "Install with:\n"
        '    pip install "model2rtl[onnx]"'
    ),
}


def _selection(path: Path) -> Tuple[str, str, str]:
    if not path.exists():
        raise ImporterError("model source does not exist: {}".format(path))
    suffix = path.suffix.lower()
    try:
        return _FRONTENDS[suffix]
    except KeyError as error:
        shown_suffix = suffix or "<none>"
        raise ImporterError(
            "unsupported model source extension {!r}; expected .h5, .keras, or .onnx".format(
                shown_suffix
            )
        ) from error


def frontend_for_path(path: str) -> str:
    """Return the selected frontend name after validating the source path."""
    frontend, _module_name, _function_name = _selection(Path(path))
    return frontend


def import_model(path: str) -> ImportResult:
    """Import a supported model source through its lazily loaded frontend."""
    source = Path(path)
    frontend, module_name, function_name = _selection(source)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        raise ImporterError(_MISSING_FRONTEND_MESSAGES[frontend]) from error
    importer: Callable[[str], ImportResult] = getattr(module, function_name)
    return importer(str(source))
