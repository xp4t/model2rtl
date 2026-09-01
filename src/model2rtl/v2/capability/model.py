"""Immutable records for V2 operator capability analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SupportClass(str, Enum):
    SUPPORTED = "supported"
    SOFTWARE_FALLBACK = "software_fallback"
    UNSUPPORTED = "unsupported"


class InferenceAction(str, Enum):
    LOWER = "lower"
    REMOVE = "remove"
    ELIDE = "elide"
    SOFTWARE = "software"
    REJECT = "reject"


@dataclass(frozen=True)
class CapabilityEntry:
    op_type: str
    support_class: SupportClass
    inference_action: InferenceAction
    validator_key: str
    shape_rule_key: str
    quantization_rule_key: Optional[str]
    lowering_rule_key: Optional[str]
    golden_rule_key: Optional[str]
    reason: str
    roadmap_label: str


@dataclass(frozen=True)
class CapabilityDecision:
    node_id: str
    op_type: str
    support_class: SupportClass
    inference_action: InferenceAction
    reason: str
    validator_key: str
    shape_rule_key: str
    quantization_rule_key: Optional[str]
    lowering_rule_key: Optional[str]
    golden_rule_key: Optional[str]
    roadmap_label: str
