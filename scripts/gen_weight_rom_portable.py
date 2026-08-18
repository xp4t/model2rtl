#!/usr/bin/env python3
"""Stage 2, Backend A: generate the portable parameter-storage RTL.

    scripts/gen_weight_rom_portable.py  ->  rtl/mnist_mlp_params_portable.v

Reads the frozen Stage-0 artefacts (model/mnist_weights_indices.npz and
model/quant_params.json), builds the CANONICAL parameter images
(src/model2rtl/param_image.py) and emits pure synthesizable Verilog-2001.

The canonical images are also written to build/param_images/ with their
SHA-256 hashes.  The OpenRAM backend consumes exactly those same images: there
is only one packing implementation in this project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import memif                                    # noqa: E402
from model2rtl import storage as S                             # noqa: E402
from model2rtl.fabric import FabricConfig                      # noqa: E402
from model2rtl.param_image import (IMAGE_ORDER, build_images,  # noqa: E402
                                   default_dir, write_images)
from model2rtl.param_verilog import emit_portable              # noqa: E402

FABRIC = os.path.join(ROOT, "rtl", "mnist_mlp_fabric.v")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "rtl",
                                                  "mnist_mlp_params_portable.v"))
    ap.add_argument("--image-dir", default=None)
    args = ap.parse_args()

    cfg = FabricConfig()

    # fail closed if this generator's idea of the interface has drifted from
    # the frozen Stage-1 fabric
    memif.verify_against_rtl(FABRIC, cfg)

    paths = S.default_paths(ROOT)
    model = S.load_indices(paths["npz"])
    quant = S.load_quant_params(paths["quant"])
    if not S.contract_matches(quant):
        raise SystemExit("model/quant_params.json does not match the compiled "
                         "arithmetic contract")

    images = build_images(model, cfg)
    image_dir = args.image_dir or default_dir(ROOT)
    manifest = write_images(image_dir, images)

    text = emit_portable(images, cfg)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(text)

    print("wrote %s" % os.path.relpath(args.out, ROOT))
    print("  sha256 %s" % hashlib.sha256(text.encode()).hexdigest())
    print("canonical parameter images -> %s" % os.path.relpath(image_dir, ROOT))
    for name in IMAGE_ORDER:
        img = images[name]
        print("  %-11s depth %4d  width %3d  %6d bits  sha256 %s"
              % (name, img.depth, img.width, img.depth * img.width, img.sha256()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
