"""`model2rtl` -- compile a trained quantized MLP into portable RTL.

    model2rtl --model mnist.h5 --output ./rtlout
    model2rtl --indices model/mnist_weights_indices.npz --output ./rtlout

The compiler builds exactly one architecture: input -> Dense -> ReLU -> Dense
-> argmax, weights quantized to K = 16 fixed levels, unsigned integer
activations, and a power-of-two requantisation shift. Anything else is
rejected with a description of what was found, never approximated.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional, Tuple

import numpy as np


def _load_calibration(path: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Calibration data: an .npz with x (and ideally y), or a bare .npy of x."""
    if path.endswith(".npy"):
        return np.load(path), None
    with np.load(path) as z:
        keys = set(z.files)
        xk = next((k for k in ("x", "x_test", "x_calib", "images") if k in keys),
                  None)
        yk = next((k for k in ("y", "y_test", "y_calib", "labels") if k in keys),
                  None)
        if xk is None:
            raise SystemExit(
                "calibration file %s has no recognisable input array (looked "
                "for x, x_test, x_calib, images; found %s)"
                % (path, sorted(keys)))
        x = np.asarray(z[xk])
        y = np.asarray(z[yk]) if yk else None
    return x, y


def _as_activations(x: np.ndarray, n_in: int, act_bits: int) -> np.ndarray:
    """Flatten to (N, n_in) unsigned integers in the activation range."""
    x = np.asarray(x)
    x = x.reshape(x.shape[0], -1)
    if x.shape[1] != n_in:
        raise SystemExit("calibration inputs have %d features, the model takes "
                         "%d" % (x.shape[1], n_in))
    hi = (1 << act_bits) - 1
    if np.issubdtype(x.dtype, np.floating):
        if x.max() <= 1.0 + 1e-9:
            x = np.round(x * hi)
        else:
            x = np.round(x)
    x = np.clip(x, 0, hi).astype(np.int64)
    return x


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="model2rtl", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--model", metavar="PATH",
                     help="trained float model: .h5 / .keras, or .npz with "
                          "w1, b1, w2, b2")
    src.add_argument("--indices", metavar="PATH",
                     help="already-quantized .npz of weight indices and "
                          "integer biases; skips quantization entirely")
    p.add_argument("--output", "-o", required=True, metavar="DIR",
                   help="directory to write the RTL and report into")
    p.add_argument("--prefix", default="mlp",
                   help="module and file name prefix (default: mlp)")
    p.add_argument("--calibration", metavar="PATH",
                   help="calibration data for the quantization search; an "
                        ".npz with x and ideally y. Without labels the "
                        "requantisation shift cannot be chosen by measured "
                        "accuracy and the result is reported as unmeasured.")
    p.add_argument("--quantize", choices=("ptq", "qat"), default="ptq",
                   help="ptq: post-training quantization (default, fast, no "
                        "training data needed beyond calibration). "
                        "qat: fine-tune with quantization-aware training, "
                        "which needs labelled training data and recovers "
                        "most of the accuracy 4-bit weights would otherwise "
                        "cost.")
    p.add_argument("--epochs", type=int, default=20,
                   help="QAT fine-tuning epochs (default: 20)")
    p.add_argument("--input-scale", type=float, default=None,
                   help="float scale mapping an integer activation to the "
                        "value the float model expects, e.g. 0.00392157 for "
                        "models trained on x/255. Default: try 1/255 and 1.0 "
                        "and keep whichever measures better.")
    p.add_argument("--shift", type=int, default=None,
                   help="force the requantisation shift instead of searching")
    p.add_argument("--check", action="store_true",
                   help="elaborate the emitted RTL with Icarus and Yosys if "
                        "they are on PATH")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    from . import contract as C
    from .compile import compile_model
    from .genmodel import GeneralIntegerModel, ModelSpecError

    def say(*a):
        if not args.quiet:
            print(*a, flush=True)

    fabric_module = "%s_fabric" % args.prefix
    extra = {}

    # ---- already quantized -------------------------------------------
    if args.indices:
        from . import storage as S
        frozen = S.load_indices(args.indices)
        model = GeneralIntegerModel.from_arrays(
            frozen.layer1_weight_indices, frozen.layer2_weight_indices,
            frozen.layer1_bias, frozen.layer2_bias,
            k=C.K, act_bits=C.ACT_BITS,
            requant_shift=args.shift or C.HIDDEN_REQUANT_SHIFT,
            module_name=fabric_module,
            provenance={"source": os.path.abspath(args.indices),
                        "quantization": "none: the input was already "
                                        "quantized"})
        say("loaded quantized model: %d -> %d -> %d"
            % (model.cfg.n_in, model.cfg.n_hidden, model.cfg.n_out))

    # ---- float model, needs quantizing --------------------------------
    else:
        from .ingest import UnsupportedModel, load
        from .quantize import QuantizationError, quantize_ptq
        try:
            net = load(args.model)
        except UnsupportedModel as exc:
            print("model2rtl: cannot compile this model.\n%s" % exc,
                  file=sys.stderr)
            return 2
        say("loaded %s: %d -> %d -> ReLU -> %d"
            % (os.path.basename(args.model), net.n_in, net.n_hidden,
               net.n_out))
        for n in net.notes:
            say("  note: %s" % n)

        x = y = None
        if args.calibration:
            x_raw, y = _load_calibration(args.calibration)
            x = _as_activations(x_raw, net.n_in, C.ACT_BITS)
            say("calibration: %d samples%s"
                % (x.shape[0], "" if y is None else " with labels"))
        else:
            say("  WARNING: no --calibration given. The requantisation shift "
                "cannot be chosen by measurement and the accuracy of the "
                "result is unknown.")

        if args.quantize == "qat":
            from .qat_general import qat_finetune
            if x is None or y is None:
                print("model2rtl: --quantize qat needs labelled data; pass "
                      "--calibration with x and y.", file=sys.stderr)
                return 2
            qr = qat_finetune(net, x, y, epochs=args.epochs,
                              input_scale=args.input_scale,
                              shift=args.shift, module_name=fabric_module)
        else:
            kw = {}
            if args.input_scale is not None:
                kw["input_scales"] = (args.input_scale,)
            if args.shift is not None:
                kw["shifts"] = (args.shift,)
            try:
                qr = quantize_ptq(net, x, y, module_name=fabric_module, **kw)
            except QuantizationError as exc:
                print("model2rtl: quantization failed.\n%s" % exc,
                      file=sys.stderr)
                return 3

        model = qr.model
        extra["ingest"] = net.to_dict()
        extra["quantization"] = qr.to_dict()
        say("quantized: shift %d, input scale %.8g"
            % (qr.requant_shift, qr.input_scale))
        if qr.calibration_accuracy is not None:
            say("  float %.4f -> integer %.4f on calibration (%+.2f points)"
                % (qr.float_accuracy, qr.calibration_accuracy,
                   100 * (qr.calibration_accuracy - qr.float_accuracy)))
        for n in qr.notes:
            say("  note: %s" % n)

    # ---- emit ----------------------------------------------------------
    try:
        report = compile_model(model, args.output, prefix=args.prefix,
                               extra_report=extra)
    except ModelSpecError as exc:
        print("model2rtl: %s" % exc, file=sys.stderr)
        return 3

    say("\nwrote %s" % os.path.abspath(args.output))
    for name in sorted(report["emitted"]):
        say("  %-24s %s" % (name, report["emitted"][name][:16]))
    say("  %-24s" % "compile_report.json")
    say("\nfabric is weight independent: %s"
        % report["weight_independence"]["identical"])
    say("latency: %d cycles per inference (architectural only)"
        % report["latency"]["cycles_per_inference"])

    if args.check:
        rc = _elaborate(args.output, args.prefix, say)
        if rc:
            return rc
    return 0


