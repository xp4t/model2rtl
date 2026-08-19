#!/usr/bin/env python3
"""Stage 5: emit the physical-organisation parameter backend RTL.

Writes exactly two NEW files:

    rtl/mnist_mlp_params_openrom_phys.v
    rtl/mnist_mlp_params_sel_openrom_phys.v

and touches nothing else.  Every frozen file -- the fabric, the portable
backend, the Stage-2 OpenRAM backend, the top level and both Stage-2 selectors
-- is hashed before and after and must be unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import phys_image as P                           # noqa: E402
from model2rtl import storage as S                              # noqa: E402
from model2rtl.fabric import FabricConfig                       # noqa: E402
from model2rtl.param_image import build_images                  # noqa: E402
from model2rtl.phys_verilog import (MODULE, emit_physical_backend,  # noqa: E402
                                    emit_physical_selector)

FROZEN_RTL = ["mnist_mlp_fabric.v", "mnist_mlp_params_portable.v",
              "mnist_mlp_params_openram.v", "mnist_mlp_top.v",
              "mnist_mlp_params_sel_portable.v",
              "mnist_mlp_params_sel_openram.v"]

OUT_BACKEND = "mnist_mlp_params_openrom_phys.v"
OUT_SELECTOR = "mnist_mlp_params_sel_openrom_phys.v"

BUILD_RECORD = os.path.join(ROOT, "build", "stage5",
                            "stage5_openrom_build.json")


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main() -> int:
    rtl = os.path.join(ROOT, "rtl")
    before = {n: sha(os.path.join(rtl, n)) for n in FROZEN_RTL}

    cfg = FabricConfig()
    model = S.load_indices(S.default_paths(ROOT)["npz"])
    logical = build_images(model, cfg)
    phys = P.build_physical_images(logical)
    P.verify_roundtrip(phys, logical)

    status = {}
    if os.path.exists(BUILD_RECORD):
        rec = json.load(open(BUILD_RECORD))["macros"]
        for n in P.PHYS_ORDER:
            m = rec.get(n, {})
            status[n] = ("physical macro generated (%s), contents verified "
                         "%d/%d bits"
                         % (", ".join(m.get("views_generated", [])),
                            m.get("content_verification", {}).get(
                                "bits_checked", 0)
                            - m.get("content_verification", {}).get(
                                "bit_mismatches", 0),
                            m.get("content_verification", {}).get(
                                "bits_checked", 0))
                         if m.get("status") == "PASS"
                         else "physical macro NOT generated: %s"
                              % m.get("status", "not attempted"))
    else:
        status = {n: "physical macro not yet built" for n in P.PHYS_ORDER}

    with open(os.path.join(rtl, OUT_BACKEND), "w") as fh:
        fh.write(emit_physical_backend(phys, cfg, macro_status=status))
    with open(os.path.join(rtl, OUT_SELECTOR), "w") as fh:
        fh.write(emit_physical_selector(cfg))

    after = {n: sha(os.path.join(rtl, n)) for n in FROZEN_RTL}
    changed = [n for n in FROZEN_RTL if before[n] != after[n]]
    if changed:
        print("FATAL: frozen RTL changed: %s" % changed, file=sys.stderr)
        return 1
    print("wrote rtl/%s and rtl/%s" % (OUT_BACKEND, OUT_SELECTOR))
    print("frozen RTL unchanged: %s" % (not changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
