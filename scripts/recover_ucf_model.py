#!/usr/bin/env python3
"""Inspect an immutable legacy UCF Keras H5 in the isolated Keras 2.15 env."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys
import traceback

from model2rtl.legacy_h5 import analyze_h5, verify_source_hash


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    inspect = subcommands.add_parser(
        "inspect", help="verify, inspect, and directly load an original legacy H5"
    )
    inspect.add_argument("--model", required=True, help="immutable original H5 path")
    inspect.add_argument(
        "--expected-sha256", required=True, help="required SHA-256 of the original H5"
    )
    inspect.add_argument(
        "--analysis-json", required=True, help="path for the compact JSON inspection report"
    )
    return parser


def _shape(shape) -> list:
    return [None if dim is None else int(dim) for dim in shape]


def inspect(args: argparse.Namespace) -> int:
    # Keep this before the TensorFlow import: an altered source must never be
    # passed to any executable loader.
    source_hash = verify_source_hash(args.model, args.expected_sha256)
    analysis = analyze_h5(args.model)

    try:
        import h5py
        import tensorflow as tf

        model = tf.keras.models.load_model(args.model, compile=False)
    except Exception:
        traceback.print_exc()
        return 1

    result = analysis.to_dict()
    result["legacy_loader"] = {
        "status": "loaded_directly",
        "sanitization_occurred": False,
        "source_sha256": source_hash,
        "python_version": sys.version,
        "platform": platform.platform(),
        "tensorflow_version": tf.__version__,
        "keras_version": getattr(tf.keras, "__version__", None),
        "h5py_version": h5py.__version__,
        "input_shape": _shape(model.input_shape),
        "output_shape": _shape(model.output_shape),
    }
    output = Path(args.analysis_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("verified SHA-256: %s" % source_hash)
    print("loaded original H5 directly: input %s -> output %s" % (model.input_shape, model.output_shape))
    print("sanitization occurred: false")
    print("wrote %s" % output)
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return inspect(args)
    raise AssertionError("unhandled command")


if __name__ == "__main__":
    raise SystemExit(main())
