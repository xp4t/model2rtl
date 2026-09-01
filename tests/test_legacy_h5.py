import hashlib
import json

import h5py
import numpy as np
import pytest

from model2rtl.legacy_h5 import LegacyH5Error, analyze_h5, sha256_file, verify_source_hash


def write_legacy_fixture(tmp_path, feature_width, dense_units, nested_name):
    """Write the smallest legacy-style Functional H5 needed by this test."""
    path = tmp_path / "legacy.h5"
    nested_layers = [
        {
            "class_name": "InputLayer",
            "config": {
                "batch_input_shape": [None, 4, 4, 3],
                "dtype": "float32",
                "name": "nested_input",
            },
            "name": "nested_input",
        },
        {
            "class_name": "Conv2D",
            "config": {
                "name": nested_name,
                "filters": feature_width,
                "kernel_size": [1, 1],
                "activation": "linear",
                "trainable": True,
            },
            "name": nested_name,
        },
    ]
    layers = [
        {
            "class_name": "InputLayer",
            "config": {
                "batch_input_shape": [None, 4, 4, 3],
                "dtype": "float32",
                "name": "input_1",
            },
            "name": "input_1",
        },
        {
            "class_name": "Functional",
            "config": {"name": "backbone", "layers": nested_layers},
            "name": "backbone",
        },
        {
            "class_name": "GlobalAveragePooling2D",
            "config": {"name": "global_average_pooling2d", "trainable": True},
            "name": "global_average_pooling2d",
        },
    ]
    for index, units in enumerate(dense_units):
        layers.append(
            {
                "class_name": "Dense",
                "config": {
                    "name": "dense" if index == 0 else "dense_%d" % index,
                    "units": units,
                    "activation": "relu" if index == 0 else "softmax",
                    "use_bias": True,
                    "trainable": True,
                },
                "name": "dense" if index == 0 else "dense_%d" % index,
            }
        )
        if index < len(dense_units) - 1:
            layers.append(
                {
                    "class_name": "Dropout",
                    "config": {
                        "name": "dropout_%d" % index,
                        "rate": 0.3 + index / 10,
                        "trainable": True,
                    },
                    "name": "dropout_%d" % index,
                }
            )

    config = {
        "class_name": "Functional",
        "config": {"name": "fixture", "layers": layers},
    }
    with h5py.File(path, "w") as handle:
        handle.attrs["model_config"] = json.dumps(config)
        weights = handle.create_group("model_weights")
        in_features = feature_width
        for index, units in enumerate(dense_units):
            name = "dense" if index == 0 else "dense_%d" % index
            group = weights.create_group(name).create_group(name)
            group.create_dataset("kernel:0", data=np.zeros((in_features, units)))
            group.create_dataset("bias:0", data=np.zeros((units,)))
            in_features = units
    return path


def test_analyze_legacy_h5_preserves_names_and_finds_dense_suffix(tmp_path):
    """Removing nested metadata or guessing Dense shapes loses the split contract."""
    path = write_legacy_fixture(
        tmp_path, feature_width=8, dense_units=[4, 2], nested_name="conv1/conv"
    )

    result = analyze_h5(str(path))

    assert result.layers[1].children[1].name == "conv1/conv"
    assert result.boundary.layer_name == "global_average_pooling2d"
    assert result.boundary.feature_width == 8
    assert "conv1/conv" in result.boundary.unsupported_prefix
    assert [x.in_features for x in result.dense_layers] == [8, 4]
    assert [x.out_features for x in result.dense_layers] == [4, 2]
    assert [x.parameter_count for x in result.dense_layers] == [36, 10]
    assert result.dropout_rates == (0.3,)
    assert result.execution_mode == "hybrid"
    assert result.full_cnn_in_rtl is False


def test_analyze_legacy_h5_rejects_missing_or_malformed_model_config(tmp_path):
    """A broken metadata record must fail closed instead of yielding a guessed graph."""
    missing = tmp_path / "missing.h5"
    malformed = tmp_path / "malformed.h5"
    with h5py.File(missing, "w"):
        pass
    with h5py.File(malformed, "w") as handle:
        handle.attrs["model_config"] = "not json"

    with pytest.raises(LegacyH5Error, match="model_config"):
        analyze_h5(str(missing))
    with pytest.raises(LegacyH5Error, match="invalid"):
        analyze_h5(str(malformed))


def test_verify_source_hash_rejects_mismatch_before_loader_can_run(tmp_path):
    """Changing a source byte must block recovery before TensorFlow is imported."""
    path = write_legacy_fixture(
        tmp_path, feature_width=8, dense_units=[4, 2], nested_name="conv1/conv"
    )
    actual = hashlib.sha256(path.read_bytes()).hexdigest()

    assert sha256_file(str(path)) == actual
    with pytest.raises(LegacyH5Error, match="SHA-256 mismatch"):
        verify_source_hash(str(path), "0" * 64)
