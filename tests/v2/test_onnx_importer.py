"""Optional ONNX frontend tests using real deterministic protobuf fixtures."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Iterator

import numpy as np
import pytest

from model2rtl.v2.ir import canonical_json


onnx = pytest.importorskip("onnx")


def _save_gemm(path: Path) -> None:
    from onnx import TensorProto, helper, numpy_helper

    weights = np.asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    bias = np.asarray([0.25, -0.5, 1.0], dtype=np.float32)
    graph = helper.make_graph(
        [
            helper.make_node(
                "Gemm",
                ["features", "weights", "bias"],
                ["scores"],
                name="dense",
                alpha=1.5,
                beta=0.5,
                transA=0,
                transB=0,
            )
        ],
        "fixed_gemm",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, 3])],
        initializer=[
            numpy_helper.from_array(weights, name="weights"),
            numpy_helper.from_array(bias, name="bias"),
        ],
    )
    onnx.save(helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)]), path)


def _save_unsupported_operator(path: Path) -> None:
    from onnx import TensorProto, helper

    graph = helper.make_graph(
        [
            helper.make_node(
                "UnsupportedTransform",
                ["features"],
                ["result"],
                name="keep_me",
                domain="example.model2rtl",
                label="unsupported operators stay visible",
            )
        ],
        "unsupported_operator",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("result", TensorProto.FLOAT, [1, 2])],
    )
    onnx.save(
        helper.make_model(
            graph,
            opset_imports=[
                helper.make_opsetid("", 13),
                helper.make_opsetid("example.model2rtl", 1),
            ],
        ),
        path,
    )


def _save_custom_output_without_value_info(path: Path) -> None:
    from onnx import TensorProto, helper

    graph = helper.make_graph(
        [
            helper.make_node(
                "OpaqueTransform",
                ["features"],
                ["opaque_value"],
                name="custom",
                domain="example.model2rtl",
            ),
            helper.make_node(
                "Identity", ["opaque_value"], ["result"], name="result"
            ),
        ],
        "unknown_custom_output",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("result", TensorProto.FLOAT, [1, 2])],
    )
    onnx.save(
        helper.make_model(
            graph,
            opset_imports=[
                helper.make_opsetid("", 13),
                helper.make_opsetid("example.model2rtl", 1),
            ],
        ),
        path,
    )


def _save_sparse_initializer(path: Path) -> None:
    from onnx import TensorProto, helper, numpy_helper

    values = numpy_helper.from_array(
        np.asarray([1.0, 2.0, 3.0], dtype=np.float32), name="weights"
    )
    indices = numpy_helper.from_array(
        np.asarray([[0, 1], [1, 0], [1, 2]], dtype=np.int64)
    )
    sparse_weights = helper.make_sparse_tensor(values, indices, [2, 3])
    graph = helper.make_graph(
        [helper.make_node("MatMul", ["features", "weights"], ["result"], name="dense")],
        "sparse_initializer",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("result", TensorProto.FLOAT, [1, 3])],
    )
    graph.sparse_initializer.extend([sparse_weights])
    onnx.save(
        helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)]), path
    )


def _save_constant_matmul_add(path: Path) -> None:
    from onnx import TensorProto, helper, numpy_helper

    weights = numpy_helper.from_array(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    )
    bias = numpy_helper.from_array(np.asarray([0.25, -0.5], dtype=np.float32))
    graph = helper.make_graph(
        [
            helper.make_node(
                "Constant", [], ["weights"], name="weights_node", value=weights
            ),
            helper.make_node(
                "Constant", [], ["bias"], name="bias_node", value=bias
            ),
            helper.make_node(
                "MatMul", ["features", "weights"], ["product"], name="matmul"
            ),
            helper.make_node("Add", ["product", "bias"], ["result"], name="add"),
        ],
        "constant_matmul_add",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("result", TensorProto.FLOAT, [1, 2])],
    )
    onnx.save(
        helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)]), path
    )


def _save_custom_constant_matmul(path: Path) -> None:
    from onnx import TensorProto, helper, numpy_helper

    weights = numpy_helper.from_array(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    )
    graph = helper.make_graph(
        [
            helper.make_node(
                "Constant",
                [],
                ["weights"],
                name="vendor_weights",
                domain="custom.domain",
                value=weights,
            ),
            helper.make_node(
                "MatMul", ["features", "weights"], ["result"], name="matmul"
            ),
        ],
        "custom_constant_matmul",
        [helper.make_tensor_value_info("features", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("result", TensorProto.FLOAT, [1, 2])],
        value_info=[helper.make_tensor_value_info("weights", TensorProto.FLOAT, [2, 2])],
    )
    onnx.save(
        helper.make_model(
            graph,
            opset_imports=[
                helper.make_opsetid("", 13),
                helper.make_opsetid("custom.domain", 1),
            ],
        ),
        path,
    )


def _walk(value: object) -> Iterator[object]:
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)
    elif hasattr(value, "values"):
        for item in value.values():
            yield from _walk(item)


def test_import_onnx_runs_validation_and_detaches_a_gemm_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skipping checker/inference or retaining protobuf values must fail this test."""
    from model2rtl.v2.importers.onnx import import_onnx

    source = tmp_path / "fixed.onnx"
    _save_gemm(source)
    calls: list[str] = []
    real_check_model = onnx.checker.check_model
    real_infer_shapes = onnx.shape_inference.infer_shapes

    def check_model(model: object) -> None:
        calls.append("checker")
        real_check_model(model)

    def infer_shapes(model: object) -> object:
        calls.append("inference")
        return real_infer_shapes(model)

    monkeypatch.setattr(onnx.checker, "check_model", check_model)
    monkeypatch.setattr(onnx.shape_inference, "infer_shapes", infer_shapes)

    first = import_onnx(str(source))
    second = import_onnx(str(source))

    assert calls == ["checker", "inference", "checker", "inference"]
    assert canonical_json(first.graph) == canonical_json(second.graph)
    assert first.report.frontend == "onnx"
    assert first.report.source_format == "onnx"
    assert first.graph.inputs == ("tensor_0000",)
    assert [node.op_type for node in first.graph.nodes] == ["Gemm"]
    gemm = first.graph.nodes[0]
    assert gemm.attributes == {"alpha": 1.5, "beta": 0.5, "transA": 0, "transB": 0}
    assert gemm.source_location["opset_version"] == 13
    assert list(first.graph.metadata["opsets"]) == [{"domain": "", "version": 13}]
    tensor_by_id = {tensor.id: tensor for tensor in first.graph.tensors}
    constants_by_name = {
        tensor_by_id[constant.tensor_id].name: constant
        for constant in first.graph.constants
    }
    assert set(constants_by_name) == {"weights", "bias"}
    assert tensor_by_id[gemm.inputs[1]].name == "weights"
    assert tensor_by_id[gemm.inputs[2]].name == "bias"
    assert base64.b64decode(constants_by_name["weights"].little_endian_data_base64) == (
        np.asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype="<f4").tobytes()
    )
    for value in _walk((first.graph.to_dict(), first.report.to_dict())):
        assert not type(value).__module__.startswith("onnx")


