import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import model2rtl.ucf_evidence as ucf_evidence
from model2rtl.ucf_evidence import (
    ClassMap,
    Evidence,
    EvidenceError,
    PreprocessingContract,
    PreprocessingEvidence,
    apply_preprocessing,
    require_verified_class_map,
    require_verified_preprocessing,
)


EXPECTED_CLASSES = (
    "Abuse",
    "Arrest",
    "Arson",
    "Assault",
    "Burglary",
    "Explosion",
    "Fighting",
    "NormalVideos",
    "RoadAccidents",
    "Robbery",
    "Shooting",
    "Shoplifting",
    "Stealing",
    "Vandalism",
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_H5_SHA256 = (
    "7411d46d5ab0900f46e732217b140d3f777dc028a7f74362300fd1d7dc0f1c12"
)


def test_unverified_preprocessing_blocks_feature_extraction():
    """Accepting an unresolved record would permit an unsupported transform."""
    record = PreprocessingEvidence(status="unresolved", candidates=[])

    with pytest.raises(EvidenceError, match="preprocessing is not verified"):
        require_verified_preprocessing(record)


def test_class_map_requires_all_fourteen_unique_outputs():
    """Accepting a partial map would attach labels to the wrong output indices."""
    with pytest.raises(EvidenceError, match="indices 0 through 13"):
        ClassMap(classes=("Abuse",), evidence=(), verified=True).validate()


def test_filesystem_order_is_not_evidence():
    """Treating directory order as provenance would invent training-time order."""
    evidence = Evidence(kind="filesystem_enumeration", source="Train/")

    with pytest.raises(EvidenceError, match="not training-time evidence"):
        ClassMap(
            classes=EXPECTED_CLASSES,
            evidence=(evidence,),
            verified=True,
        ).validate()


def make_contract(
    name,
    *,
    resize=(1, 1),
    interpolation="nearest",
    channel_order="RGB",
    dtype="float32",
    scale=1.0,
    offset=0.0,
    with_evidence=True,
    evidence_kind="exact_h5_training_source",
    artifact_sha256=EXPECTED_H5_SHA256,
    assertion_sha256=None,
):
    contract = PreprocessingContract(
        name=name,
        resize=resize,
        interpolation=interpolation,
        channel_order=channel_order,
        dtype=dtype,
        scale=scale,
        offset=offset,
    )
    if not with_evidence:
        return contract
    assertion_sha256 = assertion_sha256 or ucf_evidence.preprocessing_claim_sha256(
        contract
    )
    source = Evidence(
        kind=evidence_kind,
        source="https://example.test/exact-model-training.py",
        sha256="a" * 64,
        locator="lines 20-24",
        retrieved_at="2026-08-20",
        reasoning="The identity-linked source declares the complete transform.",
        claim="preprocessing_contract",
        artifact_sha256=artifact_sha256,
        assertion_sha256=assertion_sha256,
    )
    return replace(contract, evidence=(source,))


def test_apply_preprocessing_rejects_an_evidence_free_contract():
    """Direct execution must not bypass the verified preprocessing gate."""
    contract = make_contract(
        "divide_255",
        scale=1.0 / 255.0,
        with_evidence=False,
    )

    with pytest.raises(EvidenceError, match="exact-H5 preprocessing evidence"):
        apply_preprocessing(
            np.zeros((1, 1, 1, 3), dtype=np.uint8),
            contract,
        )


def test_preprocessing_evidence_must_link_the_exact_original_h5():
    """A source for a different model cannot authorize this transform."""
    contract = make_contract(
        "divide_255",
        scale=1.0 / 255.0,
        artifact_sha256="b" * 64,
    )

    with pytest.raises(EvidenceError, match="exact original H5"):
        apply_preprocessing(
            np.zeros((1, 1, 1, 3), dtype=np.uint8),
            contract,
        )


def test_preprocessing_evidence_must_establish_the_asserted_transform():
    """Evidence for another transform cannot authorize the requested affine."""
    contract = make_contract(
        "divide_255",
        scale=1.0 / 255.0,
        assertion_sha256="c" * 64,
    )

    with pytest.raises(EvidenceError, match="asserted preprocessing contract"):
        apply_preprocessing(
            np.zeros((1, 1, 1, 3), dtype=np.uint8),
            contract,
        )


def test_candidate_notebook_kind_never_verifies_preprocessing():
    """Topology and timestamp similarity are candidate facts, not provenance."""
    contract = make_contract(
        "divide_255",
        scale=1.0 / 255.0,
        evidence_kind="kaggle_candidate_notebook_source",
    )

    with pytest.raises(EvidenceError, match="does not establish preprocessing"):
        apply_preprocessing(
            np.zeros((1, 1, 1, 3), dtype=np.uint8),
            contract,
        )


def test_raw_uint8_executes_only_the_declared_cast():
    """Normalizing a raw-byte contract would change recovered model inputs."""
    images = np.array([[[[0, 128, 255]]]], dtype=np.uint8)

    result = apply_preprocessing(
        images,
        make_contract("raw_uint8", dtype="uint8"),
    )

    assert result.dtype == np.uint8
    np.testing.assert_array_equal(
        result,
        np.array([[[[0, 128, 255]]]], dtype=np.uint8),
    )


def test_raw_uint8_rejects_non_uint8_inputs_instead_of_truncating():
    """Fractional inputs must not be silently truncated by a raw-byte contract."""
    with pytest.raises(EvidenceError, match="input dtype uint8"):
        apply_preprocessing(
            np.array([[[[0.0, 127.5, 255.0]]]], dtype=np.float32),
            make_contract("raw_uint8", dtype="uint8"),
        )


def test_raw_uint8_rejects_out_of_range_inputs_instead_of_wrapping():
    """Values outside the byte range must not wrap during conversion."""
    with pytest.raises(EvidenceError, match="range 0 through 255"):
        apply_preprocessing(
            np.array([[[[0, 128, 256]]]], dtype=np.int16),
            make_contract("raw_uint8", dtype="uint8"),
        )


def test_divide_255_executes_the_declared_normalization():
    """Omitting the divisor would feed values 255 times too large."""
    images = np.array([[[[0, 127.5, 255]]]], dtype=np.float32)

    result = apply_preprocessing(
        images,
        make_contract("divide_255", scale=1.0 / 255.0),
    )

    assert result.dtype == np.float32
    np.testing.assert_allclose(result, [[[[0.0, 0.5, 1.0]]]], rtol=0, atol=1e-7)


def test_keras_densenet_contract_uses_imagenet_channel_statistics():
    """Replacing Keras DenseNet normalization with divide-by-255 changes features."""
    images = np.array([[[[255.0, 255.0, 255.0]]]], dtype=np.float32)
    scale = tuple(1.0 / (255.0 * value) for value in (0.229, 0.224, 0.225))
    offset = tuple(
        -value / std
        for value, std in zip(
            (0.485, 0.456, 0.406),
            (0.229, 0.224, 0.225),
        )
    )

    result = apply_preprocessing(
        images,
        make_contract(
            "keras_densenet_preprocess_input",
            scale=scale,
            offset=offset,
        ),
    )

    np.testing.assert_allclose(
        result,
        [[[[2.2489083, 2.4285715, 2.64]]]],
        rtol=0,
        atol=1e-6,
    )


def test_affine_contract_applies_per_channel_scale_offset_and_bgr_order():
    """Ignoring affine vectors or channel order would execute a different contract."""
    contract = make_contract(
        "affine",
        channel_order="BGR",
        scale=(1.0, 2.0, 3.0),
        offset=(10.0, 20.0, 30.0),
    )

    result = apply_preprocessing(
        np.array([[[[1.0, 2.0, 3.0]]]], dtype=np.float32),
        contract,
    )

    np.testing.assert_allclose(result, [[[[13.0, 24.0, 33.0]]]])


def test_nearest_resize_uses_explicit_floor_mapped_source_indices():
    """Nearest resizing must execute the declared deterministic index mapping."""
    image = np.array(
        [
            [[0, 0, 0], [10, 10, 10]],
            [[20, 20, 20], [30, 30, 30]],
        ],
        dtype=np.float32,
    )

    result = apply_preprocessing(
        image,
        make_contract("affine", resize=(4, 4)),
    )

    assert result.shape == (4, 4, 3)
    np.testing.assert_array_equal(
        result[..., 0],
        [
            [0, 0, 10, 10],
            [0, 0, 10, 10],
            [20, 20, 30, 30],
            [20, 20, 30, 30],
        ],
    )


def test_bilinear_resize_uses_half_pixel_centers():
    """Bilinear resizing must not depend on an imaging-library default."""
    image = np.array(
        [
            [[0, 10, 20], [10, 20, 30]],
            [[20, 30, 40], [30, 40, 50]],
        ],
        dtype=np.float32,
    )

    result = apply_preprocessing(
        image,
        make_contract("affine", resize=(1, 1), interpolation="bilinear"),
    )

    assert result.shape == (1, 1, 3)
    np.testing.assert_allclose(result, [[[15.0, 25.0, 35.0]]], rtol=0, atol=1e-7)


def test_undeclared_resize_algorithm_is_rejected():
    """Unsupported interpolation must fail instead of selecting a hidden default."""
    with pytest.raises(EvidenceError, match="unsupported interpolation"):
        apply_preprocessing(
            np.zeros((2, 2, 3), dtype=np.float32),
            make_contract("affine", resize=(3, 3), interpolation="bicubic"),
        )


def test_unsupported_transform_fails_closed():
    """Falling through on an unknown name would silently guess preprocessing."""
    with pytest.raises(EvidenceError, match="unsupported preprocessing contract"):
        apply_preprocessing(
            np.zeros((1, 1, 1, 3), dtype=np.uint8),
            make_contract("guess_from_accuracy"),
        )


def exact_class_map_evidence(
    *,
    kind="exact_h5_class_indices",
    artifact_sha256=EXPECTED_H5_SHA256,
    assertion_sha256=None,
):
    return Evidence(
        kind=kind,
        source="https://example.test/exact-class-indices.json",
        sha256="d" * 64,
        locator="$.class_indices",
        retrieved_at="2026-08-20",
        reasoning="The identity-linked sidecar maps every output index.",
        claim="class_map",
        artifact_sha256=artifact_sha256,
        assertion_sha256=(
            assertion_sha256
            or ucf_evidence.class_map_claim_sha256(EXPECTED_CLASSES)
        ),
    )


def test_verified_preprocessing_requires_complete_documentary_evidence():
    """A status string alone must not promote an unsupported preprocessing claim."""
    unsupported = make_contract(
        "divide_255",
        scale=1.0 / 255.0,
        with_evidence=False,
    )
    record = PreprocessingEvidence(status="verified", contract=unsupported)

    with pytest.raises(EvidenceError, match="documentary evidence"):
        require_verified_preprocessing(record)


def test_verified_preprocessing_returns_an_exact_supported_contract():
    """Rejecting a complete source-backed contract would block valid extraction."""
    contract = make_contract(
        "divide_255",
        resize=(64, 64),
        scale=1.0 / 255.0,
    )

    assert require_verified_preprocessing(
        PreprocessingEvidence(
            status="verified",
            contract=contract,
            evidence=contract.evidence,
        )
    ) is contract


def test_empirical_characterization_cannot_verify_preprocessing():
    """Unlabelled activation behavior is not documentary contract evidence."""
    empirical = Evidence(
        kind="empirical_characterization",
        source="TRAIN frames",
        sha256="b" * 64,
        locator="candidate raw_uint8",
        retrieved_at="2026-08-20",
        reasoning="Characterizes activations without labels.",
    )
    contract = PreprocessingContract(
        name="divide_255",
        resize=(64, 64),
        interpolation="nearest",
        channel_order="RGB",
        dtype="float32",
        scale=1.0 / 255.0,
        offset=0.0,
        evidence=(empirical,),
    )

    with pytest.raises(EvidenceError, match="cannot verify"):
        require_verified_preprocessing(
            PreprocessingEvidence(status="verified", contract=contract)
        )


def test_named_transform_rejects_a_contradictory_affine():
    """A divide_255 name with raw scaling would execute an ambiguous contract."""
    with pytest.raises(EvidenceError, match="divide_255"):
        apply_preprocessing(
            np.zeros((1, 1, 1, 3), dtype=np.uint8),
            make_contract("divide_255", scale=1.0),
        )


def test_verified_class_map_requires_documentary_evidence():
    """A complete label tuple without provenance must remain unverified."""
    with pytest.raises(EvidenceError, match="documentary evidence"):
        require_verified_class_map(
            ClassMap(classes=EXPECTED_CLASSES, evidence=(), verified=True)
        )


def test_verified_class_map_preserves_the_source_backed_output_order():
    """A complete training-source mapping must be returned without reordering."""
    record = ClassMap(
        classes=EXPECTED_CLASSES,
        evidence=(exact_class_map_evidence(),),
        verified=True,
    )

    assert require_verified_class_map(record) is record


def test_class_map_evidence_must_link_the_exact_original_h5():
    """A class sidecar for another model cannot name these output neurons."""
    record = ClassMap(
        classes=EXPECTED_CLASSES,
        evidence=(exact_class_map_evidence(artifact_sha256="e" * 64),),
        verified=True,
    )

    with pytest.raises(EvidenceError, match="exact original H5"):
        require_verified_class_map(record)


def test_class_map_evidence_must_establish_the_asserted_order():
    """A sidecar digest for another ordering cannot authorize this mapping."""
    record = ClassMap(
        classes=EXPECTED_CLASSES,
        evidence=(exact_class_map_evidence(assertion_sha256="f" * 64),),
        verified=True,
    )

    with pytest.raises(EvidenceError, match="asserted class map"):
        require_verified_class_map(record)


def test_topology_similarity_kind_never_verifies_a_class_map():
    """A 14-output topology establishes width, not output-neuron names."""
    record = ClassMap(
        classes=EXPECTED_CLASSES,
        evidence=(exact_class_map_evidence(kind="h5_model_config_attribute"),),
        verified=True,
    )

    with pytest.raises(EvidenceError, match="does not establish class order"):
        require_verified_class_map(record)


def test_unverified_class_map_blocks_label_metrics():
    """A provisional ordered tuple must not enable label-based metrics."""
    with pytest.raises(EvidenceError, match="class map is not verified"):
        require_verified_class_map(
            ClassMap(classes=EXPECTED_CLASSES, evidence=(), verified=False)
        )


def test_preprocessing_report_persists_a_fail_closed_outcome():
    """A documentary gap must be machine-readable, not hidden in prose."""
    report = json.loads(
        (REPOSITORY_ROOT / "reports" / "ucf_preprocessing.json").read_text()
    )

    assert report["status"] == "unresolved"
    assert report["contract"] is None
    assert report["blocks_feature_extraction"] is True
    assert report["research_order"] == [
        "huggingface_model_revision_and_history",
        "uploader_profile_and_linked_github",
        "attached_public_kaggle_notebooks",
        "h5_metadata",
    ]
    assert all(
        len(item["sha256"]) == 64 and item["locator"]
        for item in report["evidence"]
    )


def test_preprocessing_report_persists_bounded_train_only_characterization():
    """Fallback evidence must be reproducible without labels or TEST leakage."""
    report = json.loads(
        (REPOSITORY_ROOT / "reports" / "ucf_preprocessing.json").read_text()
    )
    fallback = report["controlled_fallback"]
    selection = fallback["selection"]

    assert fallback["status"] == "completed_non_verifying"
    assert fallback["used_train_frames"] is True
    assert fallback["used_labels"] is False
    assert fallback["used_test_frames"] is False
    assert fallback["accuracy_scored"] is False
    assert fallback["candidate_ranking_performed"] is False
    assert 1 <= selection["sample_count"] <= 16
    assert selection["split"] == "TRAIN"
    assert selection["seed"] == 20260820
    assert len(selection["subset_sha256"]) == 64
    assert len(selection["samples"]) == selection["sample_count"]
    assert [item["member_path"] for item in selection["samples"]] == sorted(
        item["member_path"] for item in selection["samples"]
    )
    assert all(
        item["member_path"].startswith("Train/")
        for item in selection["samples"]
    )
    assert all("label" not in item for item in selection["samples"])
    assert {item["candidate"] for item in fallback["results"]} == {
        "raw_uint8",
        "divide_255",
        "keras_densenet_preprocess_input",
        "matching_notebook_declared_composition",
    }
    assert all(
        item["sample_subset_sha256"] == selection["subset_sha256"]
        for item in fallback["results"]
    )
    assert all(
        item["output"]["finite_fraction"] == 1.0
        for item in fallback["results"]
    )
    assert all(item["activations"] for item in fallback["results"])


def test_class_map_artifact_is_ordered_but_explicitly_unverified():
    """A provisional display order must never enable label-based metrics."""
    record = json.loads(
        (REPOSITORY_ROOT / "ucfout" / "class_map.json").read_text()
    )

    assert record["status"] == "unresolved"
    assert record["verified"] is False
    assert record["blocks_label_metrics"] is True
    assert [item["index"] for item in record["output_map"]] == list(range(14))
    assert tuple(item["class_name"] for item in record["output_map"]) == EXPECTED_CLASSES
    assert record["output_map_role"] == "provisional_candidate_only"
