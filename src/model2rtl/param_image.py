"""Canonical parameter images -- the single source of truth for both backends.

Stage 2 has two storage backends (portable Verilog and an OpenRAM/OpenROM
physical macro).  Neither is allowed its own packing code: both consume the
images built here, and both are proved against the same SHA-256 hashes.  That
is what makes it impossible to physically build one dataset while testing
another.

Four logical parameter memories, matching the Stage-1 fabric interface exactly
(see model2rtl.memif):

    weights_l1 : depth 784, width 128   one packed word per input feature
    weights_l2 : depth  32, width  40   one packed word per hidden feature
    bias_l1    : depth  32, width  22   one signed bias per hidden neuron
    bias_l2    : depth  10, width  17   one signed bias per output neuron

bias_l2 is stored at its architectural width of 17 bits.  The backend wrapper
SIGN EXTENDS it to the 22-bit bmem_data bus; it is never zero extended.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from .fabric import (FabricConfig, derive_widths, pack_weight_words,
                     to_twos_complement, unpack_weight_word)


@dataclass(frozen=True)
class ParamImage:
    """One logical parameter memory, fully determined and hashable."""

    name: str
    depth: int
    width: int
    rows: tuple            # tuple of unsigned ints, index = address
    packing: str
    orientation: str
    signed: bool

    def __post_init__(self):
        if len(self.rows) != self.depth:
            raise ValueError("%s: %d rows for depth %d"
                             % (self.name, len(self.rows), self.depth))
        for i, v in enumerate(self.rows):
            if v < 0 or v >> self.width:
                raise ValueError("%s: row %d does not fit %d bits"
                                 % (self.name, i, self.width))

    # -- canonical serialisation ----------------------------------------
    def canonical_bytes(self) -> bytes:
        """Deterministic byte image: header, then each row big-endian, MSB first.

        Row 0 comes first.  This is the byte string every hash in Stage 2 is
        taken over, so "the same image" always means the same bytes.
        """
        row_bytes = (self.width + 7) // 8
        out = bytearray()
        out += b"model2rtl-param-image-v1\n"
        out += ("%s %d %d\n" % (self.name, self.depth, self.width)).encode()
        for v in self.rows:
            out += int(v).to_bytes(row_bytes, "big")
        return bytes(out)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def hex_lines(self) -> List[str]:
        """One zero-padded hex word per line, row 0 first."""
        digits = (self.width + 3) // 4
        return ["%0*x" % (digits, v) for v in self.rows]

    def bit_string_msb_first(self) -> str:
        """All rows concatenated, each row MSB first, row 0 first."""
        return "".join(format(v, "0%db" % self.width) for v in self.rows)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "depth": self.depth,
            "width": self.width,
            "packing": self.packing,
            "orientation": self.orientation,
            "signed": self.signed,
            "total_bits": self.depth * self.width,
            "sha256": self.sha256(),
        }

    def signed_rows(self) -> List[int]:
        if not self.signed:
            raise ValueError("%s is not signed" % self.name)
        lim = 1 << (self.width - 1)
        return [v - (1 << self.width) if v >= lim else v for v in self.rows]


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------

def build_images(model, cfg: FabricConfig = FabricConfig()) -> Dict[str, ParamImage]:
    """Build all four canonical images from the trained integer model."""
    model.validate()
    w = derive_widths(cfg)
    ib = w["index_bits"]

    def weight_image(name, indices, n_out):
        return ParamImage(
            name=name,
            depth=indices.shape[0],
            width=n_out * ib,
            rows=tuple(pack_weight_words(indices, cfg, word_bits=n_out * ib)),
            packing="row[i] bits [j*%d +: %d] = weight_index[i][j]; neuron 0 in "
                    "the least significant nibble" % (ib, ib),
            orientation="[in_features, out_features] (Stage-0 orientation)",
            signed=False,
        )

    def bias_image(name, bias, bits):
        return ParamImage(
            name=name,
            depth=len(bias),
            width=bits,
            rows=tuple(to_twos_complement(int(v), bits) for v in bias),
            packing="row[j] = two's-complement bias of output neuron j",
            orientation="[out_features]",
            signed=True,
        )

    return {
        "weights_l1": weight_image("weights_l1", model.layer1_weight_indices,
                                   cfg.n_hidden),
        "weights_l2": weight_image("weights_l2", model.layer2_weight_indices,
                                   cfg.n_out),
        "bias_l1": bias_image("bias_l1", model.layer1_bias,
                              w["layer1_bias_bits"]),
        "bias_l2": bias_image("bias_l2", model.layer2_bias,
                              w["layer2_bias_bits"]),
    }


IMAGE_ORDER = ("weights_l1", "weights_l2", "bias_l1", "bias_l2")


# --------------------------------------------------------------------------
# Bus-level view (what the fabric actually sees on wmem_data / bmem_data)
# --------------------------------------------------------------------------

def weight_bus_word(images: Dict[str, ParamImage], layer: int, addr: int,
                    cfg: FabricConfig = FabricConfig()) -> int:
    """Expected wmem_data for (layer, addr). Invalid address -> 0."""
    img = images["weights_l1"] if layer == 0 else images["weights_l2"]
    if addr < 0 or addr >= img.depth:
        return 0
    return img.rows[addr]          # high bits above the layer field stay zero


def bias_bus_word(images: Dict[str, ParamImage], layer: int, addr: int,
                  cfg: FabricConfig = FabricConfig()) -> int:
    """Expected bmem_data for (layer, addr), SIGN EXTENDED. Invalid -> 0."""
    bus = derive_widths(cfg)["bias_data_bits"]
    img = images["bias_l1"] if layer == 0 else images["bias_l2"]
    if addr < 0 or addr >= img.depth:
        return 0
    signed = img.signed_rows()[addr]
    return to_twos_complement(signed, bus)


# --------------------------------------------------------------------------
# Round trip back to the trained tensors (used by the readback tests)
# --------------------------------------------------------------------------

def unpack_weight_image(img: ParamImage, n_out: int,
                        cfg: FabricConfig = FabricConfig()) -> np.ndarray:
    return np.array([unpack_weight_word(v, n_out, cfg) for v in img.rows],
                    dtype=np.int64)


# --------------------------------------------------------------------------
# Serialisation to disk
# --------------------------------------------------------------------------

def default_dir(root: str) -> str:
    return os.path.join(root, "build", "param_images")


def write_images(directory: str, images: Dict[str, ParamImage]) -> dict:
    """Write the canonical images plus a manifest. Deterministic."""
    os.makedirs(directory, exist_ok=True)
    manifest = {"format": "model2rtl-param-image-v1", "images": {}}
    for name in IMAGE_ORDER:
        img = images[name]
        with open(os.path.join(directory, name + ".bin"), "wb") as fh:
            fh.write(img.canonical_bytes())
        with open(os.path.join(directory, name + ".hex"), "w") as fh:
            fh.write("\n".join(img.hex_lines()) + "\n")
        entry = img.to_dict()
        entry["files"] = {"canonical_bin": name + ".bin", "hex_rows": name + ".hex"}
        manifest["images"][name] = entry
    with open(os.path.join(directory, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return manifest


def read_manifest(directory: str) -> dict:
    with open(os.path.join(directory, "manifest.json")) as fh:
        return json.load(fh)


def load_images_from_model(root: str, cfg: FabricConfig = FabricConfig()):
    """Build the images straight from the frozen Stage-0 artefacts."""
    from . import storage as S
    model = S.load_indices(S.default_paths(root)["npz"])
    return model, build_images(model, cfg)
