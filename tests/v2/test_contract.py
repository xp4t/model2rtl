"""Behavioral tests for the V2 YAML model-contract boundary."""

from __future__ import annotations

from pathlib import Path
import re
from types import MappingProxyType

import pytest

from model2rtl.v2 import model_contract as contract_api
from model2rtl.v2.ir import GraphIR, TensorIR
from model2rtl.v2.model_contract import ContractError, load_contract
from model2rtl.v2.model_contract.schema import (
    InputContract,
    ModelContract,
    OutputContract,
    PreprocessingContract,
)


VALID_CONTRACT = """\
schema_version: model2rtl-contract-v1
input:
  name: features
  shape: [1, 8]
  dtype: float32
  layout: NC
output:
  interpretation: classification
  decision: argmax
labels:
  path: labels.json
"""


def write_contract(directory: Path, content: str = VALID_CONTRACT) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "contract.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_contract_resolves_runtime_paths_and_keeps_canonical_paths_relative(
    tmp_path: Path,
) -> None:
    """Removing relative-path canonicalization would break this contract digest."""
    contract = load_contract(str(write_contract(tmp_path)))

    assert contract.input.name == "features"
    assert contract.input.shape == (1, 8)
    assert contract.labels is not None
    assert contract.labels.path == tmp_path / "labels.json"
    assert contract.to_dict()["labels"]["path"] == "labels.json"


def test_load_contract_rejects_unknown_schema_version(tmp_path: Path) -> None:
    """Accepting a future schema without a parser must fail this test."""
    path = write_contract(
        tmp_path, VALID_CONTRACT.replace("model2rtl-contract-v1", "future-v2")
    )

    with pytest.raises(
        ContractError,
        match="^unknown schema_version: 'future-v2'; expected 'model2rtl-contract-v1'$",
    ):
        load_contract(str(path))


def test_load_contract_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    """Replacing duplicate detection with YAML's last-key-wins behavior fails here."""
    path = write_contract(
        tmp_path,
        VALID_CONTRACT
        + "input:\n"
        + "  name: duplicate\n"
        + "  shape: [1, 8]\n"
        + "  dtype: float32\n"
        + "  layout: NC\n",
    )

    with pytest.raises(ContractError, match="^duplicate YAML key: 'input'$"):
        load_contract(str(path))


def test_load_contract_rejects_non_finite_numbers(tmp_path: Path) -> None:
    """Allowing NaN into canonical data would make semantic output non-portable."""
    path = write_contract(
        tmp_path,
        VALID_CONTRACT.replace(
            "output:\n", "preprocessing:\n  operations:\n    - scale: .nan\noutput:\n"
        ),
    )

    with pytest.raises(
        ContractError,
        match=r"^non-finite number at preprocessing\.operations\[0\]\.scale$",
    ):
        load_contract(str(path))


def test_load_contract_rejects_yaml_native_non_json_scalars(tmp_path: Path) -> None:
    """Letting YAML timestamps through would defer a loader error to JSON output."""
    path = write_contract(
        tmp_path,
        VALID_CONTRACT.replace(
            "output:\n",
            "preprocessing:\n  operations:\n    - starts_at: 2026-08-21\noutput:\n",
        ),
    )

    with pytest.raises(
        ContractError,
        match=r"^non-JSON value at preprocessing\.operations\[0\]\.starts_at: date$",
    ):
        load_contract(str(path))


def test_contract_sha_is_stable_when_containing_directory_changes(tmp_path: Path) -> None:
    """Leaking the absolute source directory into canonical data fails this test."""
    first = load_contract(str(write_contract(tmp_path / "one")))
    second = load_contract(str(write_contract(tmp_path / "two")))

    assert first.canonical_json() == second.canonical_json()
    assert first.sha256 == second.sha256


def _input_graph(
    *,
    name: str = "features",
    shape: tuple[int, ...] = (1, 8),
    dtype: str = "float32",
    layout: str = "NC",
    metadata: object = None,
) -> GraphIR:
    return GraphIR(
        inputs=("graph_input",),
        outputs=("graph_input",),
        tensors=(TensorIR("graph_input", name, shape, dtype, layout),),
        nodes=(),
        constants=(),
        metadata={} if metadata is None else metadata,
    )


def _model_contract(
    *,
    name: str = "features",
    shape: tuple[int, ...] = (1, 8),
    dtype: str = "float32",
    layout: str = "NC",
    preprocessing: PreprocessingContract | None = None,
) -> ModelContract:
    return ModelContract(
        input=InputContract(name, shape, dtype, layout),
        output=OutputContract("classification", "argmax"),
        preprocessing=preprocessing,
    )


def test_contract_selects_a_graph_input_by_name_and_requires_exact_metadata() -> None:
    """Skipping exact contract reconciliation must accept a mismatched model boundary."""
    graph = _input_graph()

    contract_api.validate_contract_against_graph(graph, _model_contract())

    mismatches = [
        (
            _model_contract(name="other"),
            "contract input.name 'other' does not match any GraphIR input",
        ),
        (
            _model_contract(shape=(1, 4)),
            "contract input.shape [1, 4] does not match GraphIR input 'features' shape [1, 8]",
        ),
        (
            _model_contract(dtype="float64"),
            "contract input.dtype 'float64' does not match GraphIR input 'features' dtype 'float32'",
        ),
        (
            _model_contract(layout="NCHW"),
            "contract input.layout 'NCHW' does not match GraphIR input 'features' layout 'NC'",
        ),
    ]
    for contract, message in mismatches:
        with pytest.raises(ContractError, match="^" + re.escape(message) + "$"):
            contract_api.validate_contract_against_graph(graph, contract)


def test_contract_rejects_conflicting_embedded_preprocessing() -> None:
    """Ignoring overlapping embedded preprocessing must permit double transformation."""
    graph = _input_graph(
        metadata={
            "preprocessing": {
                "resize": [32, 32],
                "interpolation": "bilinear",
            }
        }
    )
    contract = _model_contract(
        preprocessing=PreprocessingContract(
            MappingProxyType(
                {"resize": (64, 64), "interpolation": "bilinear"}
            )
        )
    )

    with pytest.raises(
        ContractError,
        match=(
            r"^contract preprocessing\.resize conflicts with embedded model "
            r"preprocessing$"
        ),
    ):
        contract_api.validate_contract_against_graph(graph, contract)
