"""Framework-neutral orchestration for V2 model analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from .capability import CapabilityDecision, SupportClass, classify_graph
from .importers import ImportReport, ImporterError, import_model
from .ir import graph_sha256
from .model_contract import load_contract, validate_contract_against_graph
from .partition import CostEstimate, PartitionIR, estimate_partition_cost, partition_graph


ANALYSIS_SCHEMA_VERSION = "model2rtl-analysis-v1"

_RESULT_LABELS = {
    "full_rtl": "FULL RTL-CAPABLE",
    "hybrid": "HYBRID",
    "analysis_only": "ANALYSIS ONLY",
    "compile_unavailable": "COMPILE UNAVAILABLE",
}

_LIMITATIONS = (
    "Milestone 1 performs analysis only and does not generate RTL.",
    "Only one contiguous Dense suffix can be proposed as an RTL region.",
    "Cost estimates are advisory and do not represent synthesis results.",
)


def _decision_dict(decision: CapabilityDecision) -> Mapping[str, object]:
    return {
        "node_id": decision.node_id,
        "op_type": decision.op_type,
        "support_class": decision.support_class.value,
        "inference_action": decision.inference_action.value,
        "reason": decision.reason,
        "validator_key": decision.validator_key,
        "shape_rule_key": decision.shape_rule_key,
        "quantization_rule_key": decision.quantization_rule_key,
        "lowering_rule_key": decision.lowering_rule_key,
        "golden_rule_key": decision.golden_rule_key,
        "roadmap_label": decision.roadmap_label,
    }


def _partition_dict(partition: PartitionIR) -> Mapping[str, object]:
    return {
        "execution_mode": partition.mode,
        "selected_output_tensor_id": partition.selected_output_tensor_id,
        "software_prefix_node_ids": list(partition.software_prefix_node_ids),
        "rtl_node_ids": list(partition.rtl_node_ids),
        "software_postfix_node_ids": list(partition.software_postfix_node_ids),
        "boundary": {
            "input_tensor_ids": list(partition.input_boundary_tensor_ids),
            "output_tensor_ids": list(partition.output_boundary_tensor_ids),
        },
        "transformations": [
            {"node_id": item.node_id, "action": item.action, "reason": item.reason}
            for item in partition.transformations
        ],
        "exclusions": [
            {"node_id": item.node_id, "reason": item.reason}
            for item in partition.exclusion_reasons
        ],
        "reasons": list(partition.reasons),
    }


def _cost_dict(cost: CostEstimate) -> Mapping[str, object]:
    ratio = cost.compute_to_transfer_ratio
    return {
        "threshold_version": cost.threshold_version,
        "output_tile": cost.output_tile,
        "boundary_transfer_bytes": cost.boundary_transfer_bytes,
        "dense_macs": cost.dense_macs,
        "weight_bits_4bit": cost.weight_bits_4bit,
        "bias_bits": cost.bias_bits,
        "parameter_bits": cost.parameter_bits,
        "activation_bytes": cost.activation_bytes,
        "estimated_cycles": cost.estimated_cycles,
        "compute_to_transfer_ratio": ratio if math.isfinite(ratio) else None,
        "compilable_not_recommended": cost.compilable_not_recommended,
        "reasons": list(cost.reasons),
    }


def _plain_metadata(value: object) -> object:
    """Detach immutable GraphIR metadata into JSON-native containers."""
    if isinstance(value, Mapping):
        return {str(key): _plain_metadata(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_metadata(item) for item in value]
    return value


@dataclass(frozen=True)
class AnalysisReport:
    """Complete deterministic result of the shared V2 analysis pipeline."""

    tensor_count: int
    node_count: int
    parameter_count: int
    importer: ImportReport
    graph_ir_sha256: str
    contract_sha256: Optional[str]
    decisions: Tuple[CapabilityDecision, ...]
    partition: PartitionIR
    costs: CostEstimate
    graph_metadata: Mapping[str, object]
    limitations: Tuple[str, ...] = _LIMITATIONS
    schema_version: str = ANALYSIS_SCHEMA_VERSION
    rtl_generated: bool = False

    @property
    def result(self) -> str:
        return _RESULT_LABELS[self.partition.mode]

    def to_dict(self) -> Mapping[str, object]:
        counts = {item.value: 0 for item in SupportClass}
        for decision in self.decisions:
            counts[decision.support_class.value] += 1
        return {
            "schema_version": self.schema_version,
            "result": self.result,
            "model": {
                "tensor_count": self.tensor_count,
                "node_count": self.node_count,
                "parameter_count": self.parameter_count,
            },
            "operator_support": {
                "total": len(self.decisions),
                "supported": counts[SupportClass.SUPPORTED.value],
                "software_fallback": counts[SupportClass.SOFTWARE_FALLBACK.value],
                "unsupported": counts[SupportClass.UNSUPPORTED.value],
            },
            "decisions": [_decision_dict(item) for item in self.decisions],
            "partition": _partition_dict(self.partition),
            "costs": _cost_dict(self.costs),
            "hashes": {
                "source_sha256": self.importer.source_sha256,
                "graph_ir_sha256": self.graph_ir_sha256,
                "contract_sha256": self.contract_sha256,
            },
            "importer": dict(self.importer.to_dict()),
            "graph_metadata": _plain_metadata(self.graph_metadata),
            "limitations": list(self.limitations),
            "rtl_generated": self.rtl_generated,
        }


def analyze_model(model_path: str, contract_path: Optional[str] = None) -> AnalysisReport:
    """Import, validate, classify, partition, and cost one model without RTL."""
    try:
        imported = import_model(model_path)
    except OSError as error:
        raise ImporterError("unable to read model source: {}".format(error)) from error
    graph = imported.graph
    graph.validate()
    contract = load_contract(contract_path) if contract_path is not None else None
    if contract is not None:
        validate_contract_against_graph(graph, contract)
    decisions = classify_graph(graph, contract)
    partition = partition_graph(graph, decisions, contract)
    costs = estimate_partition_cost(graph, partition)
    parameter_count = sum(math.prod(item.shape) for item in graph.constants)
    return AnalysisReport(
        tensor_count=len(graph.tensors),
        node_count=len(graph.nodes),
        parameter_count=parameter_count,
        importer=imported.report,
        graph_ir_sha256=graph_sha256(graph),
        contract_sha256=None if contract is None else contract.sha256,
        decisions=decisions,
        partition=partition,
        costs=costs,
        graph_metadata=graph.metadata,
    )
