#!/usr/bin/env python3
"""Stage 1: generate the fixed Multiply-Select-Add compute fabric.

    scripts/gen_compute_fabric.py  ->  rtl/mnist_mlp_fabric.v

WEIGHT INDEPENDENCE IS THE POINT OF THIS SCRIPT.

It reads the topology, K and the frozen Stage-0 arithmetic contract from
src/model2rtl/contract.py.  It never opens model/mnist_weights_indices.npz and
never sees a trained weight index or a trained bias.  Running it against a
different trained model must produce a byte-identical file; Stage-1 tests prove
that by regenerating with a substituted NPZ and comparing SHA-256.

No weight ROM is generated here.  That is Stage 2.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl.fabric import FabricConfig, check_production_widths, derive_widths  # noqa: E402
from model2rtl.verilog_emit import emit_fabric_verilog  # noqa: E402


def generate(cfg: FabricConfig) -> str:
    check_production_widths(cfg)
    return emit_fabric_verilog(cfg)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "rtl", "mnist_mlp_fabric.v"))
    ap.add_argument("--n-in", type=int, default=None)
    ap.add_argument("--n-hidden", type=int, default=None)
    ap.add_argument("--n-out", type=int, default=None)
    ap.add_argument("--module-name", default=None)
    args = ap.parse_args()

    kwargs = {}
    if args.n_in is not None:
        kwargs["n_in"] = args.n_in
    if args.n_hidden is not None:
        kwargs["n_hidden"] = args.n_hidden
    if args.n_out is not None:
        kwargs["n_out"] = args.n_out
    if args.module_name is not None:
        kwargs["module_name"] = args.module_name
    cfg = FabricConfig(**kwargs)

    text = generate(cfg)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(text)

    w = derive_widths(cfg)
    print("wrote %s" % os.path.relpath(args.out, ROOT))
    print("  topology            : %d -> %d -> %d, K = %d"
          % (cfg.n_in, cfg.n_hidden, cfg.n_out, cfg.k))
    print("  shared product gens : %d (one bank, reused by both layers)" % cfg.k)
    print("  product / acc1 / acc2 bits : %d / %d / %d"
          % (w["product_bits"], w["layer1_acc_bits"], w["layer2_acc_bits"]))
    print("  weight word bits    : %d   bias data bits: %d"
          % (w["weight_word_bits"], w["bias_data_bits"]))
    print("  sha256              : %s" % hashlib.sha256(text.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
