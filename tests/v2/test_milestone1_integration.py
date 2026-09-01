"""Deterministic real-model integration matrix for V2 Milestone 1."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Tuple
import zipfile

import numpy as np
import pytest

from model2rtl.v2.compiler import AnalysisReport, analyze_model
from model2rtl.v2.importers import import_model
from model2rtl.v2.importers import base as importer_base
from model2rtl.v2.ir import GraphIR, canonical_json, graph_sha256


def _fixed_values(shape: Tuple[int, ...], start: int) -> np.ndarray:
    count = int(np.prod(shape))
    return (np.arange(start, start + count, dtype=np.float32) / 32.0).reshape(
        shape
    )


def _set_dense_weights(layer: object, start: int) -> None:
    kernel_shape = tuple(int(value) for value in layer.kernel.shape)
    bias_shape = tuple(int(value) for value in layer.bias.shape)
    layer.set_weights(
        [_fixed_values(kernel_shape, start), _fixed_values(bias_shape, -start)]
    )


def _keras() -> object:
    return pytest.importorskip(
        "keras", reason="real native H5/Keras integration requires model2rtl[keras]"
    )


def _canonicalize_shared_object_ids(value: object) -> None:
    stable_ids = {}

    def visit(item: object) -> None:
        if isinstance(item, dict):
            if "shared_object_id" in item:
                source_id = json.dumps(
                    item["shared_object_id"],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                if source_id not in stable_ids:
                    stable_ids[source_id] = len(stable_ids) + 1
                item["shared_object_id"] = stable_ids[source_id]
            for key in sorted(item):
                if key != "shared_object_id":
                    visit(item[key])
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)


def _canonicalize_keras_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as source:
        members = [
            (info.filename, source.read(info))
            for info in source.infolist()
        ]

    canonical = io.BytesIO()
    with zipfile.ZipFile(canonical, "w", compression=zipfile.ZIP_STORED) as output:
        for filename, data in sorted(members):
            if filename == "metadata.json":
                metadata = json.loads(data.decode("utf-8"))
                metadata["date_saved"] = "1980-01-01@00:00:00"
                data = json.dumps(
                    metadata,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            elif filename == "config.json":
                config = json.loads(data.decode("utf-8"))
                _canonicalize_shared_object_ids(config)
                data = json.dumps(
                    config,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            info = zipfile.ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            output.writestr(info, data)
    path.write_bytes(canonical.getvalue())


def _generate_model_b_in_subprocess(path: Path) -> object:
    project_root = Path(__file__).resolve().parents[2]
    child = """
from pathlib import Path
import hashlib
import json
import runpy
import sys

from model2rtl.v2.importers import import_model
from model2rtl.v2.ir import graph_sha256

