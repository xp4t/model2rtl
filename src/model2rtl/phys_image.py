"""Stage 5: PHYSICAL parameter images for the OpenROM macros.

There are now two representations of the same parameters:

  LOGICAL   -- :mod:`model2rtl.param_image`, the canonical Stage-2 images.  This
               is what the fabric sees and it is authoritative.  Nothing here
               may redefine or overwrite it.
  PHYSICAL  -- what OpenROM can actually be asked to build.  Two shape
               transformations are needed, both approved for Stage 5 and both
               required to be exactly reversible:

                 * bias width padding: OpenROM's word_size is expressed in
                   BYTES, so a 22-bit or 17-bit word cannot be requested.  The
                   physical word is the SIGN EXTENSION of the logical word to
                   24 bits.  Never zero extension.
                 * layer-1 weight banking: the installed OpenROM cannot route a
                   784 x 128 array (signal_escape_router fails on clk0).  The
                   logical row is split into four 32-bit slices held in four
                   784 x 32 macros, all addressed together and read in
                   parallel, so the external read latency stays one cycle.

Every physical image is derived deterministically from the canonical logical
image, and :func:`decode_physical` maps the whole set back.  The test suite
requires decode(build(logical)) == logical for every row of every memory.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .param_image import IMAGE_ORDER, ParamImage

#: OpenROM word widths are a whole number of bytes.
BYTE_BITS = 8

#: Physical bias word width (3 bytes).  Approved for Stage 5.
BIAS_PHYS_BITS = 24

#: Physical layer-1 weight bank width and count.  Approved for Stage 5.
L1_BANK_BITS = 32
L1_BANKS = 4

#: Proven in Stage 2 by an 8192/8192-cell diagnostic against a generated macro:
#: the OpenROM *output port* presents the word bit-reversed,
#:     dout0[b] == word_bit(word_bits - 1 - b).
#: The ROM *input data file* is plain big-endian hex, one word per depth index,
#: which is what write_rom_data proves against the canonical image.  Recorded
#: here so every physical image carries the convention it was built under.
OPENROM_DOUT_CONVENTION = ("dout0[b] = word_bit(word_bits-1-b); the hex input "
                           "file is big-endian, row 0 first")


class PhysImageError(ValueError):
    pass


def _sign_extend(value: int, from_bits: int, to_bits: int) -> int:
    """Two's-complement sign extension. Never zero extension."""
    if to_bits < from_bits:
        raise PhysImageError("cannot sign extend %d -> %d" % (from_bits, to_bits))
    if value < 0 or value >> from_bits:
        raise PhysImageError("value does not fit %d bits" % from_bits)
    if value >> (from_bits - 1):                       # negative
        return value | (((1 << (to_bits - from_bits)) - 1) << from_bits)
    return value


def _truncate(value: int, to_bits: int) -> int:
    return value & ((1 << to_bits) - 1)


@dataclass(frozen=True)
class PhysImage:
    """One physical OpenROM macro image, fully determined and hashable."""

    name: str                       # macro name, e.g. weights_l1_b2
    logical_memory: str             # weights_l1 / weights_l2 / bias_l1 / bias_l2
    logical_depth: int
    logical_width: int
    bank_index: int                 # 0 when the memory is not banked
    bank_count: int
    logical_bit_slice: Tuple[int, int]     # (lsb, msb) inclusive, of the logical word
    depth: int                      # physical depth (always == logical depth)
    width: int                      # physical width, a multiple of 8
    rows: tuple
    transform: str                  # human-readable derivation rule
    sign_padded: bool
    bit_order: str = OPENROM_DOUT_CONVENTION

    def __post_init__(self):
        if self.width % BYTE_BITS:
            raise PhysImageError("%s: physical width %d is not byte granular"
                                 % (self.name, self.width))
        if len(self.rows) != self.depth:
            raise PhysImageError("%s: %d rows for depth %d"
                                 % (self.name, len(self.rows), self.depth))
        for i, v in enumerate(self.rows):
            if v < 0 or v >> self.width:
                raise PhysImageError("%s: row %d does not fit %d bits"
                                     % (self.name, i, self.width))

    # -- serialisation, deliberately mirroring ParamImage ----------------
    def canonical_bytes(self) -> bytes:
        row_bytes = self.width // BYTE_BITS
        out = bytearray()
        out += b"model2rtl-phys-image-v1\n"
        out += ("%s %s %d %d %d/%d %d:%d\n"
                % (self.name, self.logical_memory, self.depth, self.width,
                   self.bank_index, self.bank_count,
                   self.logical_bit_slice[1], self.logical_bit_slice[0])).encode()
        for v in self.rows:
            out += int(v).to_bytes(row_bytes, "big")
        return bytes(out)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def hex_lines(self) -> List[str]:
        digits = self.width // 4
        return ["%0*x" % (digits, v) for v in self.rows]

    def hex_stream(self) -> str:
        """Exactly the bytes handed to OpenROM as rom_data."""
        return "".join(self.hex_lines())

    def bit_string_msb_first(self) -> str:
        return "".join(format(v, "0%db" % self.width) for v in self.rows)

    def word_size_bytes(self) -> int:
        return self.width // BYTE_BITS

    def to_dict(self) -> dict:
        return {
            "macro": self.name,
            "logical_memory": self.logical_memory,
            "logical_depth": self.logical_depth,
            "logical_width": self.logical_width,
            "bank_index": self.bank_index,
            "bank_count": self.bank_count,
            "logical_bit_slice": "[%d:%d]" % (self.logical_bit_slice[1],
                                              self.logical_bit_slice[0]),
            "physical_depth": self.depth,
            "physical_width": self.width,
            "physical_bits": self.depth * self.width,
            "word_size_bytes": self.word_size_bytes(),
            "sign_padded": self.sign_padded,
            "transform": self.transform,
            "bit_order_transform": self.bit_order,
            "sha256": self.sha256(),
        }


