#!/usr/bin/env python3
"""Stage 0: train, quantise and export the MNIST MLP for model2rtl.

Produces:
    model/mnist_weights_indices.npz    trained 4-bit indices + integer biases
    model/quant_params.json            fixed arithmetic contract (no weights)
    reports/stage0_quantization.json   full Stage-0 report

No RTL is written by this script.  Stage 0 stops at the integer golden model.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from model2rtl import contract as C            # noqa: E402
from model2rtl import data as D                # noqa: E402
from model2rtl import report as R              # noqa: E402
from model2rtl import storage as S             # noqa: E402
from model2rtl.golden import accuracy          # noqa: E402


def package_versions() -> dict:
    import numpy
    import tensorflow as tf
    return {
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "tensorflow": tf.__version__,
        "keras": tf.keras.__version__,
    }


def sweep_hidden_shift(data, shifts, epochs, seed, batch_size, lr):
    """Diagnostic sweep used once to freeze HIDDEN_REQUANT_SHIFT."""
    from model2rtl import qat
    from model2rtl.golden import accuracy as gacc
    out = []
    for s in shifts:
        model, _ = qat.train(data, epochs=epochs, batch_size=batch_size,
                             lr=lr, seed=seed, hidden_shift=s, verbose=0)
        im = model.export_integer_model()
        col = {}
        # golden model is hard-wired to the contract shift, so evaluate the
        # candidate shift through the TF graph instead
        logits = qat.qat_integer_logits_numpy(model, data["x_val"])
        acc = float((np.argmax(logits, axis=1) == data["y_val"]).mean())
        entry = {"hidden_shift": s, "val_accuracy": acc}
        if s == C.HIDDEN_REQUANT_SHIFT:
            entry["golden_val_accuracy"] = gacc(im, data["x_val"], data["y_val"],
                                                collect=col)
        out.append(entry)
        print("  shift=%2d  val_accuracy=%.4f" % (s, acc))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--float-epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--sweep-hidden-shift", action="store_true",
                    help="run the diagnostic requantisation-shift sweep")
    ap.add_argument("--sweep-epochs", type=int, default=8)
    ap.add_argument("--verbose", type=int, default=2)
    args = ap.parse_args()

    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    from model2rtl import qat  # imported after the env var is set

    paths = S.default_paths(ROOT)
    for p in paths.values():
        os.makedirs(os.path.dirname(p), exist_ok=True)

    t0 = time.time()
    print("== loading MNIST (uint8, zero-point 0) ==")
    data = D.load_mnist_uint8()
    fingerprint = D.dataset_fingerprint(data)
    print("   train=%d val=%d test=%d" % (fingerprint["train_images"],
                                          fingerprint["val_images"],
                                          fingerprint["test_images"]))

    sweep = None
    if args.sweep_hidden_shift:
        print("== hidden requantisation shift sweep ==")
        sweep = sweep_hidden_shift(data, [5, 6, 7, 8, 9, 10],
                                   args.sweep_epochs, args.seed,
                                   args.batch_size, args.lr)

    print("== float32 baseline (reference only) ==")
    fmodel, fhist = qat.train_float(data, epochs=args.float_epochs,
                                    batch_size=args.batch_size, lr=args.lr,
                                    seed=args.seed, verbose=args.verbose)
    float_acc = {
        "train": qat.evaluate_keras_accuracy(fmodel, data["x_train"], data["y_train"]),
        "val": qat.evaluate_keras_accuracy(fmodel, data["x_val"], data["y_val"]),
        "test": qat.evaluate_keras_accuracy(fmodel, data["x_test"], data["y_test"]),
    }
    print("   float train=%.4f val=%.4f test=%.4f"
          % (float_acc["train"], float_acc["val"], float_acc["test"]))

    print("== quantisation-aware training (K=%d, int4 alphabet, uint8 acts) =="
          % C.K)
    qmodel, qhist = qat.train(data, epochs=args.epochs,
                              batch_size=args.batch_size, lr=args.lr,
                              seed=args.seed,
                              hidden_shift=C.HIDDEN_REQUANT_SHIFT,
                              verbose=args.verbose)
    imodel = qmodel.export_integer_model()
    sat_stats = qmodel.saturation_stats()

    print("== cross-checking the TF QAT graph against the NumPy golden model ==")
    tf_logits = qat.qat_integer_logits_numpy(qmodel, data["x_test"])
    golden_logits = imodel.forward(data["x_test"])
    max_diff = float(np.abs(tf_logits - golden_logits.astype(np.float64)).max())
    if max_diff != 0.0:
        print("FAIL: QAT graph and golden model disagree (max diff %g)" % max_diff)
        return 1
    print("   bit-exact: max |tf_logits - golden_logits| = 0")

    int_test_acc = accuracy(imodel, data["x_test"], data["y_test"])
    print("   integer golden test accuracy = %.4f" % int_test_acc)
    if int_test_acc <= 0.90:
        print("FAIL: quantised integer accuracy %.4f is not > 0.90" % int_test_acc)
        return 1

    print("== writing artefacts ==")
    S.save_indices(paths["npz"], imodel)
    S.save_quant_params(paths["quant"])

    meta = {
        "seed": args.seed,
        "epochs_qat": args.epochs,
        "epochs_float": args.float_epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "optimizer": "Adam with cosine decay",
        "quantization_method": "quantisation-aware training with "
                               "straight-through estimators",
        "weight_latent_scale": qat.WEIGHT_LATENT_SCALE,
        "bias_latent_scale": qat.BIAS_LATENT_SCALE,
        "dataset": fingerprint,
        "versions": package_versions(),
        "hidden_shift_sweep": sweep,
        "training_seconds": round(time.time() - t0, 1),
        "tf_graph_vs_golden_max_logit_diff": max_diff,
    }
    rep = R.build_stage0_report(imodel, data, float_acc, sat_stats, meta)
    rep["meta"]["artifact_hashes"] = {
        "mnist_weights_indices.npz": D.file_sha256(paths["npz"]),
        "quant_params.json": D.file_sha256(paths["quant"]),
        "model_parameter_sha256": D.array_sha256(
            imodel.layer1_weight_indices.astype(np.uint8),
            imodel.layer2_weight_indices.astype(np.uint8),
            imodel.layer1_bias.astype(np.int32),
            imodel.layer2_bias.astype(np.int32)),
    }
    with open(paths["report"], "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print_summary(rep, paths)
    return 0


def print_summary(rep: dict, paths: dict) -> None:
    f, q = rep["float_model"], rep["quantized_integer_model"]
    ac = rep["arithmetic_contract"]
    msa = rep["multiply_select_add"]
    print("")
    print("=" * 70)
    print("STAGE 0 SUMMARY")
    print("=" * 70)
    print("Float train accuracy              : %.4f" % f["train_accuracy"])
    print("Float test accuracy               : %.4f" % f["test_accuracy"])
    print("Quantised integer test accuracy   : %.4f" % q["test_accuracy"])
    print("Accuracy drop from float          : %+.4f" % q["accuracy_drop_from_float"])
    print("")
    print("Quantisation")
    print("  K                               : %d" % msa["layer1"]["K"])
    print("  weight alphabet                 : %s" % ac["weight_alphabet_values"])
    print("  activation format               : uint8 [0,255], zero-point 0")
    print("  bias format                     : %s" % ac["bias_format"])
    print("  rounding                        : %s" % ac["rounding_rule"])
    print("  saturation                      : %s" % ac["saturation_rule"])
    for name in ("layer1", "layer2"):
        L = rep[name]
        print("")
        print("%s" % name.upper())
        print("  shape                           : %s %s" % (L["shape"], L["orientation"]))
        print("  synapses                        : %d" % L["synapse_count"])
        print("  index histogram [0..15]         : %s" % L["weight_index_histogram"])
        print("  unused levels                   : %s" % (L["unused_weight_levels"] or "none"))
        print("  quantised weight range          : [%d, %d]"
              % (L["min_quantized_weight"], L["max_quantized_weight"]))
        print("  weight saturation               : %d (%.4f%%)"
              % (L["weight_saturation_count"], L["weight_saturation_percentage"]))
        print("  product width                   : %d bits signed" % L["product_bits"])
        print("  accumulator width               : %d bits signed" % L["accumulator_bits"])
        print("  bias width declared/required    : %d / %d bits signed"
              % (L["bias_bits_declared"], L["bias_bits_required"]))
    a = rep["activations"]
    print("")
    print("ACTIVATIONS")
    print("  input observed range            : %s" % a["input_range_observed_test"])
    print("  hidden observed range           : %s" % a["hidden_range_observed_test"])
    print("  hidden pre-saturation max       : %d" % a["hidden_pre_saturation_max_observed"])
    print("  hidden saturation               : %d of %d (%.4f%%)"
          % (a["hidden_saturation_count"], a["hidden_elements_evaluated"],
             a["hidden_saturation_percentage"]))
    print("  logit observed range            : %s" % a["logit_range_observed"])
    print("")
    print("MULTIPLY-SELECT-ADD OPERATOR ANALYSIS")
    for name in ("layer1", "layer2"):
        m = msa[name]
        print("  %s: naive=%d shared=%d selectors=%d (fan-in %d) ratio=%.3f  %s"
              % (name, m["naive_multipliers"], m["shared_product_generators"],
                 m["selectors"], m["selector_fan_in"],
                 m["ratio_naive_over_shared"],
                 "sharing wins" if m["sharing_reduces_product_generators"]
                 else "sharing LOSES (fanout %d < K=%d)" % (m["outputs"], m["K"])))
    t = msa["total"]
    print("  total  : naive=%d shared=%d ratio=%.3f"
          % (t["naive_multipliers"], t["shared_product_generators"],
             t["ratio_naive_over_shared"]))
    print("  note   : %s" % msa["synthesis_caveat"])
    s = rep["model_size"]
    print("")
    print("WEIGHT STORAGE")
    print("  synapses  : %d (layer1 %d + layer2 %d)"
          % (s["total_synapses"], s["layer1_synapses"], s["layer2_synapses"]))
    print("  index bits: %d  (%d bytes)" % (s["total_index_bits"], s["total_index_bytes"]))
    print("")
    print("ARTIFACTS")
    for k in ("npz", "quant", "report"):
        print("  %s" % os.path.relpath(paths[k], ROOT))
    print("RTL written: NO")
    print("=" * 70)


if __name__ == "__main__":
    raise SystemExit(main())
