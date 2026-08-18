"""Verilog emitters for the Stage-2 parameter-storage backends.

Both emitters take the SAME canonical images (model2rtl.param_image) and
produce the SAME logical interface (model2rtl.memif), which is transcribed from
the frozen Stage-1 fabric.  Neither emitter has its own packing logic.

  * :func:`emit_portable`  -- Backend A. Pure synthesizable Verilog-2001,
    case/localparam constants, no $readmemh, no initial block, no vendor or
    tool specific construct. FPGA and ASIC alike.

  * :func:`emit_openram_wrapper` -- Backend B's fixed-interface wrapper plus
    the behavioural read models it instantiates.  Those models are OURS -- a
    model2rtl behavioural model of the generated OpenROM contents.  They are
    NOT OpenROM-generated Verilog and must never be described as such.
"""

from __future__ import annotations

from typing import Dict, List

from .fabric import FabricConfig, derive_widths
from .memif import build_interface
from .param_image import ParamImage, bias_bus_word, weight_bus_word


def _port_block(names_widths, out_kind: str = "reg ") -> str:
    lines = []
    n = len(names_widths)
    for i, (direction, width, name, comment) in enumerate(names_widths):
        rng = "" if width == 1 else "[%d:0] " % (width - 1)
        kind = "wire" if direction == "input" else out_kind
        sep = "," if i < n - 1 else ""
        decl = "    %-6s %s %-9s%s%s" % (direction, kind, rng, name, sep)
        lines.append("%-52s// %s" % (decl, comment) if comment else decl)
    return "\n".join(l.rstrip() for l in lines)


def _iface_ports(cfg: FabricConfig):
    w = derive_widths(cfg)
    return [
        ("input", 1, "clk", "single clock, shared with the fabric"),
        ("input", 1, "wmem_en", "read strobe"),
        ("input", 1, "wmem_layer", "0 = layer 1, 1 = layer 2"),
        ("input", w["weight_addr_bits"], "wmem_addr", "input-feature index"),
        ("output", w["weight_word_bits"], "wmem_data", "packed weight indices"),
        ("input", 1, "bmem_en", "read strobe"),
        ("input", 1, "bmem_layer", "0 = layer 1, 1 = layer 2"),
        ("input", w["bias_addr_bits"], "bmem_addr", "output-neuron index"),
        ("output", w["bias_data_bits"], "bmem_data", "sign-extended bias"),
    ]


def _common_header(cfg: FabricConfig, title: str, extra: str) -> str:
    w = derive_widths(cfg)
    iface = build_interface(cfg)
    return f"""// ===========================================================================
// {title}
//
// GENERATED FILE -- do not edit by hand.
//
// Stage-2 parameter-storage backend for the model2rtl MNIST MLP.
// It presents exactly the memory interface that rtl/mnist_mlp_fabric.v already
// declares; the fabric is unchanged and cannot tell which backend is attached.
//
// TIMING CONTRACT (identical for every Stage-2 backend)
//   {iface['timing_contract']}
//   Reference model:
//       always @(posedge clk) if (en) data_r <= MEM[{{layer, addr}}];
//       assign data = data_r;
//
// WEIGHT WORD PACKING
//   {iface['packing']['rule']}
//   orientation {iface['packing']['orientation']}
//   neuron 0 occupies the least significant nibble
//   layer 1 -> {iface['packing']['layer1_field']}
//   layer 2 -> {iface['packing']['layer2_field']}; the unused high bits
//   [{w['weight_word_bits'] - 1}:{cfg.n_out * w['index_bits']}] are driven to ZERO and hold no model data.
//
// BIAS
//   layer 1 biases are {w['layer1_bias_bits']}-bit signed and occupy the whole {w['bias_data_bits']}-bit bus.
//   layer 2 biases are {w['layer2_bias_bits']}-bit signed and are SIGN EXTENDED to {w['bias_data_bits']} bits,
//   never zero extended.
//
// INVALID ADDRESSES
//   Any address outside a layer's depth returns all zeros.  No invalid address
//   aliases onto a valid parameter row.
//
// There is no reset port: a parameter memory holds no architectural state.  The
// output registers are X until the first enabled read, and the fabric never
// consumes data that it did not strobe.
//
{extra}// ===========================================================================

`default_nettype none
"""


