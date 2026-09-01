"""Evidence-gated preprocessing and output-label contracts for UCF-Crime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import re
from typing import Any, Optional, Sequence, Tuple

import numpy as np


class EvidenceError(ValueError):
    """Raised when documentary evidence does not support a requested claim."""


EXACT_H5_SHA256 = (
    "7411d46d5ab0900f46e732217b140d3f777dc028a7f74362300fd1d7dc0f1c12"
)
_PREPROCESSING_EVIDENCE_KINDS = {
    "exact_h5_training_source",
    "exact_h5_preprocessing_manifest",
}
_CLASS_MAP_EVIDENCE_KINDS = {
    "exact_h5_training_source",
    "exact_h5_class_indices",
    "exact_h5_label_map",
}
_DENSENET_SCALE = tuple(
    1.0 / (255.0 * value) for value in (0.229, 0.224, 0.225)
)
_DENSENET_OFFSET = tuple(
    -value / std
    for value, std in zip(
        (0.485, 0.456, 0.406),
        (0.229, 0.224, 0.225),
    )
)


@dataclass(frozen=True)
class Evidence:
    """A content-addressed documentary source and its relevant location."""

    kind: str
    source: str
    sha256: str = ""
    locator: str = ""
    retrieved_at: str = ""
    reasoning: str = ""
    claim: str = ""
    artifact_sha256: str = ""
    assertion_sha256: str = ""

    def validate(self) -> "Evidence":
        missing = [
            field_name
            for field_name in ("kind", "source", "locator", "retrieved_at", "reasoning")
            if not getattr(self, field_name)
        ]
        if missing:
            raise EvidenceError(
                "evidence is missing required fields: %s" % ", ".join(missing)
            )
        if re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256) is None:
            raise EvidenceError("evidence SHA-256 must contain 64 hexadecimal digits")
        try:
            date.fromisoformat(self.retrieved_at)
        except ValueError as exc:
            raise EvidenceError("evidence retrieval date must be ISO YYYY-MM-DD") from exc
        for field_name in ("artifact_sha256", "assertion_sha256"):
            value = getattr(self, field_name)
            if value and re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
                raise EvidenceError(
                    "%s must contain 64 hexadecimal digits" % field_name
                )
        return self


@dataclass(frozen=True)
class PreprocessingContract:
    """An explicit image transform contract supported by evidence."""

    name: str
    resize: Tuple[int, int]
    interpolation: str
    channel_order: str
    dtype: str
    scale: Any
    offset: Any
    evidence: Tuple[Evidence, ...] = ()

    def validate(self) -> "PreprocessingContract":
        _validate_transform_definition(self)
        _require_semantic_evidence(
            self.evidence,
            accepted_kinds=_PREPROCESSING_EVIDENCE_KINDS,
            claim="preprocessing_contract",
            assertion_sha256=preprocessing_claim_sha256(self),
            subject="preprocessing",
        )
        return self


def _validate_transform_definition(
    contract: PreprocessingContract,
) -> PreprocessingContract:
    if (
        len(contract.resize) != 2
        or any(
            not isinstance(value, int) or value <= 0
            for value in contract.resize
        )
    ):
        raise EvidenceError("resize must be two positive integer dimensions")
    if contract.interpolation not in {"nearest", "bilinear"}:
        raise EvidenceError(
            "unsupported interpolation: %s" % contract.interpolation
        )
    if contract.channel_order not in {"RGB", "BGR"}:
        raise EvidenceError(
            "unsupported channel order: %s" % contract.channel_order
        )
    try:
        dtype = np.dtype(contract.dtype)
    except TypeError as exc:
        raise EvidenceError(
            "unsupported preprocessing dtype: %s" % contract.dtype
        ) from exc
    scale = _affine_vector(contract.scale, "scale")
    offset = _affine_vector(contract.offset, "offset")
    if contract.name == "raw_uint8":
        if (
            dtype != np.dtype("uint8")
            or not _matches(scale, 1.0)
            or not _matches(offset, 0.0)
        ):
            raise EvidenceError(
                "raw_uint8 requires uint8 dtype, scale 1, and offset 0"
            )
    elif contract.name == "divide_255":
        if (
            dtype != np.dtype("float32")
            or not _matches(scale, 1.0 / 255.0)
            or not _matches(offset, 0.0)
        ):
            raise EvidenceError(
                "divide_255 requires float32 dtype, scale 1/255, and offset 0"
            )
    elif contract.name == "keras_densenet_preprocess_input":
        if (
            dtype != np.dtype("float32")
            or not _matches(scale, _DENSENET_SCALE)
            or not _matches(offset, _DENSENET_OFFSET)
        ):
            raise EvidenceError(
                "keras_densenet_preprocess_input requires the Keras ImageNet "
                "channel scale and offset"
            )
    elif contract.name != "affine":
        raise EvidenceError(
            "unsupported preprocessing contract: %s" % contract.name
        )
    return contract


@dataclass(frozen=True)
class PreprocessingEvidence:
    """Evidence review outcome for preprocessing recovery."""

    status: str
    contract: Optional[PreprocessingContract] = None
    candidates: Sequence[Any] = field(default_factory=tuple)
    evidence: Tuple[Evidence, ...] = ()

    def validate(self) -> "PreprocessingEvidence":
        if self.status not in {"verified", "unresolved"}:
            raise EvidenceError("preprocessing status must be verified or unresolved")
        for item in self.evidence:
            item.validate()
        if self.status == "verified":
            if self.contract is None:
                raise EvidenceError("preprocessing is not verified")
            self.contract.validate()
        return self


@dataclass(frozen=True)
class ClassMap:
    """Ordered output-neuron labels and their documentary provenance."""

    classes: Tuple[str, ...]
    evidence: Tuple[Evidence, ...]
    verified: bool

    def validate(self) -> "ClassMap":
        if len(self.classes) != 14 or len(set(self.classes)) != 14:
            raise EvidenceError(
                "class map must uniquely cover output indices 0 through 13"
            )
        if self.verified and any(
            item.kind == "filesystem_enumeration" for item in self.evidence
        ):
            raise EvidenceError(
                "filesystem enumeration is not training-time evidence"
            )
        for item in self.evidence:
            item.validate()
        if self.verified:
            _require_semantic_evidence(
                self.evidence,
                accepted_kinds=_CLASS_MAP_EVIDENCE_KINDS,
                claim="class_map",
                assertion_sha256=class_map_claim_sha256(self.classes),
                subject="class order",
            )
        return self


def require_verified_preprocessing(
    record: PreprocessingEvidence,
) -> PreprocessingContract:
    """Return a supported transform or fail before feature extraction."""
    if record.status != "verified" or record.contract is None:
        raise EvidenceError("preprocessing is not verified")
    record.validate()
    return record.contract


def require_verified_class_map(record: ClassMap) -> ClassMap:
    """Return a supported output ordering or fail before label-based metrics."""
    record.validate()
    if not record.verified:
        raise EvidenceError("class map is not verified")
    return record


def preprocessing_claim_sha256(contract: PreprocessingContract) -> str:
    """Hash the exact transform assertion independently of its evidence."""
    payload = {
        "channel_order": contract.channel_order,
        "dtype": np.dtype(contract.dtype).name,
        "interpolation": contract.interpolation,
        "name": contract.name,
        "offset": _canonical_affine(contract.offset),
        "resize": list(contract.resize),
        "scale": _canonical_affine(contract.scale),
    }
    return _canonical_sha256(payload)


def class_map_claim_sha256(classes: Sequence[str]) -> str:
    """Hash an index-preserving output-neuron label assertion."""
    return _canonical_sha256(
        {
            "classes": list(classes),
            "indices": list(range(len(classes))),
        }
    )


def apply_preprocessing(
    images: np.ndarray,
    contract: PreprocessingContract,
) -> np.ndarray:
    """Execute one already-selected preprocessing contract without inference."""
    contract.validate()
    array = np.asarray(images)
    if array.ndim not in {3, 4} or array.shape[-1] != 3:
        raise EvidenceError("preprocessing expects RGB HWC or NHWC images")
    if contract.name == "raw_uint8":
        if array.size and (
            not np.all(np.isfinite(array))
            or np.min(array) < 0
            or np.max(array) > 255
        ):
            raise EvidenceError("raw_uint8 input values must be in range 0 through 255")
        if array.dtype != np.dtype("uint8"):
            raise EvidenceError("raw_uint8 requires input dtype uint8")
    if contract.channel_order == "BGR":
        array = array[..., ::-1]
    array = _resize_images(array, contract.resize, contract.interpolation)
    output_dtype = np.dtype(contract.dtype)
    if contract.name == "raw_uint8":
        if array.dtype.kind == "f":
            array = np.rint(array)
        return array.astype(output_dtype)
    result = array.astype(output_dtype)
    return result * np.asarray(contract.scale, dtype=output_dtype) + np.asarray(
        contract.offset,
        dtype=output_dtype,
    )


def _affine_vector(value: Any, field_name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(
            "%s must be a finite scalar or RGB vector" % field_name
        ) from exc
    if array.shape not in {(), (3,)} or not np.all(np.isfinite(array)):
        raise EvidenceError("%s must be a finite scalar or RGB vector" % field_name)
    return array


def _matches(actual: np.ndarray, expected: Any) -> bool:
    return bool(np.allclose(actual, np.asarray(expected), rtol=0.0, atol=1e-12))


def _require_semantic_evidence(
    evidence: Tuple[Evidence, ...],
    *,
    accepted_kinds: set[str],
    claim: str,
    assertion_sha256: str,
    subject: str,
) -> None:
    if not evidence:
        raise EvidenceError(
            "verified claims require documentary evidence: exact-H5 %s evidence"
            % subject
        )
    for item in evidence:
        item.validate()
    qualifying = [item for item in evidence if item.kind in accepted_kinds]
    if not qualifying:
        prefix = ""
        if any(
            item.kind in {"empirical_characterization", "filesystem_enumeration"}
            for item in evidence
        ):
            prefix = "empirical or enumerated observations cannot verify; "
        raise EvidenceError(
            prefix + "evidence kind does not establish %s" % subject
        )
    for item in qualifying:
        if item.artifact_sha256 != EXACT_H5_SHA256:
            raise EvidenceError(
                "%s evidence must identity-link the exact original H5" % subject
            )
        if item.claim != claim or item.assertion_sha256 != assertion_sha256:
            asserted_subject = (
                "preprocessing contract"
                if claim == "preprocessing_contract"
                else "class map"
            )
            raise EvidenceError(
                "%s evidence does not establish the asserted %s"
                % (subject, asserted_subject)
            )


def _canonical_affine(value: Any) -> Any:
    array = _affine_vector(value, "affine value")
    if array.shape == ():
        return float(array)
    return [float(item) for item in array]


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resize_images(
    images: np.ndarray,
    target: Tuple[int, int],
    interpolation: str,
) -> np.ndarray:
    """Resize using nearest floor indices or edge-clamped half-pixel bilinear."""
    squeeze = images.ndim == 3
    batch = images[np.newaxis, ...] if squeeze else images
    source_height, source_width = batch.shape[1:3]
    target_height, target_width = target
    if (source_height, source_width) == target:
        return images
    if interpolation == "nearest":
        y = np.floor(
            np.arange(target_height, dtype=np.float64)
            * source_height
            / target_height
        ).astype(np.int64)
        x = np.floor(
            np.arange(target_width, dtype=np.float64)
            * source_width
            / target_width
        ).astype(np.int64)
        resized = batch[:, y, :, :][:, :, x, :]
    elif interpolation == "bilinear":
        resized = _resize_bilinear_half_pixel(
            batch,
            target_height,
            target_width,
        )
    else:
        raise EvidenceError("unsupported interpolation: %s" % interpolation)
    return resized[0] if squeeze else resized


def _resize_bilinear_half_pixel(
    batch: np.ndarray,
    target_height: int,
    target_width: int,
) -> np.ndarray:
    source_height, source_width = batch.shape[1:3]
    y = (
        (np.arange(target_height, dtype=np.float64) + 0.5)
        * source_height
        / target_height
        - 0.5
    )
    x = (
        (np.arange(target_width, dtype=np.float64) + 0.5)
        * source_width
        / target_width
        - 0.5
    )
    y0_unclipped = np.floor(y).astype(np.int64)
    x0_unclipped = np.floor(x).astype(np.int64)
    y_weight = y - y0_unclipped
    x_weight = x - x0_unclipped
    y0 = np.clip(y0_unclipped, 0, source_height - 1)
    x0 = np.clip(x0_unclipped, 0, source_width - 1)
    y1 = np.clip(y0_unclipped + 1, 0, source_height - 1)
    x1 = np.clip(x0_unclipped + 1, 0, source_width - 1)
    values = batch.astype(np.float64, copy=False)
    top_left = values[:, y0, :, :][:, :, x0, :]
    top_right = values[:, y0, :, :][:, :, x1, :]
    bottom_left = values[:, y1, :, :][:, :, x0, :]
    bottom_right = values[:, y1, :, :][:, :, x1, :]
    wy = y_weight.reshape(1, target_height, 1, 1)
    wx = x_weight.reshape(1, 1, target_width, 1)
    top = top_left * (1.0 - wx) + top_right * wx
    bottom = bottom_left * (1.0 - wx) + bottom_right * wx
    return top * (1.0 - wy) + bottom * wy