def test_import_onnx_keeps_unknown_domain_nodes_visible(tmp_path: Path) -> None:
    """Dropping an unsupported ONNX node would make capability analysis lie."""
    from model2rtl.v2.importers.onnx import import_onnx

    source = tmp_path / "unsupported.onnx"
    _save_unsupported_operator(source)

    graph = import_onnx(str(source)).graph

    assert [node.op_type for node in graph.nodes] == ["UnsupportedTransform"]
    assert graph.nodes[0].name == "keep_me"
    assert graph.nodes[0].attributes == {"label": "unsupported operators stay visible"}
    assert graph.nodes[0].source_location["domain"] == "example.model2rtl"
    assert graph.nodes[0].source_location["opset_version"] == 1
    assert list(graph.metadata["opsets"]) == [
        {"domain": "", "version": 13},
        {"domain": "example.model2rtl", "version": 1},
    ]


def test_import_onnx_keeps_custom_outputs_without_inferred_metadata_visible(
    tmp_path: Path,
) -> None:
    """Rejecting an untyped custom output would hide a valid analysis-only node."""
    from model2rtl.v2.importers.onnx import import_onnx

    source = tmp_path / "custom-output.onnx"
    _save_custom_output_without_value_info(source)

    graph = import_onnx(str(source)).graph

    assert [node.op_type for node in graph.nodes] == ["OpaqueTransform", "Identity"]
    custom = graph.nodes[0]
    opaque = next(tensor for tensor in graph.tensors if tensor.id == custom.outputs[0])
    assert opaque.name == "opaque_value"
    assert opaque.shape is None
    assert opaque.dtype is None
    assert graph.nodes[1].inputs == custom.outputs