def _case_arms(img: ParamImage, addr_bits: int, word_bits: int,
               pad_hi: int, indent: str, signed_comment: bool = False) -> str:
    lines = []
    digits = (img.width + 3) // 4
    for addr, value in enumerate(img.rows):
        if pad_hi > 0:
            rhs = "{%d'd0, %d'h%0*x}" % (pad_hi, img.width, digits, value)
        else:
            rhs = "%d'h%0*x" % (word_bits, digits, value)
        comment = ""
        if signed_comment:
            lim = 1 << (img.width - 1)
            sv = value - (1 << img.width) if value >= lim else value
            comment = "  // %+d" % sv
        lines.append("%s%d'd%d: %s <= %s;%s"
                     % (indent, addr_bits, addr, "DATA", rhs, comment))
    return "\n".join(lines)


def _rom_case(img: ParamImage, target: str, addr_sig: str, addr_bits: int,
              word_bits: int, pad_hi: int, indent: str,
              signed_comment: bool = False) -> str:
    body = _case_arms(img, addr_bits, word_bits, pad_hi, indent + "    ",
                      signed_comment).replace("DATA", target)
    return ("%scase (%s)\n%s\n%s    default: %s <= {%d{1'b0}};\n%sendcase"
            % (indent, addr_sig, body, indent, target, word_bits, indent))


def emit_portable(images: Dict[str, ParamImage],
                  cfg: FabricConfig = FabricConfig(),
                  module_name: str = "mnist_mlp_params_portable") -> str:
    """Backend A: pure Verilog-2001 case/constant parameter memory."""
    w = derive_widths(cfg)
    ww, bw = w["weight_word_bits"], w["bias_data_bits"]
    waw, baw = w["weight_addr_bits"], w["bias_addr_bits"]

    wl1, wl2 = images["weights_l1"], images["weights_l2"]
    bl1, bl2 = images["bias_l1"], images["bias_l2"]

    # layer-2 biases are widened to the bus by SIGN extension, so build a
    # bus-width image for them rather than emitting the raw 17-bit value
    bl2_bus = ParamImage(
        name="bias_l2_bus", depth=bl2.depth, width=bw,
        rows=tuple(bias_bus_word(images, 1, a) for a in range(bl2.depth)),
        packing="bias_l2 sign extended from %d to %d bits" % (bl2.width, bw),
        orientation=bl2.orientation, signed=True)

    extra = ("// SOURCE IMAGES (canonical, model2rtl-param-image-v1)\n"
             + "".join("//   %-11s depth %4d  width %3d  sha256 %s\n"
                       % (i.name, i.depth, i.width, i.sha256())
                       for i in (wl1, wl2, bl1, bl2)))

    return (_common_header(cfg, module_name + ".v -- PORTABLE parameter backend",
                           extra)
            + f"""
// ---------------------------------------------------------------------------
// Backend A: portable. Pure synthesizable Verilog-2001. No vendor primitive, no
// FPGA or ASIC macro, no memory IP, no attribute, no synthesis pragma, no
// $readmemh, no initial block. Usable unchanged for FPGA and ASIC.
// ---------------------------------------------------------------------------
module {module_name} (
{_port_block(_iface_ports(cfg))}
);

    // ---- weight memory: registered output, one packed word per input feature
    always @(posedge clk) begin
        if (wmem_en) begin
            if (wmem_layer == 1'b0) begin
{_rom_case(wl1, "wmem_data", "wmem_addr", waw, ww, 0, " " * 16)}
            end else begin
{_rom_case(wl2, "wmem_data", "wmem_addr", waw, ww, ww - wl2.width, " " * 16)}
            end
        end
    end

    // ---- bias memory: registered output, one signed bias per neuron
    always @(posedge clk) begin
        if (bmem_en) begin
            if (bmem_layer == 1'b0) begin
{_rom_case(bl1, "bmem_data", "bmem_addr", baw, bw, 0, " " * 16, True)}
            end else begin
{_rom_case(bl2_bus, "bmem_data", "bmem_addr", baw, bw, 0, " " * 16, True)}
            end
        end
    end

endmodule

`default_nettype wire
""")


