"""Stage 5: the fixed-interface wrapper over the PHYSICAL OpenROM macros.

The Stage-2 backend `rtl/mnist_mlp_params_openram.v` models four macros whose
shapes match the logical memories one for one.  Two of those shapes cannot
actually be built by the installed OpenROM, so Stage 5 introduces the physical
organisation -- four 784 x 32 layer-1 banks and 24-bit sign-padded bias words --
and this module emits the wrapper that hides it again.

Both files stay in the tree.  `mnist_mlp_params_openram.v` is frozen and
unchanged; `mnist_mlp_params_openrom_phys.v` is the Stage-5 addition that
corresponds to macros that exist on disk as GDS.

The wrapper's obligations, all of which the Stage-5 tests check:

  * the four layer-1 banks receive the SAME address and are read in PARALLEL,
    so the external read latency is still exactly one cycle,
  * `wmem_data[127:0]` is reassembled bit-exactly from the four 32-bit banks,
  * a physical 24-bit bias word is truncated to its logical width and then SIGN
    extended onto the 22-bit bus (never zero extended),
  * out-of-range addresses still return zero,
  * the port list is byte-for-byte the frozen Stage-1 interface.
"""

from __future__ import annotations

from typing import Dict

from .fabric import FabricConfig, derive_widths
from .param_verilog import (OPENROM_CONVENTION, _bitrev, _common_header,
                            _iface_ports, _port_block, _wrap)
from .phys_image import (L1_BANKS, L1_BANK_BITS, PHYS_ORDER, PhysImage,
                         macros_of)

MODULE = "mnist_mlp_params_openrom_phys"


def _phys_macro_module(img: PhysImage, name: str, addr_bits: int) -> str:
    """Behavioural model of one PHYSICALLY GENERATED OpenROM macro.

    MODEL2RTL BEHAVIOURAL MODEL OF THE GENERATED OpenROM CONTENTS.
    This is NOT OpenROM-generated Verilog.
    """
    digits = img.width // 4
    arms = "\n".join(
        "                %d'd%d: dout0 <= %d'h%0*x;"
        % (addr_bits, a, img.width, digits, _bitrev(v, img.width))
        for a, v in enumerate(img.rows))
    slice_txt = "[%d:%d]" % (img.logical_bit_slice[1], img.logical_bit_slice[0])
    return f"""
// ---------------------------------------------------------------------------
// {name}
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "{img.name}" ({img.depth} words x {img.width} bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/{img.name}/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "{img.logical_memory}"
// ({img.logical_depth} x {img.logical_width}):
//   bank {img.bank_index} of {img.bank_count}, logical bits {slice_txt}
//   {img.transform}
// Physical image sha256 {img.sha256()}
// Bit order on dout0: {OPENROM_CONVENTION.split('. ')[2]}.
// ---------------------------------------------------------------------------
module {name} (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [{addr_bits - 1}:0]{' ' * max(0, 11 - len(str(addr_bits - 1)))}addr0,
    output reg  [{img.width - 1}:0]{' ' * max(0, 11 - len(str(img.width - 1)))}dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
{arms}
                default: dout0 <= {{{img.width}{{1'b0}}}};
            endcase
        end
    end
endmodule
"""


def _abits(depth: int) -> int:
    return max(1, (depth - 1).bit_length())


