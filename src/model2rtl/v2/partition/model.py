"""Immutable records for V2 partition and advisory cost analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TransformationRecord:
    node_id: str
    action: str
    reason: str


@dataclass(frozen=True)
class ExclusionReason:
    node_id: str
    reason: str


@dataclass(frozen=True)
class PartitionIR:
    mode: str
    selected_output_tensor_id: str
    software_prefix_node_ids: Tuple[str, ...]
    rtl_node_ids: Tuple[str, ...]
    software_postfix_node_ids: Tuple[str, ...]
    input_boundary_tensor_ids: Tuple[str, ...]
    output_boundary_tensor_ids: Tuple[str, ...]
    transformations: Tuple[TransformationRecord, ...]
    exclusion_reasons: Tuple[ExclusionReason, ...]
    reasons: Tuple[str, ...]

    @property
    def software_prefix(self) -> Tuple[str, ...]:
        return self.software_prefix_node_ids

    @property
    def rtl_region(self) -> Tuple[str, ...]:
        return self.rtl_node_ids

    @property
    def software_postfix(self) -> Tuple[str, ...]:
        return self.software_postfix_node_ids

    @property
    def boundary_tensor_ids(self) -> Tuple[str, ...]:
        return self.input_boundary_tensor_ids + self.output_boundary_tensor_ids


@dataclass(frozen=True)
class CostThresholds:
    version: str = "model2rtl-cost-thresholds-v1"
    minimum_compute_to_transfer_ratio: float = 16.0
    trivial_output_layer_max_macs: int = 4096


@dataclass(frozen=True)
class CostEstimate:
    threshold_version: str
    output_tile: int
    boundary_transfer_bytes: int
    dense_macs: int
    weight_bits_4bit: int
    bias_bits: int
    parameter_bits: int
    activation_bytes: int
    estimated_cycles: int
    compute_to_transfer_ratio: float
    compilable_not_recommended: bool
    reasons: Tuple[str, ...]

    @property
    def transfer_bytes(self) -> int:
        return self.boundary_transfer_bytes

    @property
    def macs(self) -> int:
        return self.dense_macs

    @property
    def estimated_activation_bytes(self) -> int:
        return self.activation_bytes

    @property
    def tiled_cycles(self) -> int:
        return self.estimated_cycles