def test_import_onnx_converts_sparse_initializers_to_constants(tmp_path: Path) -> None:
    """Ignoring graph.sparse_initializer would leave a MatMul input unproduced."""
    from model2rtl.v2.importers.onnx import import_onnx

    source = tmp_path / "sparse.onnx"
    _save_sparse_initializer(source)

    graph = import_onnx(str(source)).graph

    tensor_by_id = {tensor.id: tensor for tensor in graph.tensors}
    constants_by_name = {
        tensor_by_id[constant.tensor_id].name: constant
        for constant in graph.constants
    }
    assert set(constants_by_name) == {"weights"}
    weights = constants_by_name["weights"]
    assert weights.shape == (2, 3)
    assert base64.b64decode(weights.little_endian_data_base64) == np.asarray(
        [[0.0, 1.0, 0.0], [2.0, 0.0, 3.0]], dtype="<f4"
    ).tobytes()


def test_import_onnx_materializes_constant_tensor_attributes_for_dense_patterns(
    tmp_path: Path,
) -> None:
    """Leaving Constant attributes as snapshots must make MatMul/Add look dynamic."""
    from model2rtl.v2.capability import InferenceAction, SupportClass, classify_graph
    from model2rtl.v2.importers.onnx import import_onnx

    source = tmp_path / "constant-matmul-add.onnx"
    _save_constant_matmul_add(source)

    graph = import_onnx(str(source)).graph
    tensor_by_id = {tensor.id: tensor for tensor in graph.tensors}
    constant_names = {
        tensor_by_id[constant.tensor_id].name for constant in graph.constants
    }
    decisions = classify_graph(graph)
    decision_by_name = {
        node.name: decision for node, decision in zip(graph.nodes, decisions)
    }

    assert [node.op_type for node in graph.nodes] == [
        "Constant",
        "Constant",
        "MatMul",
        "Add",
    ]
    assert constant_names == {"weights", "bias"}
    assert decision_by_name["matmul"].support_class is SupportClass.SUPPORTED
    assert decision_by_name["matmul"].inference_action is InferenceAction.LOWER
    assert decision_by_name["add"].support_class is SupportClass.SUPPORTED
    assert decision_by_name["add"].inference_action is InferenceAction.LOWER


def test_custom_domain_constant_feeding_matmul_blocks_full_rtl(tmp_path: Path) -> None:
    """Materializing custom-domain Constants would hide a live unsupported producer."""
    from model2rtl.v2.capability import SupportClass, classify_graph
    from model2rtl.v2.importers.onnx import import_onnx
    from model2rtl.v2.partition import partition_graph

    source = tmp_path / "custom-constant-matmul.onnx"
    _save_custom_constant_matmul(source)

    graph = import_onnx(str(source)).graph
    decisions = classify_graph(graph)
    partition = partition_graph(graph, decisions)

    assert [node.name for node in graph.nodes] == ["vendor_weights", "matmul"]
    assert graph.constants == ()
    assert decisions[0].support_class is SupportClass.UNSUPPORTED
    assert partition.mode == "compile_unavailable"