# --------------------------------------------------------------------------
# Backend B: OpenRAM/OpenROM macro wrapper + our own behavioural models
# --------------------------------------------------------------------------

#: Proven OpenROM data convention (see scripts/gen_weight_rom_openram.py and
#: the Stage-2 report; established empirically from a generated SPICE netlist).
OPENROM_CONVENTION = (
    "OpenROM stores the input file as a big-endian bit stream, first bit "
    "first. Word A of the file lands at addr0 = A. Within a word, the macro "
    "drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, "
    "i.e. dout0 is BIT REVERSED with respect to a Verilog [word_bits-1:0] "
    "literal. This was proven empirically against a generated SPICE netlist, "
    "not assumed."
)


def _bitrev(value: int, width: int) -> int:
    out = 0
    for i in range(width):
        if (value >> i) & 1:
            out |= 1 << (width - 1 - i)
    return out


def _macro_module(img: ParamImage, name: str, addr_bits: int) -> str:
    """Behavioural model of one generated OpenROM macro.

    MODEL2RTL BEHAVIOURAL MODEL OF THE GENERATED OpenROM CONTENTS.
    This is NOT OpenROM-generated Verilog.
    """
    digits = (img.width + 3) // 4
    arms = "\n".join(
        "                %d'd%d: dout0 <= %d'h%0*x;"
        % (addr_bits, a, img.width, digits, _bitrev(v, img.width))
        for a, v in enumerate(img.rows))
    return f"""
// ---------------------------------------------------------------------------
// {name}
//
// model2rtl behavioural model for the generated OpenROM contents of the
// "{img.name}" macro.  It is NOT OpenROM-generated Verilog: the OpenROM
// compiler's own .v output is a byte-oriented, delay-based, non-synthesizable
// stub that does not implement this project's read contract, so it is not used.
//
// Pin names follow the OpenROM macro convention (clk0 / cs0 / addr0 / dout0) so
// that dropping in the physical macro changes only this module body.
//
// Contents: {img.depth} words x {img.width} bits, canonical image sha256
//   {img.sha256()}
// Bit order: {OPENROM_CONVENTION.split('. ')[2]}.
// ---------------------------------------------------------------------------
module {name} (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [{addr_bits - 1}:0]           addr0,
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


def emit_openram_backend(images: Dict[str, ParamImage],
                         cfg: FabricConfig = FabricConfig(),
                         module_name: str = "mnist_mlp_params_openram",
                         macro_status: Dict[str, str] | None = None) -> str:
    """Backend B: fixed-interface wrapper over four OpenROM-shaped macros."""
    w = derive_widths(cfg)
    ww, bw = w["weight_word_bits"], w["bias_data_bits"]
    waw, baw = w["weight_addr_bits"], w["bias_addr_bits"]
    wl1, wl2 = images["weights_l1"], images["weights_l2"]
    bl1, bl2 = images["bias_l1"], images["bias_l2"]

    def abits(depth):
        return max(1, (depth - 1).bit_length())

    a_wl1, a_wl2 = abits(wl1.depth), abits(wl2.depth)
    a_bl1, a_bl2 = abits(bl1.depth), abits(bl2.depth)

    status = macro_status or {}
    status_lines = "".join(
        "//   %-11s %s\n" % (n, status.get(n, "physical macro NOT generated"))
        for n in ("weights_l1", "weights_l2", "bias_l1", "bias_l2"))

    extra = (
        "// OpenROM DATA CONVENTION (proven empirically, see the Stage-2 report)\n"
        + "".join("//   %s\n" % line for line in
                  _wrap(OPENROM_CONVENTION, 72))
        + "//\n// PHYSICAL MACRO STATUS AT GENERATION TIME\n"
        + status_lines
        + "//\n// The behavioural macro models below are OURS. OpenROM's own .v output\n"
          "// is a byte-oriented, delay-based, non-synthesizable stub and is not used.\n"
        + "//\n// SOURCE IMAGES (canonical, model2rtl-param-image-v1)\n"
        + "".join("//   %-11s depth %4d  width %3d  sha256 %s\n"
                  % (i.name, i.depth, i.width, i.sha256())
                  for i in (wl1, wl2, bl1, bl2)))

    macros = (_macro_module(wl1, "rom_macro_weights_l1", a_wl1)
              + _macro_module(wl2, "rom_macro_weights_l2", a_wl2)
              + _macro_module(bl1, "rom_macro_bias_l1", a_bl1)
              + _macro_module(bl2, "rom_macro_bias_l2", a_bl2))

    def rev_assign(dst, src, width, indent="    "):
        return (f"{indent}generate\n"
                f"{indent}    for (gi = 0; gi < {width}; gi = gi + 1) begin : {dst.upper()}_REV\n"
                f"{indent}        assign {dst}[gi] = {src}[{width - 1} - gi];\n"
                f"{indent}    end\n"
                f"{indent}endgenerate")

    return (_common_header(cfg, module_name + ".v -- OpenRAM/OpenROM ASIC backend",
                           extra)
            + macros
            + f"""
