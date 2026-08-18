"""Persistence of the trained model in its integer storage form.

Two artefacts, with a strict separation of concerns:

  model/mnist_weights_indices.npz
      MODEL parameters only: per-synapse 4-bit weight indices and per-neuron
      integer biases.

  model/quant_params.json
      The fixed arithmetic contract: alphabet, widths, shifts, clipping
      limits, tensor orientation, activation format, bias format.  It contains
      NO per-synapse weight index and no per-neuron bias value.

Nothing else is needed to run exact integer inference.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import numpy as np

from . import contract as C
from .golden import IntegerModel

NPZ_NAME = "mnist_weights_indices.npz"
QUANT_NAME = "quant_params.json"


def save_indices(path: str, model: IntegerModel) -> None:
    model.validate()
    np.savez(
        path,
        layer1_weight_indices=model.layer1_weight_indices.astype(np.uint8),
        layer2_weight_indices=model.layer2_weight_indices.astype(np.uint8),
        layer1_bias=model.layer1_bias.astype(np.int32),
        layer2_bias=model.layer2_bias.astype(np.int32),
    )


def load_indices(path: str) -> IntegerModel:
    with np.load(path) as z:
        model = IntegerModel(
            layer1_weight_indices=z["layer1_weight_indices"].astype(np.int64),
            layer2_weight_indices=z["layer2_weight_indices"].astype(np.int64),
            layer1_bias=z["layer1_bias"].astype(np.int64),
            layer2_bias=z["layer2_bias"].astype(np.int64),
        )
    model.validate()
    return model


def quant_params_dict() -> Dict[str, Any]:
    d = C.width_report()
    d["_comment"] = (
        "Fixed quantisation / arithmetic contract for the model2rtl MNIST MLP. "
        "Architecture level only: contains no trained synapse weight index and "
        "no trained bias value. The compute fabric may depend on this file; it "
        "must never depend on mnist_weights_indices.npz."
    )
    d["bias_format"] = {
        "domain": "same integer domain as the layer accumulator "
                  "(added directly to the dot product, no pre-scaling)",
        "signed": True,
        "layer1_bits": C.BIAS_BITS["layer1"],
        "layer2_bits": C.BIAS_BITS["layer2"],
        "storage_dtype": "int32 in the NPZ, sign-extended into the accumulator",
    }
    d["model_parameters"] = [
        "layer1_weight_indices", "layer2_weight_indices",
        "layer1_bias", "layer2_bias",
    ]
    d["fabric_parameters"] = [
        "topology", "K", "weight_alphabet", "activation format",
        "hidden_requant_shift", "rounding_rule", "saturation_rule",
    ]
    return d


def save_quant_params(path: str) -> None:
    with open(path, "w") as fh:
        json.dump(quant_params_dict(), fh, indent=2, sort_keys=True)
        fh.write("\n")


def load_quant_params(path: str) -> Dict[str, Any]:
    with open(path) as fh:
        return json.load(fh)


def contract_matches(params: Dict[str, Any]) -> bool:
    """True if a loaded quant_params.json agrees with the compiled contract."""
    ref = quant_params_dict()
    keys = ["K", "weight_index_bits", "weight_alphabet", "activation_bits",
            "activation_signed", "activation_min", "activation_max",
            "hidden_requant_shift", "rounding_rule", "saturation_rule",
            "layer1", "layer2", "bias_format"]
    return all(params.get(k) == ref.get(k) for k in keys)


def default_paths(root: str) -> Dict[str, str]:
    return {
        "npz": os.path.join(root, "model", NPZ_NAME),
        "quant": os.path.join(root, "model", QUANT_NAME),
        "report": os.path.join(root, "reports", "stage0_quantization.json"),
    }
