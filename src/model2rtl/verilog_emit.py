"""Verilog-2001 emitters for the Stage-1 compute fabric.

The fabric emitter is a pure function of :class:`FabricConfig`.  It never
touches a trained weight index or a trained bias: those reach the fabric only
through the memory ports it declares.

Testbench emitters live here too, but they are TEST-ONLY: they model the model
parameter memories behaviourally so Stage 1 can be verified before the Stage-2
ROM backends exist.
"""

from __future__ import annotations

from typing import List

from .fabric import FabricConfig, derive_widths


def _hdr(cfg: FabricConfig, w: dict) -> str:
    alpha = ", ".join(str(int(a)) for a in cfg.alphabet)
    return f"""// ===========================================================================
// {cfg.module_name}.v
//
// GENERATED FILE -- do not edit by hand.
// Produced by scripts/gen_compute_fabric.py (model2rtl Stage 1).
//
// Fixed Multiply-Select-Add compute fabric, INPUT-SERIAL / OUTPUT-PARALLEL.
//
// This file is WEIGHT INDEPENDENT.  It contains no trained weight index and no
// trained bias.  Its content is a function of the topology, K, the activation
// format and the frozen Stage-0 arithmetic contract only.  Model parameters are
// supplied at run time through the wmem_* and bmem_* ports.
//
// ---------------------------------------------------------------------------
// TOPOLOGY
//   {cfg.n_in} inputs -> {cfg.n_hidden} hidden (ReLU + requantise) -> {cfg.n_out} logits -> argmax
//   K = {cfg.k}, alphabet[i] = i - {cfg.k // 2}  =>  [{alpha}]
//
// ARITHMETIC (frozen Stage-0 contract)
//   activation        : unsigned {w['act_bits']}-bit, [0, {w['act_max']}], zero point 0
//   weight index      : unsigned {w['index_bits']}-bit
//   weight value      : signed {w['index_bits']}-bit, from the fixed alphabet
//   product           : signed {w['product_bits']}-bit, exact range [{w['product_min']}, {w['product_max']}]
//   layer1 dot product: signed {w['layer1_dot_bits']}-bit
//   layer1 bias       : signed {w['layer1_bias_bits']}-bit, accumulator domain
//   layer1 accumulator: signed {w['layer1_acc_bits']}-bit (dot product + bias)
//   layer2 dot product: signed {w['layer2_dot_bits']}-bit
//   layer2 bias       : signed {w['layer2_bias_bits']}-bit, accumulator domain
//   layer2 accumulator: signed {w['layer2_acc_bits']}-bit (dot product + bias)
//   hidden requantise : h = clamp((max(acc,0) + {w['round_const']}) >> {w['requant_shift']}, 0, {w['act_max']})
//   rounding          : round-half-up (add {w['round_const']}, then shift right {w['requant_shift']})
//   saturation        : clamp to [0, {w['act_max']}]
//   output            : raw signed logits, no requantisation
//   prediction        : argmax, LOWEST index wins on ties (matches numpy.argmax)
//
// ---------------------------------------------------------------------------
// ARCHITECTURE
//
// Exactly K = {cfg.k} product generators exist in this design.  For the CURRENT
// activation x they produce the whole product bank
//
//     prod_bank[k] = x * alphabet[k],   k = 0 .. {cfg.k - 1}
//
// and every output neuron of the currently active layer selects one entry of
// that same bank with its {w['index_bits']}-bit weight index.  There is no multiplier per
// synapse.  The bank is reused across input cycles AND across both layers.
//
//     x -> [ {cfg.k} shared products ] -> {cfg.k}:1 selector per neuron -> accumulator per neuron
//
// ---------------------------------------------------------------------------
// MEMORY INTERFACE (identical for the Stage-2 portable ROM and the Stage-2
// OpenRAM macro; the fabric cannot tell them apart)
//
//   SYNCHRONOUS READ, 1 CYCLE LATENCY:
//     an address driven during cycle T is captured on the posedge that ends
//     cycle T; the corresponding data must be presented during cycle T+1.
//     Equivalent memory-side model:
//         always @(posedge clk) if (en) data_r <= MEM[addr];
//         assign data = data_r;
//
//   WEIGHT WORD PACKING (Stage-0 orientation [in_features, out_features]):
//     wmem_addr  = input-feature index i
//     wmem_data  = one word holding EVERY output neuron's index for input i
//     weight_index[i][j] = wmem_data[j*{w['index_bits']} +: {w['index_bits']}]
//     neuron j = 0 occupies the least significant nibble.
//     layer 1 uses bits [{cfg.n_hidden * w['index_bits'] - 1}:0]; layer 2 uses bits [{cfg.n_out * w['index_bits'] - 1}:0].
//     Bits above the active layer's field are ignored by the fabric.
//
//   BIAS INTERFACE: option B, indexed read (chosen over a wide packed port
//     because finalisation is already one neuron per cycle, so an indexed read
//     costs no extra cycles and keeps the port count and the Stage-2 ROM shape
//     small and identical to the weight interface).
//     bmem_addr = output-neuron index j
//     bmem_data = that neuron's signed bias, sign extended to {w['bias_data_bits']} bits.
//     layer 1 biases are {w['layer1_bias_bits']}-bit, layer 2 biases are {w['layer2_bias_bits']}-bit.
//
// ---------------------------------------------------------------------------
// TRANSACTION PROTOCOL
//   1. rst (synchronous, active high) clears all state.
//   2. Pulse start for one cycle while idle. Accumulators are cleared.
//   3. in_ready rises; stream exactly {cfg.n_in} activations, index order 0..{cfg.n_in - 1},
//      one per cycle in which (in_valid and in_ready) are both high.
//   4. The fabric finalises the {cfg.n_hidden} hidden neurons (bias, ReLU, requantise,
//      saturate) one neuron per cycle and stores them internally.
//   5. It streams those {cfg.n_hidden} hidden activations through the SAME product bank.
//   6. It finalises {cfg.n_out} signed logits one per cycle and tracks argmax.
//   7. done is high for exactly one cycle; prediction_valid is high from that
//      cycle until the next start. logits and prediction hold until then.
//   busy is high whenever an inference is in flight.
//
//   No external timing assumption is made anywhere: every transfer is either
//   handshaked (activations) or driven by the fabric's own explicit counters
//   and FSM state (weights, biases).
//
// ---------------------------------------------------------------------------
// STYLE: synthesizable Verilog-2001 only. One clock, one synchronous reset,
// no latches, no vendor primitives, no attributes, no synthesis pragmas, no
// initial blocks, no delays, no force/release.
// ===========================================================================

`default_nettype none
"""


