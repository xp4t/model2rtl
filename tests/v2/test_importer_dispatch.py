"""Behavioral tests for V2 importer selection and optional dependencies."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("suffix", "module_name", "function_name", "frontend"),
    (
        (".h5", "model2rtl.v2.importers.keras", "import_keras", "keras"),
        (".keras", "model2rtl.v2.importers.keras", "import_keras", "keras"),
        (".onnx", "model2rtl.v2.importers.onnx", "import_onnx", "onnx"),
    ),
)
def test_import_model_selects_frontend_from_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    module_name: str,
    function_name: str,
    frontend: str,
) -> None:
    """Routing one supported suffix to another frontend must fail this test."""
    from model2rtl.v2.importers import dispatch

    source = tmp_path / ("model" + suffix)
    source.write_bytes(b"fixture")
    sentinel = object()

    def selected_importer(path: str) -> object:
        assert path == str(source)
        return sentinel

    real_import_module = importlib.import_module

    def import_module(name: str) -> object:
        if name == module_name:
            return SimpleNamespace(**{function_name: selected_importer})
        return real_import_module(name)

    monkeypatch.setattr(dispatch.importlib, "import_module", import_module)

    assert dispatch.import_model(str(source)) is sentinel
    assert dispatch.frontend_for_path(str(source)) == frontend


def test_import_model_rejects_a_missing_source_before_loading_a_frontend(
    tmp_path: Path,
) -> None:
    """Deferring existence checks would replace a clear path error with a loader error."""
    from model2rtl.v2.importers import ImporterError, import_model

    source = tmp_path / "missing.h5"

    with pytest.raises(ImporterError, match=r"^model source does not exist: "):
        import_model(str(source))


def test_import_model_rejects_unsupported_file_extensions(tmp_path: Path) -> None:
    """Guessing a frontend for an unknown extension would make routing ambiguous."""
    from model2rtl.v2.importers import ImporterError, import_model

    source = tmp_path / "model.pb"
    source.write_bytes(b"fixture")

    with pytest.raises(
        ImporterError,
        match=(
            r"^unsupported model source extension '\.pb'; expected \.h5, \.keras, or \.onnx$"
        ),
    ):
        import_model(str(source))


@pytest.mark.parametrize(
    ("suffix", "missing_name", "install_command"),
    (
        (".h5", "tensorflow", 'pip install "model2rtl[keras]"'),
        (".onnx", "onnx", 'pip install "model2rtl[onnx]"'),
    ),
)
def test_missing_optional_frontend_has_actionable_install_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    missing_name: str,
    install_command: str,
) -> None:
    """Removing the exact extra command would leave installation failures unactionable."""
    from model2rtl.v2.importers import ImporterError, dispatch

    source = tmp_path / ("model" + suffix)
    source.write_bytes(b"fixture")

    def missing_frontend(name: str) -> object:
        raise ModuleNotFoundError(
            "No module named {!r}".format(missing_name), name=missing_name
        )

    monkeypatch.setattr(dispatch.importlib, "import_module", missing_frontend)

    with pytest.raises(ImporterError) as raised:
        dispatch.import_model(str(source))

    assert install_command in str(raised.value)


def test_importing_dispatch_does_not_import_optional_frameworks() -> None:
    """Adding an eager framework import at dispatch import time must fail this test."""
    code = """
import sys
import model2rtl.v2.importers.dispatch
for name in ('tensorflow', 'keras', 'h5py', 'onnx'):
    assert name not in sys.modules, name
"""

    project_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project_root / "src")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
