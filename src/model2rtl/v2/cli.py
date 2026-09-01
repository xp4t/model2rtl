"""Command-line interface for V2 analysis and reserved compilation."""

from __future__ import annotations

import argparse
import json
import sys

from . import compiler
from .importers import ImporterError
from .ir import GraphValidationError
from .model_contract import ContractError


COMPILE_UNAVAILABLE = (
    "model2rtl V2: [E200] compile is unavailable in Milestone 1; "
    "no output was written."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="model2rtl")
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="analyze a model without generating RTL")
    analyze.add_argument("model", metavar="MODEL")
    analyze.add_argument("--contract", metavar="YAML")
    analyze.add_argument("--json", metavar="REPORT")

    compile_parser = commands.add_parser("compile", help="reserved V2 compile command")
    compile_parser.add_argument("--model", required=True, metavar="MODEL")
    compile_parser.add_argument("--contract", metavar="YAML")
    compile_parser.add_argument("--calibration", metavar="NPZ")
    compile_parser.add_argument("--output", required=True, metavar="DIR")
    return parser


def _print_analysis(report: compiler.AnalysisReport) -> None:
    document = report.to_dict()
    model = document["model"]
    operators = document["operator_support"]
    partition = document["partition"]
    costs = document["costs"]
    importer = document["importer"]
    graph_metadata = document["graph_metadata"]
    recovery = graph_metadata.get("keras_recovery", {})
    print("IMPORTER")
    print(
        "  frontend: {frontend}  format: {source_format}".format(**importer)
    )
    if recovery:
        print("  recovery: {}".format(recovery.get("mode", "unknown")))
        print(
            "  executable: {}  weights verified: {}".format(
                "yes" if recovery.get("executable") else "no",
                "yes" if recovery.get("weights_verified") else "no",
            )
        )
    print("MODEL")
    print(
        "  tensors: {tensor_count}  nodes: {node_count}  parameters: {parameter_count}".format(
            **model
        )
    )
    print("OPERATORS")
    print(
        "  supported: {supported}  software fallback: {software_fallback}  "
        "unsupported: {unsupported}".format(**operators)
    )
    print("PARTITION")
    print("  execution mode: {}".format(partition["execution_mode"]))
    print("  RTL nodes: {}".format(", ".join(partition["rtl_node_ids"]) or "none"))
    print("COSTS")
    print(
        "  Dense MACs: {dense_macs}  boundary bytes: {boundary_transfer_bytes}  "
        "estimated cycles: {estimated_cycles}".format(**costs)
    )
    print("RESULT: {}".format(report.result))
    print("RTL generated: no")


def _write_json(path: str, report: compiler.AnalysisReport) -> None:
    text = json.dumps(
        report.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"
    with open(path, "w", encoding="utf-8") as destination:
        destination.write(text)


def main(argv=None, *, command=None) -> int:
    """Run direct subparser argv or argv already stripped by the console router."""
    parse_argv = argv
    if command is not None:
        parse_argv = [command] + ([] if argv is None else list(argv))
    args = build_parser().parse_args(parse_argv)
    if args.command == "compile":
        print(COMPILE_UNAVAILABLE, file=sys.stderr)
        return 2
    try:
        report = compiler.analyze_model(args.model, args.contract)
    except (ImporterError, ContractError, GraphValidationError) as error:
        print("model2rtl V2: {}".format(error), file=sys.stderr)
        return 2
    if args.json is not None:
        try:
            _write_json(args.json, report)
        except OSError as error:
            print(
                "model2rtl V2: unable to write analysis JSON: {}".format(error),
                file=sys.stderr,
            )
            return 2
    _print_analysis(report)
    return 0