def _select_module(cfg: FabricConfig, w: dict) -> str:
    pw, ib, k = w["product_bits"], w["index_bits"], cfg.k
    name = cfg.module_name + "_msa_select"
    arms = "\n".join(
        f"            {ib}'d{i}: selected = bank[{i * pw} +: {pw}];"
        for i in range(k))
    return f"""
// ---------------------------------------------------------------------------
// {name}
//
// One neuron's {k}:1 selector.  Every instance reads the SAME shared product
// bank, which is what makes this Multiply-Select-Add rather than one
// multiplier per synapse.  Purely combinational, fully specified (no latch).
// ---------------------------------------------------------------------------
module {name} (
    input  wire [{ib - 1}:0]  index,
    input  wire [{k * pw - 1}:0] bank,
    output reg  [{pw - 1}:0]  selected
);
    always @(*) begin
        case (index)
{arms}
            default: selected = {{{pw}{{1'b0}}}};
        endcase
    end
endmodule
"""


def _sext(src: str, from_bits: int, to_bits: int) -> str:
    pad = to_bits - from_bits
    if pad == 0:
        return src
    return "{{%d{%s[%d]}}, %s}" % (pad, src, from_bits - 1, src)


def _fabric_module(cfg: FabricConfig, w: dict) -> str:
    pw = w["product_bits"]
    ib = w["index_bits"]
    aw = w["act_bits"]
    a1 = w["layer1_acc_bits"]
    a2 = w["layer2_acc_bits"]
    bdw = w["bias_data_bits"]
    ww = w["weight_word_bits"]
    waw = w["weight_addr_bits"]
    baw = w["bias_addr_bits"]
    predw = w["prediction_bits"]
    logw = w["logits_bits"]
    shift = w["requant_shift"]
    rnd = w["round_const"]
    amax = w["act_max"]
    k = cfg.k
    sel_mod = cfg.module_name + "_msa_select"

    # index widths for the internal register files
    hsel = max(1, (cfg.n_hidden - 1).bit_length())
    osel = max(1, (cfg.n_out - 1).bit_length())

    alphas = "\n".join(
        f"    localparam signed [{pw - 1}:0] ALPHA_{i:02d} = "
        f"{'-' if int(a) < 0 else ' '}{pw}'sd{abs(int(a))};"
        f"{'':<2}// weight index {i} -> {int(a):+d}"
        for i, a in enumerate(cfg.alphabet))

    prods = "\n".join(
        f"    wire signed [{pw - 1}:0] prod_{i:02d} = "
        f"$signed({{{pw - aw}'b{'0' * (pw - aw)}, act_pipe}}) * ALPHA_{i:02d};"
        for i in range(k))

    bank_cat = ", ".join(f"prod_{i:02d}" for i in range(k - 1, -1, -1))

    return f"""
// ---------------------------------------------------------------------------
// {cfg.module_name} -- the fixed compute fabric
// ---------------------------------------------------------------------------
module {cfg.module_name} (
    input  wire                 clk,
    input  wire                 rst,               // synchronous, active high
    input  wire                 start,

    // activation input stream (layer-1 inputs, index order 0..{cfg.n_in - 1})
    output wire                 in_ready,
    input  wire                 in_valid,
    input  wire [{aw - 1}:0]          in_data,

    // weight-index memory port (synchronous read, 1 cycle latency)
    output wire                 wmem_en,
    output wire                 wmem_layer,        // 0 = layer 1, 1 = layer 2
    output wire [{waw - 1}:0]          wmem_addr,
    input  wire [{ww - 1}:0]         wmem_data,

    // bias memory port (synchronous read, 1 cycle latency)
    output wire                 bmem_en,
    output wire                 bmem_layer,
    output wire [{baw - 1}:0]           bmem_addr,
    input  wire [{bdw - 1}:0]          bmem_data,

    // results
    output wire                 busy,
    output wire                 done,
    output wire                 prediction_valid,
    output wire [{predw - 1}:0]           prediction,
    output wire [{logw - 1}:0]         logits
);

    // -----------------------------------------------------------------------
    // topology / arithmetic constants (architecture level, no trained value)
    // -----------------------------------------------------------------------
    localparam N_IN        = {cfg.n_in};
    localparam N_HID       = {cfg.n_hidden};
    localparam N_OUT       = {cfg.n_out};
    localparam K           = {k};
    localparam ACT_BITS    = {aw};
    localparam IDX_BITS    = {ib};
    localparam PROD_BITS   = {pw};
    localparam ACC1_BITS   = {a1};
    localparam ACC2_BITS   = {a2};
    localparam RQ_SHIFT    = {shift};
    localparam RQ_ROUND    = {rnd};
    localparam ACT_MAX     = {amax};

    // the fixed weight alphabet
{alphas}

    // -----------------------------------------------------------------------
    // FSM states
    // -----------------------------------------------------------------------
    localparam [3:0] S_IDLE         = 4'd0,
                     S_L1_STREAM    = 4'd1,
                     S_L1_DRAIN     = 4'd2,
                     S_L1_FIN       = 4'd3,
                     S_L1_FIN_DRAIN = 4'd4,
                     S_L2_STREAM    = 4'd5,
                     S_L2_DRAIN     = 4'd6,
                     S_L2_FIN       = 4'd7,
                     S_L2_FIN_DRAIN = 4'd8,
                     S_DONE         = 4'd9;

    reg [3:0]              state;
    reg [{waw - 1}:0]             in_cnt;       // current input-feature index
    reg [{baw - 1}:0]              fin_cnt;      // finalisation issue index
    reg [{baw - 1}:0]              fin_idx;      // finalisation index, stage B
    reg                    mac_valid;    // stage-B multiply-select-add valid
    reg                    fin_valid;    // stage-B finalisation valid
    reg                    layer_r;      // 0 = layer 1, 1 = layer 2
    reg                    clr_acc;
    reg [{aw - 1}:0]              act_pipe;     // the CURRENT activation x

    reg [{aw - 1}:0]              hidden [0:N_HID-1];
    reg signed [ACC1_BITS-1:0] acc1 [0:N_HID-1];
    reg signed [ACC2_BITS-1:0] acc2 [0:N_OUT-1];
    reg signed [ACC2_BITS-1:0] logit_reg [0:N_OUT-1];
    reg signed [ACC2_BITS-1:0] best_logit;
    reg [{predw - 1}:0]              best_idx;
    reg                    have_best;
    reg                    pvalid_r;

    // separate loop variables: one procedural block per variable, so no net
    // ends up with more than one driver
    integer ia1;
    integer ia2;
    integer ic;

    // -----------------------------------------------------------------------
    // SHARED PRODUCT BANK -- exactly K = {k} product generators in the design.
    //
    // act_pipe is unsigned; it is zero extended to PROD_BITS and explicitly
    // made signed, and each alphabet level is a signed PROD_BITS constant, so
    // the multiply is unambiguously a signed multiply.  Every product is
    // exactly representable in PROD_BITS ([{w['product_min']}, {w['product_max']}]), so the
    // assignment truncation is value preserving and no wraparound is possible.
    // -----------------------------------------------------------------------
{prods}

    wire [K*PROD_BITS-1:0] prod_bank = {{{bank_cat}}};

    // -----------------------------------------------------------------------
    // Layer-1 selectors: N_HID instances, all reading the SAME prod_bank
    // -----------------------------------------------------------------------
    wire signed [ACC1_BITS-1:0] l1_sel_ext [0:N_HID-1];

    genvar gj;
    generate
        for (gj = 0; gj < N_HID; gj = gj + 1) begin : L1_SELECT
            wire [PROD_BITS-1:0] p;
            {sel_mod} u_sel (
                .index    (wmem_data[gj*IDX_BITS +: IDX_BITS]),
                .bank     (prod_bank),
                .selected (p)
            );
            assign l1_sel_ext[gj] =
                {{{{(ACC1_BITS-PROD_BITS){{p[PROD_BITS-1]}}}}, p}};
        end
    endgenerate

    // -----------------------------------------------------------------------
    // Layer-2 selectors: N_OUT instances, same shared prod_bank
    // -----------------------------------------------------------------------
    wire signed [ACC2_BITS-1:0] l2_sel_ext [0:N_OUT-1];

    generate
        for (gj = 0; gj < N_OUT; gj = gj + 1) begin : L2_SELECT
            wire [PROD_BITS-1:0] p;
            {sel_mod} u_sel (
                .index    (wmem_data[gj*IDX_BITS +: IDX_BITS]),
                .bank     (prod_bank),
                .selected (p)
            );
            assign l2_sel_ext[gj] =
                {{{{(ACC2_BITS-PROD_BITS){{p[PROD_BITS-1]}}}}, p}};
        end
    endgenerate

    // -----------------------------------------------------------------------
    // Accumulators.  acc1/acc2 hold the running DOT PRODUCT only; the bias is
    // added in the finalisation datapath, exactly as the Stage-0 contract
    // describes.
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            for (ia1 = 0; ia1 < N_HID; ia1 = ia1 + 1)
                acc1[ia1] <= {{ACC1_BITS{{1'b0}}}};
        end else if (clr_acc) begin
            for (ia1 = 0; ia1 < N_HID; ia1 = ia1 + 1)
                acc1[ia1] <= {{ACC1_BITS{{1'b0}}}};
        end else if (mac_valid && (layer_r == 1'b0)) begin
            for (ia1 = 0; ia1 < N_HID; ia1 = ia1 + 1)
                acc1[ia1] <= acc1[ia1] + l1_sel_ext[ia1];
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            for (ia2 = 0; ia2 < N_OUT; ia2 = ia2 + 1)
                acc2[ia2] <= {{ACC2_BITS{{1'b0}}}};
        end else if (clr_acc) begin
            for (ia2 = 0; ia2 < N_OUT; ia2 = ia2 + 1)
                acc2[ia2] <= {{ACC2_BITS{{1'b0}}}};
        end else if (mac_valid && (layer_r == 1'b1)) begin
            for (ia2 = 0; ia2 < N_OUT; ia2 = ia2 + 1)
                acc2[ia2] <= acc2[ia2] + l2_sel_ext[ia2];
        end
    end

    // -----------------------------------------------------------------------
    // Finalisation datapath (combinational).
    //
    // Layer 1: bias, ReLU, round half up, shift right, saturate to uint8.
    // ReLU is applied to the SIGNED accumulator BEFORE the shift, so the
    // shifted operand is provably non-negative.  It is therefore carried in an
    // unsigned {a1 + 1}-bit temporary: one bit wider than the architectural
    // accumulator purely to hold the sign-free value plus the rounding
    // constant, which removes every signed/unsigned shift ambiguity.  The
    // architectural accumulator itself stays signed {a1}-bit.
    // -----------------------------------------------------------------------
    wire signed [ACC1_BITS-1:0] l1_acc  = acc1[fin_idx[{hsel - 1}:0]];
    wire signed [ACC1_BITS-1:0] l1_bias =
        $signed({_sext('bmem_data', bdw, a1) if a1 > bdw else f'bmem_data[{a1 - 1}:0]'});
    wire signed [ACC1_BITS-1:0] l1_accb = l1_acc + l1_bias;

    wire [ACC1_BITS:0] l1_relu  = l1_accb[ACC1_BITS-1] ? {{(ACC1_BITS+1){{1'b0}}}}
                                                       : {{1'b0, l1_accb}};
    wire [ACC1_BITS:0] l1_round = l1_relu + RQ_ROUND;
    wire [ACC1_BITS:0] l1_shift = l1_round >> RQ_SHIFT;
    wire [ACT_BITS-1:0] hid_next = (l1_shift > ACT_MAX) ? ACT_MAX
                                                        : l1_shift[ACT_BITS-1:0];

    wire signed [ACC2_BITS-1:0] l2_acc  = acc2[fin_idx[{osel - 1}:0]];
    wire signed [ACC2_BITS-1:0] l2_bias =
        $signed({_sext('bmem_data', bdw, a2) if a2 > bdw else f'bmem_data[{a2 - 1}:0]'});
    wire signed [ACC2_BITS-1:0] logit_next = l2_acc + l2_bias;

    // -----------------------------------------------------------------------
    // Control FSM + finalisation writeback + argmax
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            state      <= S_IDLE;
            in_cnt     <= {{{waw}{{1'b0}}}};
            fin_cnt    <= {{{baw}{{1'b0}}}};
            fin_idx    <= {{{baw}{{1'b0}}}};
            mac_valid  <= 1'b0;
            fin_valid  <= 1'b0;
            layer_r    <= 1'b0;
            clr_acc    <= 1'b0;
            act_pipe   <= {{ACT_BITS{{1'b0}}}};
            best_logit <= {{ACC2_BITS{{1'b0}}}};
            best_idx   <= {{{predw}{{1'b0}}}};
            have_best  <= 1'b0;
            pvalid_r   <= 1'b0;
            for (ic = 0; ic < N_HID; ic = ic + 1)
                hidden[ic] <= {{ACT_BITS{{1'b0}}}};
            for (ic = 0; ic < N_OUT; ic = ic + 1)
                logit_reg[ic] <= {{ACC2_BITS{{1'b0}}}};
        end else begin
            mac_valid <= 1'b0;
            fin_valid <= 1'b0;
            clr_acc   <= 1'b0;

            // ---- finalisation stage B ----------------------------------
            if (fin_valid) begin
                if (layer_r == 1'b0) begin
                    hidden[fin_idx[{hsel - 1}:0]] <= hid_next;
                end else begin
                    logit_reg[fin_idx[{osel - 1}:0]] <= logit_next;
                    if ((have_best == 1'b0) || (logit_next > best_logit)) begin
                        best_logit <= logit_next;
                        best_idx   <= fin_idx[{predw - 1}:0];
                        have_best  <= 1'b1;
                    end
                end
            end

            // ---- control ------------------------------------------------
            case (state)
                S_IDLE: begin
                    if (start) begin
                        clr_acc   <= 1'b1;
                        in_cnt    <= {{{waw}{{1'b0}}}};
                        layer_r   <= 1'b0;
                        have_best <= 1'b0;
                        pvalid_r  <= 1'b0;
                        state     <= S_L1_STREAM;
                    end
                end

                S_L1_STREAM: begin
                    if (in_valid) begin
                        act_pipe  <= in_data;
                        mac_valid <= 1'b1;
                        in_cnt    <= in_cnt + 1'b1;
                        if (in_cnt == N_IN - 1)
                            state <= S_L1_DRAIN;
                    end
                end

                S_L1_DRAIN: begin       // last layer-1 MAC retires this cycle
                    fin_cnt <= {{{baw}{{1'b0}}}};
                    state   <= S_L1_FIN;
                end

                S_L1_FIN: begin
                    fin_valid <= 1'b1;
                    fin_idx   <= fin_cnt;
                    fin_cnt   <= fin_cnt + 1'b1;
                    if (fin_cnt == N_HID - 1)
                        state <= S_L1_FIN_DRAIN;
                end

                S_L1_FIN_DRAIN: begin   // last hidden neuron retires this cycle
                    layer_r <= 1'b1;
                    in_cnt  <= {{{waw}{{1'b0}}}};
                    state   <= S_L2_STREAM;
                end

                S_L2_STREAM: begin
                    act_pipe  <= hidden[in_cnt[{hsel - 1}:0]];
                    mac_valid <= 1'b1;
                    in_cnt    <= in_cnt + 1'b1;
                    if (in_cnt == N_HID - 1)
                        state <= S_L2_DRAIN;
                end

                S_L2_DRAIN: begin       // last layer-2 MAC retires this cycle
                    fin_cnt <= {{{baw}{{1'b0}}}};
                    state   <= S_L2_FIN;
                end

                S_L2_FIN: begin
                    fin_valid <= 1'b1;
                    fin_idx   <= fin_cnt;
                    fin_cnt   <= fin_cnt + 1'b1;
                    if (fin_cnt == N_OUT - 1)
                        state <= S_L2_FIN_DRAIN;
                end

                S_L2_FIN_DRAIN: begin   // last logit + argmax retire this cycle
                    pvalid_r <= 1'b1;
                    state    <= S_DONE;
                end

                S_DONE: begin
                    state <= S_IDLE;
                end

                default: begin
                    state <= S_IDLE;
                end
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // Outputs (pure decodes of registered state -- no latches)
    // -----------------------------------------------------------------------
    assign in_ready   = (state == S_L1_STREAM);
    assign wmem_en    = ((state == S_L1_STREAM) && in_valid) ||
                        (state == S_L2_STREAM);
    assign wmem_layer = layer_r;
    assign wmem_addr  = in_cnt;
    assign bmem_en    = (state == S_L1_FIN) || (state == S_L2_FIN);
    assign bmem_layer = layer_r;
    assign bmem_addr  = fin_cnt;
    assign busy       = (state != S_IDLE);
    assign done       = (state == S_DONE);
    assign prediction_valid = pvalid_r;
    assign prediction = best_idx;

    generate
        for (gj = 0; gj < N_OUT; gj = gj + 1) begin : LOGIT_PACK
            assign logits[gj*ACC2_BITS +: ACC2_BITS] = logit_reg[gj];
        end
    endgenerate

endmodule

`default_nettype wire
"""