// ---------------------------------------------------------------------------
// Backend B wrapper. ASIC / SKY130 only -- no FPGA portability is claimed.
//
// It presents byte-for-byte the same logical interface as the portable backend
// and hides how many physical macros exist behind it.  Its jobs are:
//   * strobe the right macro for the requested layer,
//   * undo the OpenROM bit reversal,
//   * zero the unused high weight bits for layer 2,
//   * sign extend the layer-2 bias onto the {bw}-bit bus,
//   * return zeros for out-of-range addresses.
// ---------------------------------------------------------------------------
module {module_name} (
{_port_block(_iface_ports(cfg), out_kind="wire")}
);

    genvar gi;

    // ---- macro strobes and range qualification -------------------------
    wire wsel_l1 = wmem_en && (wmem_layer == 1'b0) && (wmem_addr < {waw}'d{wl1.depth});
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

    // ---- macro instances -----------------------------------------------
    wire [{wl1.width - 1}:0] wl1_dout;
    wire [{wl2.width - 1}:0]  wl2_dout;
    wire [{bl1.width - 1}:0]  bl1_dout;
    wire [{bl2.width - 1}:0]  bl2_dout;

    rom_macro_weights_l1 u_wl1 (.clk0(clk), .cs0(wsel_l1),
                                .addr0(wmem_addr[{a_wl1 - 1}:0]), .dout0(wl1_dout));
    rom_macro_weights_l2 u_wl2 (.clk0(clk), .cs0(wsel_l2),
                                .addr0(wmem_addr[{a_wl2 - 1}:0]), .dout0(wl2_dout));
    rom_macro_bias_l1    u_bl1 (.clk0(clk), .cs0(bsel_l1),
                                .addr0(bmem_addr[{a_bl1 - 1}:0]), .dout0(bl1_dout));
    rom_macro_bias_l2    u_bl2 (.clk0(clk), .cs0(bsel_l2),
                                .addr0(bmem_addr[{a_bl2 - 1}:0]), .dout0(bl2_dout));

    // ---- undo the OpenROM bit reversal ----------------------------------
    wire [{wl1.width - 1}:0] wl1_word;
    wire [{wl2.width - 1}:0]  wl2_word;
    wire [{bl1.width - 1}:0]  bl1_word;
    wire [{bl2.width - 1}:0]  bl2_word;
{rev_assign('wl1_word', 'wl1_dout', wl1.width)}
{rev_assign('wl2_word', 'wl2_dout', wl2.width)}
{rev_assign('bl1_word', 'bl1_dout', bl1.width)}
{rev_assign('bl2_word', 'bl2_dout', bl2.width)}

    // ---- present the fixed interface ------------------------------------
    assign wmem_data = (wvalid_d == 1'b0) ? {{{ww}{{1'b0}}}}
                     : (wlayer_d == 1'b0) ? wl1_word
                                          : {{{ww - wl2.width}'d0, wl2_word}};

    // layer-2 biases are SIGN extended from {bl2.width} to {bw} bits, never zero extended
    assign bmem_data = (bvalid_d == 1'b0) ? {{{bw}{{1'b0}}}}
                     : (blayer_d == 1'b0) ? bl1_word
                                          : {{{{{bw - bl2.width}{{bl2_word[{bl2.width - 1}]}}}}, bl2_word}};

endmodule

`default_nettype wire
""")


def _wrap(text: str, width: int) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > width:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# Top level and build-time backend selection
# --------------------------------------------------------------------------

def emit_top(cfg: FabricConfig = FabricConfig(),
             top_name: str = "mnist_mlp_top") -> str:
    """Fabric + one parameter backend, wired through the abstract module name.

    The fabric is instantiated unchanged.  The parameter memory is instantiated
    under the stable abstract name `mnist_mlp_params`; exactly one selector file
    (rtl/mnist_mlp_params_sel_portable.v or rtl/mnist_mlp_params_sel_openram.v)
    defines that module for a given build.  Backend selection is therefore a
    build-time source-list choice: no runtime mux, no parameter, and no change
    of any kind to mnist_mlp_fabric.v.
    """
    w = derive_widths(cfg)
    return f"""// ===========================================================================
// {top_name}.v -- GENERATED FILE, do not edit by hand.
//
// mnist_mlp_fabric (Stage 1, UNCHANGED) + one Stage-2 parameter backend.
//
// BACKEND SELECTION IS BUILD TIME. Compile exactly one of:
//     rtl/{top_name}.v rtl/mnist_mlp_fabric.v rtl/mnist_mlp_params_portable.v \\
//         rtl/mnist_mlp_params_sel_portable.v
//     rtl/{top_name}.v rtl/mnist_mlp_fabric.v rtl/mnist_mlp_params_openram.v \\
//         rtl/mnist_mlp_params_sel_openram.v
// Each selector file defines the module `mnist_mlp_params` and binds it to one
// backend.  The two selectors are mutually exclusive by construction, so there
// is never an unresolved or duplicated module.
// ===========================================================================

`default_nettype none

module {top_name} (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    output wire         in_ready,
    input  wire         in_valid,
    input  wire [{w['act_bits'] - 1}:0]   in_data,
    output wire         busy,
    output wire         done,
    output wire         prediction_valid,
    output wire [{w['prediction_bits'] - 1}:0]   prediction,
    output wire [{w['logits_bits'] - 1}:0] logits
);

    wire         wmem_en, wmem_layer;
    wire [{w['weight_addr_bits'] - 1}:0]  wmem_addr;
    wire [{w['weight_word_bits'] - 1}:0] wmem_data;
    wire         bmem_en, bmem_layer;
    wire [{w['bias_addr_bits'] - 1}:0]   bmem_addr;
    wire [{w['bias_data_bits'] - 1}:0]  bmem_data;

    mnist_mlp_fabric u_fabric (
        .clk(clk), .rst(rst), .start(start),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data),
        .busy(busy), .done(done), .prediction_valid(prediction_valid),
        .prediction(prediction), .logits(logits)
    );

    mnist_mlp_params u_params (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data)
    );

endmodule

`default_nettype wire
"""


def emit_selector(backend_module: str, cfg: FabricConfig = FabricConfig()) -> str:
    """The one-module file that binds the abstract name to a backend."""
    w = derive_widths(cfg)
    return f"""// ===========================================================================
// Build-time backend selector: `mnist_mlp_params` -> {backend_module}
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

    {backend_module} u_backend (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data)
    );

endmodule

`default_nettype wire
"""