# --------------------------------------------------------------------------
# Forward transformation: logical -> physical
# --------------------------------------------------------------------------

def bank_weights_l1(img: ParamImage) -> List[PhysImage]:
    """784 x 128  ->  4 x (784 x 32).  Bank b carries logical bits [32b+31:32b]."""
    if img.width != L1_BANK_BITS * L1_BANKS:
        raise PhysImageError("weights_l1 width %d is not %d x %d"
                             % (img.width, L1_BANKS, L1_BANK_BITS))
    out = []
    for b in range(L1_BANKS):
        lo = b * L1_BANK_BITS
        rows = tuple((v >> lo) & ((1 << L1_BANK_BITS) - 1) for v in img.rows)
        out.append(PhysImage(
            name="%s_b%d" % (img.name, b),
            logical_memory=img.name,
            logical_depth=img.depth,
            logical_width=img.width,
            bank_index=b,
            bank_count=L1_BANKS,
            logical_bit_slice=(lo, lo + L1_BANK_BITS - 1),
            depth=img.depth,
            width=L1_BANK_BITS,
            rows=rows,
            transform="physical_row = (logical_row >> %d) & 0x%08x; all %d "
                      "banks share one address and are read in parallel"
                      % (lo, (1 << L1_BANK_BITS) - 1, L1_BANKS),
            sign_padded=False))
    return out


def pad_bias(img: ParamImage) -> PhysImage:
    """32 x 22 or 10 x 17  ->  depth x 24, SIGN extended.  Never zero extended."""
    if not img.signed:
        raise PhysImageError("%s is not a signed memory" % img.name)
    rows = tuple(_sign_extend(v, img.width, BIAS_PHYS_BITS) for v in img.rows)
    return PhysImage(
        name=img.name,
        logical_memory=img.name,
        logical_depth=img.depth,
        logical_width=img.width,
        bank_index=0,
        bank_count=1,
        logical_bit_slice=(0, img.width - 1),
        depth=img.depth,
        width=BIAS_PHYS_BITS,
        rows=rows,
        transform="physical_row = sign_extend_%d(logical_row_%d); the wrapper "
                  "truncates back to %d bits and re-extends to the 22-bit bus"
                  % (BIAS_PHYS_BITS, img.width, img.width),
        sign_padded=True)


def passthrough(img: ParamImage) -> PhysImage:
    """Byte-granular memory that needs no transformation at all."""
    if img.width % BYTE_BITS:
        raise PhysImageError("%s width %d is not byte granular"
                             % (img.name, img.width))
    return PhysImage(
        name=img.name,
        logical_memory=img.name,
        logical_depth=img.depth,
        logical_width=img.width,
        bank_index=0,
        bank_count=1,
        logical_bit_slice=(0, img.width - 1),
        depth=img.depth,
        width=img.width,
        rows=tuple(img.rows),
        transform="identity: the logical word is already byte granular",
        sign_padded=False)


def build_physical_images(images: Dict[str, ParamImage]
                          ) -> Dict[str, PhysImage]:
    """Every physical macro image, keyed by macro name."""
    out: Dict[str, PhysImage] = {}
    for p in bank_weights_l1(images["weights_l1"]):
        out[p.name] = p
    out["weights_l2"] = passthrough(images["weights_l2"])
    out["bias_l1"] = pad_bias(images["bias_l1"])
    out["bias_l2"] = pad_bias(images["bias_l2"])
    return out