def emit_fabric_verilog(cfg: FabricConfig) -> str:
    """The whole generated fabric file, as a string."""
    w = derive_widths(cfg)
    return _hdr(cfg, w) + _select_module(cfg, w) + _fabric_module(cfg, w)


def emit_testbench_verilog(cfg: FabricConfig) -> str:
    """TEST-ONLY testbench for the Stage-1 fabric.

    It models the model-parameter memories behaviourally (synchronous read,
    1 cycle latency -- exactly the documented port contract) and drives weight
    words and biases straight from hex files written by Python.  This is not a
    Stage-2 ROM backend and is never synthesized.
    """
    w = derive_widths(cfg)
    m = cfg.module_name
    return f"""// TEST-ONLY testbench for {m}. Never synthesized.
// The model-parameter memories below are a behavioural stand-in for the
// Stage-2 weight/bias ROM: they implement the documented synchronous-read,
// one-cycle-latency port contract and nothing else.
`timescale 1ns/1ps

module tb;
    parameter NIMG  = 4;
    parameter STALL = 0;   // 0 = stream back to back; N = one bubble every N inputs

    localparam N_IN      = {cfg.n_in};
    localparam N_HID     = {cfg.n_hidden};
    localparam N_OUT     = {cfg.n_out};
    localparam ACT_BITS  = {w['act_bits']};
    localparam WW        = {w['weight_word_bits']};
    localparam WAW       = {w['weight_addr_bits']};
    localparam BDW       = {w['bias_data_bits']};
    localparam BAW       = {w['bias_addr_bits']};
    localparam ACC2      = {w['layer2_acc_bits']};
    localparam PREDW     = {w['prediction_bits']};
    localparam LOGW      = {w['logits_bits']};
    localparam TIMEOUT   = 20000;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg                 rst;
    reg                 start;
    reg                 in_valid;
    reg [ACT_BITS-1:0]  in_data;

    wire                in_ready;
    wire                wmem_en, wmem_layer;
    wire [WAW-1:0]      wmem_addr;
    reg  [WW-1:0]       wmem_data;
    wire                bmem_en, bmem_layer;
    wire [BAW-1:0]      bmem_addr;
    reg  [BDW-1:0]      bmem_data;
    wire                busy, done, prediction_valid;
    wire [PREDW-1:0]    prediction;
    wire [LOGW-1:0]     logits;

    {m} dut (
        .clk(clk), .rst(rst), .start(start),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data),
        .busy(busy), .done(done), .prediction_valid(prediction_valid),
        .prediction(prediction), .logits(logits)
    );

    // ---- TEST-ONLY model-parameter memories -------------------------------
    reg [WW-1:0]  w1mem [0:N_IN-1];
    reg [WW-1:0]  w2mem [0:N_HID-1];
    reg [BDW-1:0] b1mem [0:N_HID-1];
    reg [BDW-1:0] b2mem [0:N_OUT-1];
    reg [ACT_BITS-1:0] img [0:NIMG*N_IN-1];

    always @(posedge clk) begin
        if (wmem_en)
            wmem_data <= wmem_layer ? w2mem[wmem_addr] : w1mem[wmem_addr];
        if (bmem_en)
            bmem_data <= bmem_layer ? b2mem[bmem_addr] : b1mem[bmem_addr];
    end

    reg [31:0] cyc;
    always @(posedge clk) cyc <= cyc + 32'd1;

    integer fh_out, fh_hid, fh_acc;
    integer im, q;
    integer errors;

    task run_image;
        input integer index;
        integer base, pix, t0, t1, guard, bubble;
        begin
            base = index * N_IN;

            @(negedge clk);
            start = 1'b1;
            t0    = cyc;
            @(negedge clk);
            start = 1'b0;

            // stream the N_IN activations, honouring in_ready/in_valid.
            // With STALL != 0 the driver deliberately drops in_valid every
            // STALL inputs, which proves the handshake really is a handshake.
            pix    = 0;
            bubble = 0;
            while (pix < N_IN) begin
                if (in_ready && (bubble == 0)) begin
                    in_valid = 1'b1;
                    in_data  = img[base + pix];
                    pix      = pix + 1;
                    if ((STALL != 0) && ((pix % STALL) == 0))
                        bubble = 1;
                    else
                        bubble = 0;
                end else begin
                    in_valid = 1'b0;
                    bubble   = 0;
                end
                @(negedge clk);
            end
            in_valid = 1'b0;

            // snapshot the layer-1 dot products (bias not yet applied)
            guard = 0;
            while (!(bmem_en && (bmem_layer == 1'b0)) && (guard < TIMEOUT)) begin
                @(negedge clk);
                guard = guard + 1;
            end
            $fwrite(fh_acc, "%0d", index);
            for (q = 0; q < N_HID; q = q + 1)
                $fwrite(fh_acc, " %0d", dut.acc1[q]);
            $fdisplay(fh_acc, "");

            guard = 0;
            while (!done && (guard < TIMEOUT)) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) begin
                $display("TIMEOUT waiting for done on image %0d", index);
                errors = errors + 1;
                $fdisplay(fh_out, "%0d TIMEOUT", index);
            end else begin
                t1 = cyc;
                if (prediction_valid !== 1'b1) begin
                    $display("prediction_valid not asserted with done, image %0d",
                             index);
                    errors = errors + 1;
                end
                $fwrite(fh_out, "%0d %0d %0d", index, t1 - t0 + 1, prediction);
                for (q = 0; q < N_OUT; q = q + 1)
                    $fwrite(fh_out, " %0d", $signed(logits[q*ACC2 +: ACC2]));
                $fdisplay(fh_out, "");

                $fwrite(fh_hid, "%0d", index);
                for (q = 0; q < N_HID; q = q + 1)
                    $fwrite(fh_hid, " %0d", dut.hidden[q]);
                $fdisplay(fh_hid, "");
            end
            @(negedge clk);
        end
    endtask

    initial begin
        cyc      = 32'd0;
        errors   = 0;
        rst      = 1'b1;
        start    = 1'b0;
        in_valid = 1'b0;
        in_data  = {{ACT_BITS{{1'b0}}}};
        wmem_data = {{WW{{1'b0}}}};
        bmem_data = {{BDW{{1'b0}}}};

        $readmemh("w1.hex",  w1mem);
        $readmemh("w2.hex",  w2mem);
        $readmemh("b1.hex",  b1mem);
        $readmemh("b2.hex",  b2mem);
        $readmemh("img.hex", img);

        fh_out = $fopen("out.txt", "w");
        fh_hid = $fopen("hidden.txt", "w");
        fh_acc = $fopen("acc1.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        for (im = 0; im < NIMG; im = im + 1)
            run_image(im);

        $fclose(fh_out);
        $fclose(fh_hid);
        $fclose(fh_acc);
        if (errors != 0)
            $display("TB ERRORS: %0d", errors);
        else
            $display("TB OK");
        $finish;
    end
endmodule
"""
