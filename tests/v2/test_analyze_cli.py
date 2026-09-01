"""End-to-end behavior for the framework-neutral V2 analysis command."""

from __future__ import annotations

import hashlib
import json

import pytest

from model2rtl.v2 import compiler
from model2rtl.v2.cli import main
from model2rtl.v2.importers import ImportReport, ImportResult, ImporterError
from model2rtl.v2.ir import ConstantIR, GraphIR, NodeIR, TensorIR
from model2rtl.v2.model_contract import ContractError


def _tensor(tensor_id, shape):
    return TensorIR(tensor_id, tensor_id, shape, "float32", "NC")


def _constant(tensor_id, shape):
    count = 1
    for dimension in shape:
        count *= dimension
    return ConstantIR.from_values(tensor_id, "float32", shape, [0.0] * count)


def _dense(node_id, source, target, weights, bias):
    return NodeIR(
        node_id,
        node_id,
        "Dense",
        (source,),
        (target,),
        {"kernel_tensor_id": weights, "bias_tensor_id": bias},
        {},
    )


def _import_result(source_sha256):
    graph = GraphIR(
        inputs=("features",),
        outputs=("output",),
        tensors=(
            _tensor("features", (1, 4)),
            _tensor("w1", (4, 5)),
            _tensor("b1", (5,)),
            _tensor("hidden_linear", (1, 5)),
            _tensor("hidden", (1, 5)),
            _tensor("w2", (5, 3)),
            _tensor("b2", (3,)),
            _tensor("output", (1, 3)),
        ),
        nodes=(
            _dense("dense1", "features", "hidden_linear", "w1", "b1"),
            NodeIR("relu", "relu", "ReLU", ("hidden_linear",), ("hidden",), {}, {}),
            _dense("dense2", "hidden", "output", "w2", "b2"),
        ),
        constants=(
            _constant("w1", (4, 5)),
            _constant("b1", (5,)),
            _constant("w2", (5, 3)),
            _constant("b2", (3,)),
        ),
        metadata={},
    )
    return ImportResult(
        graph,
        ImportReport("fixture", "1", "fixture", source_sha256, ()),
    )


def test_analyze_prints_honest_summary_and_writes_only_requested_json(
    monkeypatch, tmp_path, capsys
):
    """Analysis must not silently create a compile directory or claim RTL output."""
    model = tmp_path / "model.onnx"
    model.write_bytes(b"framework source")
    source_sha = hashlib.sha256(model.read_bytes()).hexdigest()
    monkeypatch.setattr(compiler, "import_model", lambda path: _import_result(source_sha))
    report_path = tmp_path / "requested-analysis.json"

    rc = main(["analyze", str(model), "--json", str(report_path)])

    assert rc == 0
    stdout = capsys.readouterr().out
    assert "MODEL" in stdout
    assert "OPERATORS" in stdout
    assert "PARTITION" in stdout
    assert "COSTS" in stdout
    assert "FULL RTL-CAPABLE" in stdout
    assert "RTL generated: no" in stdout

    report = json.loads(report_path.read_text())
    assert report["schema_version"] == "model2rtl-analysis-v1"
    assert report["model"] == {
        "tensor_count": 8,
        "node_count": 3,
        "parameter_count": 43,
    }
    assert report["operator_support"] == {
        "total": 3,
        "supported": 3,
        "software_fallback": 0,
        "unsupported": 0,
    }
    assert [item["node_id"] for item in report["decisions"]] == [
        "dense1",
        "relu",
        "dense2",
    ]
    assert [item["inference_action"] for item in report["decisions"]] == [
        "lower",
        "lower",
        "lower",
    ]
    partition = report["partition"]
    assert partition["execution_mode"] == "full_rtl"
    assert partition["software_prefix_node_ids"] == []
    assert partition["rtl_node_ids"] == ["dense1", "relu", "dense2"]
    assert partition["software_postfix_node_ids"] == []
    assert partition["boundary"] == {
        "input_tensor_ids": ["features"],
        "output_tensor_ids": ["output"],
    }
    assert report["costs"]["dense_macs"] == 35
    assert report["costs"]["parameter_bits"] == 396
    assert report["hashes"]["source_sha256"] == source_sha
    assert len(report["hashes"]["graph_ir_sha256"]) == 64
    assert report["limitations"]
    assert report["rtl_generated"] is False
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "model.onnx",
        "requested-analysis.json",
    ]
    assert not list(tmp_path.rglob("*.v"))


def test_analysis_report_is_framework_neutral_and_exposes_truthful_modes(monkeypatch):
    """Changing the imported framework must not alter shared orchestration fields."""
    source_sha = "a" * 64
    monkeypatch.setattr(compiler, "import_model", lambda path: _import_result(source_sha))

    report = compiler.analyze_model("opaque.model")

    document = report.to_dict()
    assert document["importer"]["frontend"] == "fixture"
    assert document["partition"]["execution_mode"] == "full_rtl"
    assert document["result"] == "FULL RTL-CAPABLE"
    assert document["rtl_generated"] is False