PHYS_ORDER = ("weights_l1_b0", "weights_l1_b1", "weights_l1_b2",
              "weights_l1_b3", "weights_l2", "bias_l1", "bias_l2")


def macros_of(logical_name: str) -> Tuple[str, ...]:
    if logical_name == "weights_l1":
        return tuple("weights_l1_b%d" % b for b in range(L1_BANKS))
    return (logical_name,)


# --------------------------------------------------------------------------
# Reverse transformation: physical -> logical
# --------------------------------------------------------------------------

def decode_logical_rows(phys: Dict[str, PhysImage], logical_name: str,
                        logical_width: int) -> List[int]:
    """Rebuild one logical memory's rows from its physical macro(s) alone."""
    names = macros_of(logical_name)
    parts = [phys[n] for n in names]
    depth = parts[0].depth
    for p in parts:
        if p.depth != depth:
            raise PhysImageError("%s: banks disagree on depth" % logical_name)

    rows = []
    for a in range(depth):
        if len(parts) == 1:
            p = parts[0]
            v = p.rows[a]
            if p.sign_padded:
                # drop the sign padding: the logical value is the low bits
                if _sign_extend(_truncate(v, logical_width), logical_width,
                                p.width) != v:
                    raise PhysImageError(
                        "%s row %d: padding is not a pure sign extension"
                        % (logical_name, a))
                v = _truncate(v, logical_width)
            elif v >> logical_width:
                raise PhysImageError("%s row %d exceeds the logical width"
                                     % (logical_name, a))
            rows.append(v)
        else:
            word = 0
            for p in sorted(parts, key=lambda q: q.bank_index):
                lo, hi = p.logical_bit_slice
                if hi - lo + 1 != p.width:
                    raise PhysImageError("%s: bank slice width mismatch"
                                         % logical_name)
                word |= p.rows[a] << lo
            if word >> logical_width:
                raise PhysImageError("%s row %d exceeds the logical width"
                                     % (logical_name, a))
            rows.append(word)
    return rows


def decode_physical(phys: Dict[str, PhysImage],
                    logical: Dict[str, ParamImage]) -> Dict[str, List[int]]:
    """Decode every physical macro set back to logical rows."""
    return {name: decode_logical_rows(phys, name, logical[name].width)
            for name in IMAGE_ORDER}


def verify_roundtrip(phys: Dict[str, PhysImage],
                     logical: Dict[str, ParamImage]) -> Dict[str, object]:
    """decode(build(logical)) == logical, row by row.  Raises on any mismatch."""
    decoded = decode_physical(phys, logical)
    detail = {}
    total_rows = total_bad = 0
    for name in IMAGE_ORDER:
        want = list(logical[name].rows)
        got = decoded[name]
        if len(want) != len(got):
            raise PhysImageError("%s: decoded %d rows, expected %d"
                                 % (name, len(got), len(want)))
        bad = [i for i, (a, b) in enumerate(zip(want, got)) if a != b]
        detail[name] = {
            "rows_checked": len(want),
            "mismatches": len(bad),
            "first_mismatches": bad[:5],
            "macros": list(macros_of(name)),
        }
        total_rows += len(want)
        total_bad += len(bad)
    if total_bad:
        raise PhysImageError("physical -> logical round trip failed: %s"
                             % detail)
    return {"per_memory": detail, "rows_checked": total_rows,
            "mismatches": total_bad}


# --------------------------------------------------------------------------
# Bus-level view through the physical path
# --------------------------------------------------------------------------

def weight_bus_word_from_physical(phys: Dict[str, PhysImage], layer: int,
                                  addr: int) -> int:
    """wmem_data reconstructed from the physical banks only."""
    name = "weights_l1" if layer == 0 else "weights_l2"
    parts = [phys[n] for n in macros_of(name)]
    if addr < 0 or addr >= parts[0].depth:
        return 0
    word = 0
    for p in parts:
        word |= p.rows[addr] << p.logical_bit_slice[0]
    return word


def bias_bus_word_from_physical(phys: Dict[str, PhysImage], layer: int,
                                addr: int, bus_bits: int = 22) -> int:
    """bmem_data reconstructed from the physical (padded) bias macro only.

    Physical 24-bit word -> truncate to the logical width -> sign extend to the
    22-bit bus.  For layer 1 the logical width already is 22.
    """
    p = phys["bias_l1" if layer == 0 else "bias_l2"]
    if addr < 0 or addr >= p.depth:
        return 0
    logical_width = p.logical_width
    v = _truncate(p.rows[addr], logical_width)
    return _truncate(_sign_extend(v, logical_width, bus_bits), bus_bits)