def emit_physical_backend(phys: Dict[str, PhysImage],
                          cfg: FabricConfig = FabricConfig(),
                          module_name: str = MODULE,
                          macro_status: Dict[str, str] | None = None) -> str:
    w = derive_widths(cfg)
    ww, bw = w["weight_word_bits"], w["bias_data_bits"]
    waw, baw = w["weight_addr_bits"], w["bias_addr_bits"]

    banks = [phys["weights_l1_b%d" % b] for b in range(L1_BANKS)]
    wl2, bl1, bl2 = phys["weights_l2"], phys["bias_l1"], phys["bias_l2"]

    a_b = _abits(banks[0].depth)
    a_wl2, a_bl1, a_bl2 = (_abits(wl2.depth), _abits(bl1.depth),
                           _abits(bl2.depth))

    status = macro_status or {}
    status_lines = "".join("//   %-14s %s\n"
                           % (n, status.get(n, "physical macro NOT generated"))
                           for n in PHYS_ORDER)

    extra = (
        "// PHYSICAL ORGANISATION (Stage 5)\n"
        "//   The installed OpenROM cannot route a 784 x 128 array and cannot\n"
        "//   express a 22-bit or 17-bit word (word_size is in BYTES). Two\n"
        "//   approved, exactly reversible physical transformations are used:\n"
        "//     * weights_l1 is split into %d parallel banks of %d x %d bits;\n"
        "//       every bank sees the same address and all are read together,\n"
        "//       so the external read latency is still ONE cycle.\n"
        "//     * both bias memories are stored as 24-bit SIGN EXTENDED words\n"
        "//       and truncated back to their logical width here.\n"
        "//   The logical memories, the bit packing and the fabric interface\n"
        "//   are unchanged. The canonical Stage-2 images remain authoritative.\n"
        "//\n" % (L1_BANKS, banks[0].depth, L1_BANK_BITS)
        + "// OpenROM DATA CONVENTION (proven empirically, Stage 2 and Stage 5)\n"
        + "".join("//   %s\n" % line for line in _wrap(OPENROM_CONVENTION, 72))
        + "//\n// PHYSICAL MACRO STATUS AT GENERATION TIME\n"
        + status_lines
        + "//\n// PHYSICAL IMAGES (model2rtl-phys-image-v1)\n"
        + "".join("//   %-14s %4d x %3d  <- %-11s %s  sha256 %s\n"
                  % (p.name, p.depth, p.width, p.logical_memory,
                     "[%d:%d]" % (p.logical_bit_slice[1],
                                  p.logical_bit_slice[0]), p.sha256())
                  for p in (list(banks) + [wl2, bl1, bl2])))

    macros = "".join(
        _phys_macro_module(p, "rom_phys_" + p.name, _abits(p.depth))
        for p in (list(banks) + [wl2, bl1, bl2]))

    def rev(dst, src, width, indent="    "):
        return (f"{indent}generate\n"
                f"{indent}    for (gi = 0; gi < {width}; gi = gi + 1)"
                f" begin : {dst.upper()}_REV\n"
                f"{indent}        assign {dst}[gi] = {src}[{width - 1} - gi];\n"
                f"{indent}    end\n"
                f"{indent}endgenerate")

    bank_inst = "\n".join(
        "    rom_phys_weights_l1_b{b} u_wl1_b{b} (.clk0(clk), .cs0(wsel_l1),\n"
        "                                .addr0(wmem_addr[{hi}:0]),"
        " .dout0(wl1b{b}_dout));".format(b=b, hi=a_b - 1)
        for b in range(L1_BANKS))
    bank_wires = "\n".join(
        "    wire [%d:0] wl1b%d_dout;\n    wire [%d:0] wl1b%d_word;"
        % (L1_BANK_BITS - 1, b, L1_BANK_BITS - 1, b) for b in range(L1_BANKS))
    bank_rev = "\n".join(rev("wl1b%d_word" % b, "wl1b%d_dout" % b,
                             L1_BANK_BITS) for b in range(L1_BANKS))
    concat = ", ".join("wl1b%d_word" % b for b in
                       range(L1_BANKS - 1, -1, -1))

    return (_common_header(cfg, module_name + ".v -- PHYSICAL OpenROM backend "
                           "(Stage 5)", extra)
            + macros
            + f"""
// ---------------------------------------------------------------------------
// Stage-5 physical backend wrapper. ASIC / SKY130 only.
//
// Presents byte-for-byte the frozen logical interface and hides the fact that
// layer-1 weights now live in {L1_BANKS} macros and the biases are stored 24 bits wide.
// ---------------------------------------------------------------------------
module {module_name} (
{_port_block(_iface_ports(cfg), out_kind="wire")}
);

    genvar gi;

    // ---- macro strobes and range qualification -------------------------
    wire wsel_l1 = wmem_en && (wmem_layer == 1'b0) && (wmem_addr < {waw}'d{banks[0].depth});
    wire wsel_l2 = wmem_en && (wmem_layer == 1'b1) && (wmem_addr < {waw}'d{wl2.depth});
    wire bsel_l1 = bmem_en && (bmem_layer == 1'b0) && (bmem_addr < {baw}'d{bl1.depth});
    wire bsel_l2 = bmem_en && (bmem_layer == 1'b1) && (bmem_addr < {baw}'d{bl2.depth});

    // the macros register their address, so the layer decision must be
    // delayed by exactly the same cycle to stay aligned with the data
    reg wlayer_d, wvalid_d, blayer_d, bvalid_d;
    always @(posedge clk) begin
        if (wmem_en) begin
            wlayer_d <= wmem_layer;
            wvalid_d <= wsel_l1 || wsel_l2;
        end
        if (bmem_en) begin
            blayer_d <= bmem_layer;
            bvalid_d <= bsel_l1 || bsel_l2;
        end
    end

    // ---- layer-1 weight banks: ONE address, {L1_BANKS} macros, read in parallel ----
{bank_wires}
{bank_inst}
{bank_rev}
    // logical word = {{bank3, bank2, bank1, bank0}}
    wire [{ww - 1}:0] wl1_word = {{{concat}}};

    // ---- the byte-granular macros ---------------------------------------
    wire [{wl2.width - 1}:0]  wl2_dout;
    wire [{wl2.width - 1}:0]  wl2_word;
    wire [{bl1.width - 1}:0]  bl1_dout;
    wire [{bl1.width - 1}:0]  bl1_word;
    wire [{bl2.width - 1}:0]  bl2_dout;
    wire [{bl2.width - 1}:0]  bl2_word;

    rom_phys_weights_l2 u_wl2 (.clk0(clk), .cs0(wsel_l2),
                                .addr0(wmem_addr[{a_wl2 - 1}:0]), .dout0(wl2_dout));
    rom_phys_bias_l1    u_bl1 (.clk0(clk), .cs0(bsel_l1),
                                .addr0(bmem_addr[{a_bl1 - 1}:0]), .dout0(bl1_dout));
    rom_phys_bias_l2    u_bl2 (.clk0(clk), .cs0(bsel_l2),
                                .addr0(bmem_addr[{a_bl2 - 1}:0]), .dout0(bl2_dout));

{rev('wl2_word', 'wl2_dout', wl2.width)}
{rev('bl1_word', 'bl1_dout', bl1.width)}
{rev('bl2_word', 'bl2_dout', bl2.width)}

    // ---- undo the physical bias padding ---------------------------------
    // The physical word is sign extended to {bl1.width} bits.  Take the logical
    // low bits back and SIGN extend them onto the {bw}-bit bus. Never zero extend.
    wire [{bl1.logical_width - 1}:0] bl1_logical = bl1_word[{bl1.logical_width - 1}:0];
    wire [{bl2.logical_width - 1}:0] bl2_logical = bl2_word[{bl2.logical_width - 1}:0];

    // ---- present the fixed interface ------------------------------------
    assign wmem_data = (wvalid_d == 1'b0) ? {{{ww}{{1'b0}}}}
                     : (wlayer_d == 1'b0) ? wl1_word
                                          : {{{ww - wl2.width}'d0, wl2_word}};

    assign bmem_data = (bvalid_d == 1'b0) ? {{{bw}{{1'b0}}}}
                     : (blayer_d == 1'b0)
                       ? {{{{{bw - bl1.logical_width}{{bl1_logical[{bl1.logical_width - 1}]}}}}, bl1_logical}}
                       : {{{{{bw - bl2.logical_width}{{bl2_logical[{bl2.logical_width - 1}]}}}}, bl2_logical}};

endmodule

`default_nettype wire
""")


def emit_physical_selector(cfg: FabricConfig = FabricConfig(),
                           backend: str = MODULE) -> str:
    """Binds the abstract module `mnist_mlp_params` to the Stage-5 backend."""
    w = derive_widths(cfg)
    return f"""// ===========================================================================
// Build-time backend selector: `mnist_mlp_params` -> {backend}
// GENERATED FILE. Compile exactly ONE selector file per build.
// ===========================================================================

`default_nettype none

module mnist_mlp_params (
    input  wire          clk,
    input  wire          wmem_en,
    input  wire          wmem_layer,
    input  wire [{w['weight_addr_bits'] - 1}:0]    wmem_addr,
    output wire [{w['weight_word_bits'] - 1}:0]   wmem_data,
    input  wire          bmem_en,
    input  wire          bmem_layer,
    input  wire [{w['bias_addr_bits'] - 1}:0]     bmem_addr,
    output wire [{w['bias_data_bits'] - 1}:0]    bmem_data
);

    {backend} u_backend (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data)
    );

endmodule

`default_nettype wire
"""