def test_analyze_reports_structural_h5_recovery_explicitly(monkeypatch, capsys):
    """Structural topology recovery must never look like executable import."""
    imported = _import_result("b" * 64)
    graph = GraphIR(
        inputs=imported.graph.inputs,
        outputs=imported.graph.outputs,
        tensors=imported.graph.tensors,
        nodes=imported.graph.nodes,
        constants=imported.graph.constants,
        metadata={
            "keras_recovery": {
                "mode": "structural_analysis",
                "executable": False,
                "weights_verified": False,
                "unsafe_code_blocked": True,
                "native_loader_error": None,
            }
        },
    )
    monkeypatch.setattr(
        compiler,
        "import_model",
        lambda path: ImportResult(graph, imported.report),
    )

    report = compiler.analyze_model("legacy.h5")
    document = report.to_dict()
    assert document["graph_metadata"]["keras_recovery"]["executable"] is False

    rc = main(["analyze", "legacy.h5"])

    assert rc == 0
    stdout = capsys.readouterr().out
    assert "IMPORTER" in stdout
    assert "recovery: structural_analysis" in stdout
    assert "executable: no" in stdout
    assert "weights verified: no" in stdout


def test_analyze_rejects_contract_conflicts_before_capability_analysis(
    monkeypatch, tmp_path
):
    """Moving contract reconciliation after classification can authorize bad elision."""
    source_sha = "a" * 64
    imported = _import_result(source_sha)
    graph = GraphIR(
        inputs=imported.graph.inputs,
        outputs=imported.graph.outputs,
        tensors=imported.graph.tensors,
        nodes=imported.graph.nodes,
        constants=imported.graph.constants,
        metadata={"preprocessing": {"resize": [32, 32]}},
    )
    monkeypatch.setattr(
        compiler,
        "import_model",
        lambda path: ImportResult(graph, imported.report),
    )

    def capability_must_not_run(*args, **kwargs):
        raise AssertionError("capability analysis ran before contract validation")

    monkeypatch.setattr(compiler, "classify_graph", capability_must_not_run)
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        """\
schema_version: model2rtl-contract-v1
input:
  name: features
  shape: [1, 4]
  dtype: float32
  layout: NC
preprocessing:
  resize: [64, 64]
output:
  interpretation: classification
  decision: argmax
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ContractError,
        match=(
            r"^contract preprocessing\.resize conflicts with embedded model "
            r"preprocessing$"
        ),
    ):
        compiler.analyze_model("fixture.model", str(contract_path))


def test_import_failures_are_stable_parser_errors_without_tracebacks(
    monkeypatch, tmp_path, capsys
):
    """Leaking an importer traceback would make expected user errors unstable."""
    model = tmp_path / "broken.onnx"
    model.write_bytes(b"broken")
    report_path = tmp_path / "must-not-exist.json"
    monkeypatch.setattr(
        compiler,
        "import_model",
        lambda path: (_ for _ in ()).throw(ImporterError("fixture parse failed")),
    )

    rc = main(["analyze", str(model), "--json", str(report_path)])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert captured.err == "model2rtl V2: fixture parse failed\n"
    assert "Traceback" not in captured.err
    assert not report_path.exists()


def test_model_read_oserror_without_json_is_reported_as_analysis_failure(
    monkeypatch, tmp_path, capsys
):
    """A model read failure must never be mislabeled as a JSON output failure."""
    model = tmp_path / "unreadable.onnx"
    model.write_bytes(b"fixture")
    monkeypatch.setattr(
        compiler,
        "import_model",
        lambda path: (_ for _ in ()).throw(OSError("fixture model read failed")),
    )

    rc = main(["analyze", str(model)])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert captured.err == (
        "model2rtl V2: unable to read model source: fixture model read failed\n"
    )
    assert "write analysis JSON" not in captured.err
    assert "Traceback" not in captured.err


def test_json_output_oserror_is_reported_as_write_failure(
    monkeypatch, tmp_path, capsys
):
    """An actual report-open failure must retain the specific JSON-write label."""
    model = tmp_path / "model.onnx"
    model.write_bytes(b"fixture")
    source_sha = hashlib.sha256(model.read_bytes()).hexdigest()
    monkeypatch.setattr(compiler, "import_model", lambda path: _import_result(source_sha))
    report_path = tmp_path / "missing-parent" / "analysis.json"

    rc = main(["analyze", str(model), "--json", str(report_path)])

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert captured.err.startswith("model2rtl V2: unable to write analysis JSON: ")
    assert str(report_path) in captured.err
    assert "read model source" not in captured.err
    assert not report_path.exists()


def test_reserved_compile_fails_stably_without_writing_anything(tmp_path, capsys):
    """A reserved command must never leave an output that resembles a compilation."""
    model = tmp_path / "model.onnx"
    model.write_bytes(b"not opened in milestone 1")
    output = tmp_path / "compile-output"

    rc = main(
        [
            "compile",
            "--model",
            str(model),
            "--contract",
            str(tmp_path / "contract.yaml"),
            "--calibration",
            str(tmp_path / "calibration.npz"),
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert captured.err == (
        "model2rtl V2: [E200] compile is unavailable in Milestone 1; "
        "no output was written.\n"
    )
    assert not output.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["model.onnx"]


def test_router_style_compile_argv_is_already_stripped(tmp_path, capsys):
    """Requiring the stripped subcommand again would break the console router path."""
    output = tmp_path / "compile-output"

    rc = main(["--model", "model.onnx", "--output", str(output)], command="compile")

    assert rc == 2
    assert "[E200]" in capsys.readouterr().err
    assert not output.exists()
