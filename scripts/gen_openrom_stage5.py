#!/usr/bin/env python3
"""Stage 5: build every PHYSICAL OpenROM parameter macro from one flow.

Seven macros, all derived deterministically from the frozen Stage-2 canonical
logical images:

    weights_l1_b0..b3   784 x 32   four parallel banks of the 784 x 128 memory
    weights_l2           32 x 40   unchanged, already byte granular
    bias_l1              32 x 24   sign-padded from 22 bits
    bias_l2              10 x 24   sign-padded from 17 bits

Nothing in rtl/ or model/ is written by this script.  The build record goes to
build/stage5/stage5_openrom_build.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import openrom as O                              # noqa: E402
from model2rtl import phys_image as P                           # noqa: E402
from model2rtl import storage as S                              # noqa: E402
from model2rtl.fabric import FabricConfig                       # noqa: E402
from model2rtl.param_image import build_images                  # noqa: E402

BUILD = os.path.join(ROOT, "build", "stage5")
RECORD = os.path.join(BUILD, "stage5_openrom_build.json")

#: words_per_row candidate ladders, chosen from MEASURED tool behaviour rather
#: than reused blindly (see build/stage5/probe and the Stage-5 report):
#:   784 x 32  wpr=2 fails in signal_escape_router; wpr=4 and wpr=8 both
#:             generate, and wpr=4 has the smaller measured GDS bounding box
#:             (53 668 um^2 vs 56 817 um^2), so it is tried first.
#:   32 x 40   wpr=4 is the organisation Stage 2 proved; wpr=8/16 failed there.
#:   depth 10  must divide by words_per_row, so 2 and 5 are the usable values.
WPR_CANDIDATES = {
    "weights_l1_b0": (4, 8),
    "weights_l1_b1": (4, 8),
    "weights_l1_b2": (4, 8),
    "weights_l1_b3": (4, 8),
    "weights_l2": (4, 8, 2),
    "bias_l1": (4, 8, 2),
    "bias_l2": (2, 5, 10),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--macros", nargs="*", default=list(P.PHYS_ORDER))
    ap.add_argument("--timeout", type=int, default=10800)
    ap.add_argument("--lvsdrc", action="store_true",
                    help="also ask OpenROM to run DRC/LVS during generation")
    args = ap.parse_args()

    cfg = FabricConfig()
    model = S.load_indices(S.default_paths(ROOT)["npz"])
    logical = build_images(model, cfg)
    phys = P.build_physical_images(logical)
    roundtrip = P.verify_roundtrip(phys, logical)
    print("physical -> logical round trip: %d rows, %d mismatches"
          % (roundtrip["rows_checked"], roundtrip["mismatches"]))

    os.makedirs(BUILD, exist_ok=True)
    record = (json.load(open(RECORD)) if os.path.exists(RECORD)
              else {"macros": {}})
    record["toolchain"] = O.toolchain_versions()
    record["physical_images"] = {n: phys[n].to_dict() for n in P.PHYS_ORDER}
    record["logical_images"] = {n: logical[n].to_dict() for n in logical}
    record["roundtrip"] = roundtrip

    for name in args.macros:
        img = phys[name]
        print("== OpenROM macro %s: %d x %d ==" % (name, img.depth, img.width),
              flush=True)
        outdir = os.path.join(BUILD, name)
        t0 = time.time()
        b = O.build_rom(name, img.depth, img.width, img.hex_stream(), outdir,
                        ROOT, wpr_candidates=WPR_CANDIDATES[name],
                        check_lvsdrc=args.lvsdrc, timeout=args.timeout)
        entry = {
            "macro": name,
            "logical_memory": img.logical_memory,
            "requested_depth": img.depth,
            "requested_width_bits": img.width,
            "physical_image_sha256": img.sha256(),
            "physical_image": img.to_dict(),
            "attempts": b.attempts,
            "words_per_row": b.words_per_row,
            "array_rows": (-(-img.depth // b.words_per_row)
                           if b.words_per_row else None),
            "array_cols": (img.width * b.words_per_row
                           if b.words_per_row else None),
            "generated": b.generated,
            "elapsed_seconds": round(b.elapsed, 1),
            "data_image": b.data,
            "views": b.views,
            "views_generated": sorted(b.views),
            "physical_verification": b.physical_verification,
            "total_wall_seconds": round(time.time() - t0, 1),
        }
        if not b.generated:
            entry["status"] = "FAIL"
            entry["error_signature"] = b.error
            print("   FAILED after %d attempt(s): %s"
                  % (len(b.attempts), b.error.get("openram_error_lines")),
                  flush=True)
            record["macros"][name] = entry
            _save(record)
            print("\nSTOP: %s did not generate. Not inventing another banking "
                  "architecture without approval." % name, file=sys.stderr)
            return 1

        # --- independent content proof, straight out of the generated SPICE --
        sp = os.path.join(ROOT, b.views["sp"]["path"])
        entry["content_verification"] = O.verify_spice_content(
            sp, name, img.rows, img.width, b.words_per_row)
        entry["bbox"] = O.gds_bbox(os.path.join(ROOT, b.views["gds"]["path"]),
                                   os.path.join(BUILD, "_scratch"))
        entry["lef_size"] = O.lef_size(os.path.join(ROOT,
                                                    b.views["lef"]["path"]))
        entry["generated_verilog"] = O.inspect_generated_verilog(
            os.path.join(ROOT, b.views["v"]["path"]))
        entry["status"] = ("PASS" if entry["content_verification"]["exact"]
                           else "FAIL")
        print("   wpr=%d  %s  %.1fs  bits %d/%d exact  bbox %.2f x %.2f um "
              "= %.1f um^2"
              % (b.words_per_row, entry["status"], b.elapsed,
                 entry["content_verification"]["bits_checked"]
                 - entry["content_verification"]["bit_mismatches"],
                 entry["content_verification"]["bits_checked"],
                 entry["bbox"]["width_um"], entry["bbox"]["height_um"],
                 entry["bbox"]["area_um2"]), flush=True)
        record["macros"][name] = entry
        _save(record)

    _save(record)
    print("\nwrote %s" % os.path.relpath(RECORD, ROOT))
    return 0


def _save(record: dict) -> None:
    tmp = RECORD + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, RECORD)


if __name__ == "__main__":
    raise SystemExit(main())