helpers = runpy.run_path(sys.argv[1])
source = Path(sys.argv[2])
helpers[\"_save_model_b\"](source)
print(json.dumps({
    \"source_sha256\": hashlib.sha256(source.read_bytes()).hexdigest(),
    \"graph_ir_sha256\": graph_sha256(import_model(str(source)).graph),
}, sort_keys=True))
"""
    environment = os.environ.copy()
    source_path = str(project_root / "src")
    inherited_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path
        if not inherited_path
        else source_path + os.pathsep + inherited_path
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            str(Path(__file__).resolve()),
            str(path),
        ],
        cwd=project_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _save_model_a(path: Path) -> None:
    keras = _keras()
    model = keras.Sequential(
        [
            keras.Input(batch_shape=(1, 8), name="features"),
            keras.layers.Dense(4, activation="relu", name="hidden"),
            keras.layers.Dense(2, name="output"),
        ],
        name="model_a",
    )
    _set_dense_weights(model.get_layer("hidden"), 1)
    _set_dense_weights(model.get_layer("output"), 101)
    model.save(path)


def _save_model_b(path: Path) -> None:
    keras = _keras()
    inputs = keras.Input(batch_shape=(1, 8), name="features")
    hidden_1 = keras.layers.Dense(6, activation="relu", name="hidden_1")(inputs)
    hidden_2 = keras.layers.Dense(4, activation="relu", name="hidden_2")(hidden_1)
    outputs = keras.layers.Dense(2, name="output")(hidden_2)
    model = keras.Model(inputs, outputs, name="model_b")
    _set_dense_weights(model.get_layer("hidden_1"), 1)
    _set_dense_weights(model.get_layer("hidden_2"), 101)
    _set_dense_weights(model.get_layer("output"), 201)
    model.save(path)
    _canonicalize_keras_archive(path)


def _save_model_c(path: Path) -> None:
    keras = _keras()
    model = keras.Sequential(
        [
            keras.Input(batch_shape=(1, 6, 6, 1), name="image"),
            keras.layers.Conv2D(2, (3, 3), name="conv"),
            keras.layers.MaxPooling2D((2, 2), name="pool"),
            keras.layers.Flatten(name="flatten"),
            keras.layers.Dense(3, activation="relu", name="features"),
            keras.layers.Dense(2, name="output"),
        ],
        name="model_c",
    )
    conv = model.get_layer("conv")
    conv.set_weights(
        [
            _fixed_values(tuple(int(value) for value in conv.kernel.shape), 1),
            _fixed_values(tuple(int(value) for value in conv.bias.shape), -1),
        ]
    )
    _set_dense_weights(model.get_layer("features"), 101)
    _set_dense_weights(model.get_layer("output"), 201)
    model.save(path)


def _save_model_d(path: Path) -> None:
    onnx = pytest.importorskip(
        "onnx", reason="real Model D integration requires model2rtl[onnx]"
    )
    from onnx import TensorProto, helper, numpy_helper

    graph = helper.make_graph(
        [
            helper.make_node(
                "Gemm",
                ["features", "weights_1", "bias_1"],
                ["hidden_linear"],
                name="dense_1",
            ),
            helper.make_node(
                "Relu", ["hidden_linear"], ["hidden"], name="relu"
            ),
            helper.make_node(
                "Gemm",
                ["hidden", "weights_2", "bias_2"],
                ["output"],
                name="dense_2",
            ),
        ],
        "model_d",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 4])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 2])],
        initializer=[
            numpy_helper.from_array(_fixed_values((4, 3), 1), name="weights_1"),
            numpy_helper.from_array(_fixed_values((3,), -1), name="bias_1"),
            numpy_helper.from_array(_fixed_values((3, 2), 101), name="weights_2"),
            numpy_helper.from_array(_fixed_values((2,), -101), name="bias_2"),
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    onnx.save(model, path)


def _save_unsupported_only_onnx(path: Path) -> None:
    onnx = pytest.importorskip(
        "onnx", reason="real unsupported ONNX integration requires model2rtl[onnx]"
    )
    from onnx import TensorProto, helper

    graph = helper.make_graph(
        [helper.make_node("Sin", ["features"], ["output"], name="unsupported")],
        "unsupported_only",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 2])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    onnx.save(model, path)


def _report_bytes(report: AnalysisReport) -> bytes:
    return (
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _repeat_and_assert_complete_decisions(path: Path) -> Tuple[GraphIR, AnalysisReport]:
    first_import = import_model(str(path))
    second_import = import_model(str(path))
    assert canonical_json(first_import.graph) == canonical_json(second_import.graph)

    first_report = analyze_model(str(path))
    second_report = analyze_model(str(path))
    assert _report_bytes(first_report) == _report_bytes(second_report)

    graph_node_ids = [node.id for node in first_import.graph.nodes]
    decision_node_ids = [decision.node_id for decision in first_report.decisions]
    assert decision_node_ids == graph_node_ids
    assert len(decision_node_ids) == len(set(decision_node_ids))
    assert first_report.to_dict()["operator_support"]["total"] == len(graph_node_ids)
    return first_import.graph, first_report


@pytest.mark.parametrize(
    ("shape", "expected"),
    [
        ((4,), "N"),
        ((1, 4), "NC"),
        ((1, 3, 8, 8), None),
        ((), None),
        (None, None),
    ],
)
def test_onnx_layout_inference_claims_only_unambiguous_vector_and_matrix_layouts(
    shape: object, expected: object
) -> None:
    """Missing NC or guessing a rank-4 channel order must fail this test."""
    assert importer_base.infer_onnx_layout(shape) == expected


def test_model_a_real_native_h5_dense_relu_dense_is_full_rtl(
    tmp_path: Path,
) -> None:
    """Misrouting H5 or omitting a Dense/ReLU decision must fail Model A."""
    source = tmp_path / "model_a.h5"
    _save_model_a(source)

    graph, report = _repeat_and_assert_complete_decisions(source)

    assert report.importer.frontend == "keras"
    assert report.importer.source_format == "h5"
    assert [node.op_type for node in graph.nodes] == ["Dense", "ReLU", "Dense"]
    assert report.partition.mode == "full_rtl"
    assert report.partition.rtl_node_ids == tuple(node.id for node in graph.nodes)
    assert report.rtl_generated is False


def test_structurally_recovered_h5_dense_graph_is_not_selected_for_rtl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Treating unverified structural Dense weights as RTL-capable must fail."""
    from model2rtl.v2.importers import keras as keras_importer

    source = tmp_path / "legacy_model_a.h5"
    _save_model_a(source)

    def fail_native(*args: object, **kwargs: object) -> object:
        raise ValueError("legacy loader failure")

    monkeypatch.setattr(keras_importer.keras.models, "load_model", fail_native)

    graph = import_model(str(source)).graph
    report = analyze_model(str(source))

    assert graph.metadata["keras_recovery"]["mode"] == "structural_analysis"
    assert graph.constants == ()
    assert report.partition.mode == "analysis_only"
    assert report.partition.rtl_node_ids == ()


def test_model_b_real_native_keras_multilayer_dense_is_full_rtl(
    tmp_path: Path,
) -> None:
    """Stopping at two Dense layers or treating .keras as ONNX must fail Model B."""
    source = tmp_path / "model_b.keras"
    _save_model_b(source)

    graph, report = _repeat_and_assert_complete_decisions(source)

    assert report.importer.frontend == "keras"
    assert report.importer.source_format == "keras"
    assert [node.op_type for node in graph.nodes] == [
        "Dense",
        "ReLU",
        "Dense",
        "ReLU",
        "Dense",
    ]
    assert report.partition.mode == "full_rtl"
    assert report.partition.rtl_node_ids == tuple(node.id for node in graph.nodes)
    assert report.rtl_generated is False


def test_model_b_independent_native_archives_have_reproducible_source_and_graph_hashes(
    tmp_path: Path,
) -> None:
    """Wall-clock ZIP metadata must not change Model B source or GraphIR hashes."""
    first_source = tmp_path / "first.keras"
    second_source = tmp_path / "second.keras"
    _save_model_b(first_source)
    time.sleep(1.1)
    _save_model_b(second_source)

    first_source_hash = hashlib.sha256(first_source.read_bytes()).hexdigest()
    second_source_hash = hashlib.sha256(second_source.read_bytes()).hexdigest()
    assert first_source_hash == second_source_hash

    with zipfile.ZipFile(first_source, "r") as archive:
        infos = archive.infolist()
        assert [info.filename for info in infos] == sorted(
            info.filename for info in infos
        )
        for info in infos:
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert info.external_attr == 0o600 << 16
            assert info.internal_attr == 0
            assert info.extra == b""
            assert info.comment == b""
        metadata = json.loads(archive.read("metadata.json"))
        assert metadata["date_saved"] == "1980-01-01@00:00:00"
        config = json.loads(archive.read("config.json"))
        shared_ids = [
            layer["config"]["dtype"]["shared_object_id"]
            for layer in config["config"]["layers"]
            if isinstance(layer.get("config", {}).get("dtype"), dict)
            and "shared_object_id" in layer["config"]["dtype"]
        ]
        assert shared_ids == [1, 1]

    loaded = _keras().models.load_model(first_source, compile=False)
    assert loaded.get_layer("hidden_2").dtype_policy.name == "float32"
    assert loaded.get_layer("output").dtype_policy.name == "float32"

    first_graph_hash = graph_sha256(import_model(str(first_source)).graph)
    second_graph_hash = graph_sha256(import_model(str(second_source)).graph)
    assert first_graph_hash == second_graph_hash


def test_model_b_fresh_processes_have_reproducible_source_and_graph_hashes(
    tmp_path: Path,
) -> None:
    """Process-specific Keras object IDs must not affect source or GraphIR hashes."""
    first = _generate_model_b_in_subprocess(tmp_path / "first-process.keras")
    second = _generate_model_b_in_subprocess(tmp_path / "second-process.keras")

    assert first["source_sha256"] == second["source_sha256"]
    assert first["graph_ir_sha256"] == second["graph_ir_sha256"]


def test_model_c_real_h5_cnn_has_explicit_software_prefix_and_dense_suffix(
    tmp_path: Path,
) -> None:
    """Hiding CNN nodes or labeling the whole graph RTL-capable must fail Model C."""
    source = tmp_path / "model_c.h5"
    _save_model_c(source)

    graph, report = _repeat_and_assert_complete_decisions(source)

    assert [node.op_type for node in graph.nodes] == [
        "Conv2D",
        "MaxPooling2D",
        "Flatten",
        "Dense",
        "ReLU",
        "Dense",
    ]
    node_by_id = {node.id: node for node in graph.nodes}
    assert report.partition.mode == "hybrid"
    assert [
        node_by_id[node_id].op_type
        for node_id in report.partition.software_prefix_node_ids
    ] == ["Conv2D", "MaxPooling2D"]
    assert [
        node_by_id[node_id].op_type for node_id in report.partition.rtl_node_ids
    ] == ["Flatten", "Dense", "ReLU", "Dense"]
    assert report.partition.software_postfix_node_ids == ()
    assert report.rtl_generated is False


def test_model_d_real_guarded_onnx_gemm_relu_gemm_is_full_rtl(
    tmp_path: Path,
) -> None:
    """Losing an ONNX Gemm/Relu node or rejecting its static weights must fail Model D."""
    source = tmp_path / "model_d.onnx"
    _save_model_d(source)

    graph, report = _repeat_and_assert_complete_decisions(source)

    assert report.importer.frontend == "onnx"
    assert [node.op_type for node in graph.nodes] == ["Gemm", "Relu", "Gemm"]
    for tensor in graph.tensors:
        if tensor.shape is not None and len(tensor.shape) == 1:
            assert tensor.layout == "N"
        elif tensor.shape is not None and len(tensor.shape) == 2:
            assert tensor.layout == "NC"
        else:
            assert tensor.layout is None
    assert report.partition.mode == "full_rtl"
    assert report.partition.rtl_node_ids == tuple(node.id for node in graph.nodes)
    assert report.rtl_generated is False


def test_real_guarded_unsupported_only_onnx_is_compile_unavailable(
    tmp_path: Path,
) -> None:
    """Dropping an unsupported live node or calling it analysis-only must fail."""
    source = tmp_path / "unsupported_only.onnx"
    _save_unsupported_only_onnx(source)

    graph, report = _repeat_and_assert_complete_decisions(source)

    assert [node.op_type for node in graph.nodes] == ["Sin"]
    assert [decision.support_class.value for decision in report.decisions] == [
        "unsupported"
    ]
    assert report.partition.mode == "compile_unavailable"
    assert report.partition.rtl_node_ids == ()
    assert report.rtl_generated is False
