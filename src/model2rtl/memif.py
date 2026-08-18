"""Stage 2: the parameter-memory interface, as a Python object.

This module does NOT invent an interface.  It is a transcription of the ports
that rtl/mnist_mlp_fabric.v already declares (Stage 1, frozen), together with
the timing and packing semantics that file documents.  :func:`verify_against_rtl`
re-parses the Verilog and fails closed if the transcription and the RTL ever
disagree, so a backend generated from this description cannot silently drift
away from the fabric.

Both Stage-2 backends -- the portable Verilog ROM and the SKY130 OpenRAM/OpenROM
macro -- must conform to exactly this object.  Nothing here is backend specific.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import contract as C
from .fabric import FabricConfig, derive_widths, pack_weight_words, to_twos_complement


# --------------------------------------------------------------------------
# Port description
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Port:
    name: str
    direction: str          # direction as seen FROM THE FABRIC
    width: int
    role: str

    @property
    def memory_direction(self) -> str:
        """Direction as seen from the memory backend (the mirror image)."""
        return "input" if self.direction == "output" else "output"

    def decl(self) -> str:
        rng = "" if self.width == 1 else "[%d:0] " % (self.width - 1)
        return "%s wire %s%s" % (self.memory_direction, rng, self.name)


@dataclass(frozen=True)
class MemorySpace:
    """One logical memory behind a shared port (selected by the layer bit)."""
    name: str
    layer_select: int
    depth: int
    used_data_bits: int
    addr_used_bits: int
    description: str


@dataclass(frozen=True)
class MemoryPort:
    """One parameter-memory port of the fabric."""
    kind: str                       # "weight" | "bias"
    en: Port
    layer: Port
    addr: Port
    data: Port
    spaces: Tuple[MemorySpace, ...]

    @property
    def ports(self) -> Tuple[Port, ...]:
        return (self.en, self.layer, self.addr, self.data)


# --------------------------------------------------------------------------
# The interface itself, transcribed from rtl/mnist_mlp_fabric.v
# --------------------------------------------------------------------------

CLK = Port("clk", "input", 1, "single clock; both backends are clocked by it")
RST = Port("rst", "input", 1,
           "synchronous, active high; the fabric's reset. A parameter memory "
           "holds no architectural state, so a backend need not use it.")

#: Read latency, in cycles, for both ports and both backends.
READ_LATENCY = 1

#: Capture semantics both backends must implement.
CAPTURE_MODEL = (
    "always @(posedge clk) if (en) data_r <= MEM[{layer, addr}];\n"
    "assign data = data_r;"
)

TIMING_CONTRACT = (
    "Synchronous read, %d cycle latency, enable gated with hold: an address and "
    "layer driven during cycle T are captured on the posedge that ends cycle T; "
    "the corresponding data must be presented throughout cycle T+1. When en is "
    "low the previously captured data must be held unchanged." % READ_LATENCY
)


def build_interface(cfg: FabricConfig = FabricConfig()) -> Dict[str, object]:
    w = derive_widths(cfg)
    ib = w["index_bits"]

    weight = MemoryPort(
        kind="weight",
        en=Port("wmem_en", "output", 1, "read strobe for this cycle's address"),
        layer=Port("wmem_layer", "output", 1, "0 = layer 1, 1 = layer 2"),
        addr=Port("wmem_addr", "output", w["weight_addr_bits"],
                  "input-feature index i of the currently streamed activation"),
        data=Port("wmem_data", "input", w["weight_word_bits"],
                  "one word holding EVERY output neuron's %d-bit index for "
                  "input feature i" % ib),
        spaces=(
            MemorySpace("layer1_weights", 0, cfg.n_in, cfg.n_hidden * ib,
                        (cfg.n_in - 1).bit_length(),
                        "%d entries x %d bits (%d neurons x %d bits)"
                        % (cfg.n_in, cfg.n_hidden * ib, cfg.n_hidden, ib)),
            MemorySpace("layer2_weights", 1, cfg.n_hidden, cfg.n_out * ib,
                        (cfg.n_hidden - 1).bit_length(),
                        "%d entries x %d bits (%d neurons x %d bits)"
                        % (cfg.n_hidden, cfg.n_out * ib, cfg.n_out, ib)),
        ),
    )

    bias = MemoryPort(
        kind="bias",
        en=Port("bmem_en", "output", 1, "read strobe for this cycle's address"),
        layer=Port("bmem_layer", "output", 1, "0 = layer 1, 1 = layer 2"),
        addr=Port("bmem_addr", "output", w["bias_addr_bits"],
                  "output-neuron index j being finalised"),
        data=Port("bmem_data", "input", w["bias_data_bits"],
                  "that neuron's signed bias, sign extended to %d bits"
                  % w["bias_data_bits"]),
        spaces=(
            MemorySpace("layer1_bias", 0, cfg.n_hidden, w["layer1_bias_bits"],
                        (cfg.n_hidden - 1).bit_length(),
                        "%d signed %d-bit biases"
                        % (cfg.n_hidden, w["layer1_bias_bits"])),
            MemorySpace("layer2_bias", 1, cfg.n_out, w["layer2_bias_bits"],
                        (cfg.n_out - 1).bit_length(),
                        "%d signed %d-bit biases"
                        % (cfg.n_out, w["layer2_bias_bits"])),
        ),
    )

    return {
        "clk": CLK,
        "rst": RST,
        "weight": weight,
        "bias": bias,
        "read_latency": READ_LATENCY,
        "timing_contract": TIMING_CONTRACT,
        "capture_model": CAPTURE_MODEL,
        "packing": {
            "orientation": "[in_features, out_features] (Stage-0 orientation, "
                           "not transposed)",
            "rule": "weight_index[i][j] = wmem_data[j*%d +: %d]" % (ib, ib),
            "neuron0_position": "least significant nibble",
            "layer1_field": "bits [%d:0] of wmem_data"
                            % (cfg.n_hidden * ib - 1),
            "layer2_field": "bits [%d:0] of wmem_data" % (cfg.n_out * ib - 1),
            "unused_bits": "bits above the active layer's field are ignored by "
                           "the fabric; a backend may drive them to zero",
        },
        "out_of_range_note":
            "The fabric's address counter reaches n_in (=%d) for one cycle at "
            "the end of layer-1 streaming, and n_hidden (=%d) at the end of "
            "layer-2 streaming, while wmem_en is LOW. An enable-gated backend "
            "never sees those addresses. A free-running backend would read one "
            "past the end of the array; its data is never consumed, but the "
            "backend must still not produce X on the bus in that cycle."
            % (cfg.n_in, cfg.n_hidden),
    }


# --------------------------------------------------------------------------
# Parameter encoding (what a backend must actually store)
# --------------------------------------------------------------------------

def encode_weight_space(indices: np.ndarray, cfg: FabricConfig) -> List[int]:
    """Packed weight words for one layer, in wmem_addr order."""
    return pack_weight_words(indices, cfg)


def encode_bias_space(bias: np.ndarray, layer_bits: int,
                      bus_bits: int) -> List[int]:
    """Signed biases, range checked against the architectural width, then sign
    extended onto the shared bias bus."""
    out = []
    for v in bias:
        to_twos_complement(int(v), layer_bits)      # fails closed if too wide
        out.append(to_twos_complement(int(v), bus_bits))
    return out


def encode_model(model, cfg: FabricConfig = FabricConfig()) -> Dict[str, List[int]]:
    w = derive_widths(cfg)
    return {
        "layer1_weights": encode_weight_space(model.layer1_weight_indices, cfg),
        "layer2_weights": encode_weight_space(model.layer2_weight_indices, cfg),
        "layer1_bias": encode_bias_space(model.layer1_bias,
                                         w["layer1_bias_bits"],
                                         w["bias_data_bits"]),
        "layer2_bias": encode_bias_space(model.layer2_bias,
                                         w["layer2_bias_bits"],
                                         w["bias_data_bits"]),
    }


def storage_footprint(cfg: FabricConfig = FabricConfig()) -> Dict[str, int]:
    w = derive_widths(cfg)
    ib = w["index_bits"]
    l1 = cfg.n_in * cfg.n_hidden * ib
    l2 = cfg.n_hidden * cfg.n_out * ib
    b1 = cfg.n_hidden * w["layer1_bias_bits"]
    b2 = cfg.n_out * w["layer2_bias_bits"]
    return {
        "layer1_weight_bits": l1,
        "layer2_weight_bits": l2,
        "layer1_bias_bits_total": b1,
        "layer2_bias_bits_total": b2,
        "weight_bits_total": l1 + l2,
        "bias_bits_total": b1 + b2,
        "all_parameter_bits": l1 + l2 + b1 + b2,
        "all_parameter_bytes": (l1 + l2 + b1 + b2 + 7) // 8,
    }


# --------------------------------------------------------------------------
# Cross-check against the frozen Stage-1 RTL
# --------------------------------------------------------------------------

def parse_fabric_ports(path: str) -> Dict[str, Tuple[str, int]]:
    """Parse the port list of the Stage-1 fabric: name -> (direction, width)."""
    src = open(path).read()
    m = re.search(r"module\s+mnist_mlp_fabric\s*\((.*?)\n\);", src, re.S)
    if not m:
        raise RuntimeError("could not find the fabric port list in %s" % path)
    body = re.sub(r"//[^\n]*", "", m.group(1))
    ports: Dict[str, Tuple[str, int]] = {}
    for decl in body.split(","):
        d = " ".join(decl.split())
        if not d:
            continue
        mm = re.match(r"(input|output)\s+wire\s*(?:\[(\d+):(\d+)\]\s*)?(\w+)", d)
        if not mm:
            raise RuntimeError("unparsed port declaration: %r" % d)
        direction = mm.group(1)
        width = 1 if mm.group(2) is None else int(mm.group(2)) - int(mm.group(3)) + 1
        ports[mm.group(4)] = (direction, width)
    return ports


def verify_against_rtl(path: str, cfg: FabricConfig = FabricConfig()) -> None:
    """Fail closed if this description does not match the frozen fabric."""
    rtl = parse_fabric_ports(path)
    iface = build_interface(cfg)
    expected: List[Port] = [iface["clk"], iface["rst"]]
    for kind in ("weight", "bias"):
        expected.extend(iface[kind].ports)
    for p in expected:
        if p.name not in rtl:
            raise RuntimeError("fabric has no port %r" % p.name)
        direction, width = rtl[p.name]
        if direction != p.direction or width != p.width:
            raise RuntimeError(
                "port %s: interface says %s[%d], fabric declares %s[%d]"
                % (p.name, p.direction, p.width, direction, width))


def describe(cfg: FabricConfig = FabricConfig()) -> Dict[str, object]:
    """JSON-serialisable form of the whole interface."""
    iface = build_interface(cfg)
    out: Dict[str, object] = {
        "read_latency_cycles": iface["read_latency"],
        "timing_contract": iface["timing_contract"],
        "capture_model": iface["capture_model"],
        "packing": iface["packing"],
        "out_of_range_note": iface["out_of_range_note"],
        "clock": asdict(iface["clk"]),
        "reset": asdict(iface["rst"]),
        "storage_footprint": storage_footprint(cfg),
    }
    for kind in ("weight", "bias"):
        port: MemoryPort = iface[kind]
        out[kind + "_port"] = {
            "ports": [dict(asdict(p), memory_direction=p.memory_direction)
                      for p in port.ports],
            "spaces": [asdict(s) for s in port.spaces],
        }
    return out