def _locate(tool: str):
    """Find an EDA tool on PATH, or in the extra directories this project
    knows about. Returns None if it genuinely is not installed."""
    import shutil
    found = shutil.which(tool)
    if found:
        return found
    try:
        from .sim import find_tool
        return find_tool(tool)
    except Exception:
        return None


def _elaborate(outdir: str, prefix: str, say) -> int:
    """Optional sanity check: does the emitted RTL actually elaborate?"""
    import subprocess
    srcs = ["%s_top.v" % prefix, "%s_fabric.v" % prefix,
            "%s_params.v" % prefix, "%s_params_sel.v" % prefix]
    paths = [os.path.join(outdir, s) for s in srcs]
    ok = True
    iverilog = _locate("iverilog")
    if iverilog:
        r = subprocess.run([iverilog, "-g2001", "-Wall", "-o", os.devnull,
                            "-s", "%s_top" % prefix] + paths,
                           capture_output=True, text=True)
        say("icarus: %s" % ("OK" if r.returncode == 0 else "FAILED"))
        if r.returncode:
            print(r.stdout + r.stderr, file=sys.stderr)
            ok = False
    else:
        say("icarus: not on PATH, skipped")
    yosys = _locate("yosys")
    if yosys:
        script = ("read_verilog %s; hierarchy -check -top %s_top; proc; "
                  "check -assert" % (" ".join(paths), prefix))
        r = subprocess.run([yosys, "-q", "-p", script],
                           capture_output=True, text=True)
        say("yosys:  %s" % ("OK" if r.returncode == 0 else "FAILED"))
        if r.returncode:
            print(r.stdout + r.stderr, file=sys.stderr)
            ok = False
    else:
        say("yosys:  not on PATH, skipped")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
