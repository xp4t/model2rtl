"""Lexical compatibility router for the additive V2 command surface."""

from __future__ import annotations

import sys

from . import cli as v1_cli
from .v2 import cli as v2_cli


def main(argv=None) -> int:
    """Route only a leading V2 command; preserve every V1 argv sequence."""
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] in {"analyze", "compile"}:
        return v2_cli.main(arguments[1:], command=arguments[0])
    return v1_cli.main(arguments)
