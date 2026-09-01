"""Static HDF5 envelope tests that never import a model framework."""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from typing import Optional

import h5py
import pytest

from model2rtl.v2.importers.base import ImporterError


def _write_config_h5(
    tmp_path: Path,
    *,
    class_name: str = "Dense",
    model_config: Optional[object] = None,
) -> Path:
    source = tmp_path / "model.h5"
    config = (
        model_config
        if model_config is not None
        else {
            "class_name": "Functional",
            "config": {
                "layers": [
                    {"class_name": "InputLayer", "config": {"name": "inputs"}},
                    {"class_name": class_name, "config": {"name": "target"}},
                ]
            },
        }
    )
    with h5py.File(source, "w") as handle:
        handle.attrs["model_config"] = json.dumps(config)
        handle.attrs["keras_version"] = b"2.15.0"
        handle.attrs["backend"] = "tensorflow"
        handle.attrs["test_attribute"] = b"detached metadata"
        handle.create_group("model_weights")
    return source


def test_invalid_h5_has_stable_error(tmp_path: Path) -> None:
    """A non-HDF5 artifact must not reach a framework deserializer."""
    from model2rtl.v2.importers.h5_metadata import inspect_h5

    source = tmp_path / "bad.h5"
    source.write_bytes(b"not hdf5")

    with pytest.raises(ImporterError, match=r"^H5_INVALID:"):
        inspect_h5(source)


def test_weights_only_h5_explains_missing_architecture(tmp_path: Path) -> None:
    """Weights alone cannot establish a complete model graph."""
    from model2rtl.v2.importers.h5_metadata import inspect_h5

    source = tmp_path / "weights.h5"
    with h5py.File(source, "w") as handle:
        handle.create_group("model_weights")

    with pytest.raises(
        ImporterError, match=r"^H5_MODEL_CONFIG_MISSING:.*architecture"
    ):
        inspect_h5(source)


def test_malformed_model_config_has_stable_error(tmp_path: Path) -> None:
    """Topology metadata must be a UTF-8 JSON object, never a guessed shape."""
    from model2rtl.v2.importers.h5_metadata import inspect_h5

    source = tmp_path / "malformed.h5"
    with h5py.File(source, "w") as handle:
        handle.attrs["model_config"] = b"[not valid json]"

    with pytest.raises(ImporterError, match=r"^H5_MODEL_CONFIG_INVALID:"):
        inspect_h5(source)


def test_model_config_must_be_a_json_object(tmp_path: Path) -> None:
    """A JSON list is not a complete Keras model configuration."""
    from model2rtl.v2.importers.h5_metadata import inspect_h5

    source = _write_config_h5(tmp_path, model_config=["not", "a", "model"])

    with pytest.raises(ImporterError, match=r"^H5_MODEL_CONFIG_INVALID:"):
        inspect_h5(source)


def test_preflight_detects_lambda_without_deserializing(tmp_path: Path) -> None:
    """Unsafe serialized code is visible before a model loader is called."""
    from model2rtl.v2.importers.h5_metadata import inspect_h5

    source = _write_config_h5(tmp_path, class_name="Lambda")

    envelope = inspect_h5(source)

    assert envelope.unsafe_class_names == ("Lambda",)


def test_envelope_detaches_metadata_and_collects_nested_classes(tmp_path: Path) -> None:
    """Preflight must provide deterministic, immutable framework-neutral metadata."""
    from model2rtl.v2.importers.h5_metadata import inspect_h5

    config = {
        "class_name": "Functional",
        "config": {
            "layers": [
                {"class_name": "InputLayer", "config": {"name": "inputs"}},
                {
                    "class_name": "Dense",
                    "config": {
                        "name": "hidden",
                        "activation": {"class_name": "TFOpLambda"},
                    },
                },
            ]
        },
    }
    source = _write_config_h5(tmp_path, model_config=config)

    envelope = inspect_h5(source)

    assert envelope.path == source
    assert envelope.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert envelope.keras_version == "2.15.0"
    assert envelope.backend == "tensorflow"
    assert envelope.root_keys == ("model_weights",)
    assert envelope.root_attributes == (
        "backend",
        "keras_version",
        "model_config",
        "test_attribute",
    )
    assert envelope.class_names == (
        "Functional",
        "InputLayer",
        "Dense",
        "TFOpLambda",
    )
    assert envelope.unsafe_class_names == ("TFOpLambda",)
    assert envelope.model_config == config
    with pytest.raises(FrozenInstanceError):
        envelope.backend = "other"  # type: ignore[misc]
