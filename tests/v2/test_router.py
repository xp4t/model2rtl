"""Compatibility routing between the frozen V1 CLI and additive V2 commands."""

from __future__ import annotations

import pytest

from model2rtl import router


@pytest.mark.parametrize("command", ["analyze", "compile"])
def test_leading_v2_command_routes_only_remaining_arguments(monkeypatch, command):
    """Keeping the subcommand would make the V2 parser see an invalid model path."""
    calls = []
    monkeypatch.setattr(router.v1_cli, "main", lambda argv: calls.append(("v1", argv)))
    monkeypatch.setattr(
        router.v2_cli,
        "main",
        lambda argv, command=None: calls.append(("v2", command, argv)) or 17,
    )

    rc = router.main([command, "model.onnx", "--json", "analysis.json"])

    assert rc == 17
    assert calls == [("v2", command, ["model.onnx", "--json", "analysis.json"])]


@pytest.mark.parametrize(
    "legacy_argv",
    [
        [],
        ["--model", "legacy.h5", "--output", "rtl"],
        ["--indices", "weights.npz", "--output", "rtl"],
        ["--help"],
        ["legacy-error", "--unknown", "value"],
    ],
)
def test_every_non_v2_argument_sequence_is_forwarded_unchanged(
    monkeypatch, legacy_argv
):
    """Pre-parsing legacy argv would alter V1 help and parser-error behavior."""
    received = []
    monkeypatch.setattr(
        router.v1_cli,
        "main",
        lambda argv: received.append(argv) or 23,
    )
    monkeypatch.setattr(
        router.v2_cli,
        "main",
        lambda argv, command=None: pytest.fail("non-V2 argv was routed to V2"),
    )

    rc = router.main(legacy_argv)

    assert rc == 23
    assert received == [legacy_argv]
    assert received[0] is legacy_argv
