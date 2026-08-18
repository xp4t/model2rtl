// ===========================================================================
// mnist_mlp_fabric.v
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
//   784 inputs -> 32 hidden (ReLU + requantise) -> 10 logits -> argmax
//   K = 16, alphabet[i] = i - 8  =>  [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7]
//
// ARITHMETIC (frozen Stage-0 contract)
//   activation        : unsigned 8-bit, [0, 255], zero point 0
//   weight index      : unsigned 4-bit
//   weight value      : signed 4-bit, from the fixed alphabet
//   product           : signed 12-bit, exact range [-2040, 1785]
//   layer1 dot product: signed 22-bit
//   layer1 bias       : signed 22-bit, accumulator domain
//   layer1 accumulator: signed 23-bit (dot product + bias)
//   layer2 dot product: signed 17-bit
//   layer2 bias       : signed 17-bit, accumulator domain
//   layer2 accumulator: signed 18-bit (dot product + bias)
//   hidden requantise : h = clamp((max(acc,0) + 128) >> 8, 0, 255)
//   rounding          : round-half-up (add 128, then shift right 8)
//   saturation        : clamp to [0, 255]
//   output            : raw signed logits, no requantisation
//   prediction        : argmax, LOWEST index wins on ties (matches numpy.argmax)
//
// ---------------------------------------------------------------------------
// ARCHITECTURE
//
// Exactly K = 16 product generators exist in this design.  For the CURRENT
// activation x they produce the whole product bank
//
//     prod_bank[k] = x * alphabet[k],   k = 0 .. 15
//
// and every output neuron of the currently active layer selects one entry of
// that same bank with its 4-bit weight index.  There is no multiplier per
// synapse.  The bank is reused across input cycles AND across both layers.
//
//     x -> [ 16 shared products ] -> 16:1 selector per neuron -> accumulator per neuron
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
//     weight_index[i][j] = wmem_data[j*4 +: 4]
//     neuron j = 0 occupies the least significant nibble.
//     layer 1 uses bits [127:0]; layer 2 uses bits [39:0].
//     Bits above the active layer's field are ignored by the fabric.
//
//   BIAS INTERFACE: option B, indexed read (chosen over a wide packed port
//     because finalisation is already one neuron per cycle, so an indexed read
//     costs no extra cycles and keeps the port count and the Stage-2 ROM shape
//     small and identical to the weight interface).
//     bmem_addr = output-neuron index j
//     bmem_data = that neuron's signed bias, sign extended to 22 bits.
//     layer 1 biases are 22-bit, layer 2 biases are 17-bit.
//
// ---------------------------------------------------------------------------
// TRANSACTION PROTOCOL
//   1. rst (synchronous, active high) clears all state.
//   2. Pulse start for one cycle while idle. Accumulators are cleared.
//   3. in_ready rises; stream exactly 784 activations, index order 0..783,
//      one per cycle in which (in_valid and in_ready) are both high.
//   4. The fabric finalises the 32 hidden neurons (bias, ReLU, requantise,
//      saturate) one neuron per cycle and stores them internally.
//   5. It streams those 32 hidden activations through the SAME product bank.
//   6. It finalises 10 signed logits one per cycle and tracks argmax.
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

// ---------------------------------------------------------------------------
// mnist_mlp_fabric_msa_select
//
// One neuron's 16:1 selector.  Every instance reads the SAME shared product
// bank, which is what makes this Multiply-Select-Add rather than one
// multiplier per synapse.  Purely combinational, fully specified (no latch).
// ---------------------------------------------------------------------------
module mnist_mlp_fabric_msa_select (
    input  wire [3:0]  index,
    input  wire [191:0] bank,
    output reg  [11:0]  selected
);
    always @(*) begin
        case (index)
            4'd0: selected = bank[0 +: 12];
            4'd1: selected = bank[12 +: 12];
            4'd2: selected = bank[24 +: 12];
            4'd3: selected = bank[36 +: 12];
            4'd4: selected = bank[48 +: 12];
            4'd5: selected = bank[60 +: 12];
            4'd6: selected = bank[72 +: 12];
            4'd7: selected = bank[84 +: 12];
            4'd8: selected = bank[96 +: 12];
            4'd9: selected = bank[108 +: 12];
            4'd10: selected = bank[120 +: 12];
            4'd11: selected = bank[132 +: 12];
            4'd12: selected = bank[144 +: 12];
            4'd13: selected = bank[156 +: 12];
            4'd14: selected = bank[168 +: 12];
            4'd15: selected = bank[180 +: 12];
            default: selected = {12{1'b0}};
        endcase
    end
endmodule

// ---------------------------------------------------------------------------
// mnist_mlp_fabric -- the fixed compute fabric
// ---------------------------------------------------------------------------
module mnist_mlp_fabric (
    input  wire                 clk,
    input  wire                 rst,               // synchronous, active high
    input  wire                 start,

    // activation input stream (layer-1 inputs, index order 0..783)
    output wire                 in_ready,
    input  wire                 in_valid,
    input  wire [7:0]          in_data,

    // weight-index memory port (synchronous read, 1 cycle latency)
    output wire                 wmem_en,
    output wire                 wmem_layer,        // 0 = layer 1, 1 = layer 2
    output wire [9:0]          wmem_addr,
    input  wire [127:0]         wmem_data,

    // bias memory port (synchronous read, 1 cycle latency)
    output wire                 bmem_en,
    output wire                 bmem_layer,
    output wire [5:0]           bmem_addr,
    input  wire [21:0]          bmem_data,

    // results
    output wire                 busy,
    output wire                 done,
    output wire                 prediction_valid,
    output wire [3:0]           prediction,
    output wire [179:0]         logits
);

    // -----------------------------------------------------------------------
    // topology / arithmetic constants (architecture level, no trained value)
    // -----------------------------------------------------------------------
    localparam N_IN        = 784;
    localparam N_HID       = 32;
    localparam N_OUT       = 10;
    localparam K           = 16;
    localparam ACT_BITS    = 8;
    localparam IDX_BITS    = 4;
    localparam PROD_BITS   = 12;
    localparam ACC1_BITS   = 23;
    localparam ACC2_BITS   = 18;
    localparam RQ_SHIFT    = 8;
    localparam RQ_ROUND    = 128;
    localparam ACT_MAX     = 255;

    // the fixed weight alphabet
    localparam signed [11:0] ALPHA_00 = -12'sd8;  // weight index 0 -> -8
    localparam signed [11:0] ALPHA_01 = -12'sd7;  // weight index 1 -> -7
    localparam signed [11:0] ALPHA_02 = -12'sd6;  // weight index 2 -> -6
    localparam signed [11:0] ALPHA_03 = -12'sd5;  // weight index 3 -> -5
    localparam signed [11:0] ALPHA_04 = -12'sd4;  // weight index 4 -> -4
    localparam signed [11:0] ALPHA_05 = -12'sd3;  // weight index 5 -> -3
    localparam signed [11:0] ALPHA_06 = -12'sd2;  // weight index 6 -> -2
    localparam signed [11:0] ALPHA_07 = -12'sd1;  // weight index 7 -> -1
    localparam signed [11:0] ALPHA_08 =  12'sd0;  // weight index 8 -> +0
    localparam signed [11:0] ALPHA_09 =  12'sd1;  // weight index 9 -> +1
    localparam signed [11:0] ALPHA_10 =  12'sd2;  // weight index 10 -> +2
    localparam signed [11:0] ALPHA_11 =  12'sd3;  // weight index 11 -> +3
    localparam signed [11:0] ALPHA_12 =  12'sd4;  // weight index 12 -> +4
    localparam signed [11:0] ALPHA_13 =  12'sd5;  // weight index 13 -> +5
    localparam signed [11:0] ALPHA_14 =  12'sd6;  // weight index 14 -> +6
    localparam signed [11:0] ALPHA_15 =  12'sd7;  // weight index 15 -> +7

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
    reg [9:0]             in_cnt;       // current input-feature index
    reg [5:0]              fin_cnt;      // finalisation issue index
    reg [5:0]              fin_idx;      // finalisation index, stage B
    reg                    mac_valid;    // stage-B multiply-select-add valid
    reg                    fin_valid;    // stage-B finalisation valid
    reg                    layer_r;      // 0 = layer 1, 1 = layer 2
    reg                    clr_acc;
    reg [7:0]              act_pipe;     // the CURRENT activation x

    reg [7:0]              hidden [0:N_HID-1];
    reg signed [ACC1_BITS-1:0] acc1 [0:N_HID-1];
    reg signed [ACC2_BITS-1:0] acc2 [0:N_OUT-1];
    reg signed [ACC2_BITS-1:0] logit_reg [0:N_OUT-1];
    reg signed [ACC2_BITS-1:0] best_logit;
    reg [3:0]              best_idx;
    reg                    have_best;
    reg                    pvalid_r;

    // separate loop variables: one procedural block per variable, so no net
    // ends up with more than one driver
    integer ia1;
    integer ia2;
    integer ic;

    // -----------------------------------------------------------------------
    // SHARED PRODUCT BANK -- exactly K = 16 product generators in the design.
    //
    // act_pipe is unsigned; it is zero extended to PROD_BITS and explicitly
    // made signed, and each alphabet level is a signed PROD_BITS constant, so
    // the multiply is unambiguously a signed multiply.  Every product is
    // exactly representable in PROD_BITS ([-2040, 1785]), so the
    // assignment truncation is value preserving and no wraparound is possible.
    // -----------------------------------------------------------------------
    wire signed [11:0] prod_00 = $signed({4'b0000, act_pipe}) * ALPHA_00;
    wire signed [11:0] prod_01 = $signed({4'b0000, act_pipe}) * ALPHA_01;
    wire signed [11:0] prod_02 = $signed({4'b0000, act_pipe}) * ALPHA_02;
    wire signed [11:0] prod_03 = $signed({4'b0000, act_pipe}) * ALPHA_03;
    wire signed [11:0] prod_04 = $signed({4'b0000, act_pipe}) * ALPHA_04;
    wire signed [11:0] prod_05 = $signed({4'b0000, act_pipe}) * ALPHA_05;
    wire signed [11:0] prod_06 = $signed({4'b0000, act_pipe}) * ALPHA_06;
    wire signed [11:0] prod_07 = $signed({4'b0000, act_pipe}) * ALPHA_07;
    wire signed [11:0] prod_08 = $signed({4'b0000, act_pipe}) * ALPHA_08;
    wire signed [11:0] prod_09 = $signed({4'b0000, act_pipe}) * ALPHA_09;
    wire signed [11:0] prod_10 = $signed({4'b0000, act_pipe}) * ALPHA_10;
    wire signed [11:0] prod_11 = $signed({4'b0000, act_pipe}) * ALPHA_11;
    wire signed [11:0] prod_12 = $signed({4'b0000, act_pipe}) * ALPHA_12;
    wire signed [11:0] prod_13 = $signed({4'b0000, act_pipe}) * ALPHA_13;
    wire signed [11:0] prod_14 = $signed({4'b0000, act_pipe}) * ALPHA_14;
    wire signed [11:0] prod_15 = $signed({4'b0000, act_pipe}) * ALPHA_15;

    wire [K*PROD_BITS-1:0] prod_bank = {prod_15, prod_14, prod_13, prod_12, prod_11, prod_10, prod_09, prod_08, prod_07, prod_06, prod_05, prod_04, prod_03, prod_02, prod_01, prod_00};

    // -----------------------------------------------------------------------
    // Layer-1 selectors: N_HID instances, all reading the SAME prod_bank
    // -----------------------------------------------------------------------
    wire signed [ACC1_BITS-1:0] l1_sel_ext [0:N_HID-1];

    genvar gj;
    generate
        for (gj = 0; gj < N_HID; gj = gj + 1) begin : L1_SELECT
            wire [PROD_BITS-1:0] p;
            mnist_mlp_fabric_msa_select u_sel (
                .index    (wmem_data[gj*IDX_BITS +: IDX_BITS]),
                .bank     (prod_bank),
                .selected (p)
            );
            assign l1_sel_ext[gj] =
                {{(ACC1_BITS-PROD_BITS){p[PROD_BITS-1]}}, p};
        end
    endgenerate

    // -----------------------------------------------------------------------
    // Layer-2 selectors: N_OUT instances, same shared prod_bank
    // -----------------------------------------------------------------------
    wire signed [ACC2_BITS-1:0] l2_sel_ext [0:N_OUT-1];

    generate
        for (gj = 0; gj < N_OUT; gj = gj + 1) begin : L2_SELECT
            wire [PROD_BITS-1:0] p;
            mnist_mlp_fabric_msa_select u_sel (
                .index    (wmem_data[gj*IDX_BITS +: IDX_BITS]),
                .bank     (prod_bank),
                .selected (p)
            );
            assign l2_sel_ext[gj] =
                {{(ACC2_BITS-PROD_BITS){p[PROD_BITS-1]}}, p};
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
                acc1[ia1] <= {ACC1_BITS{1'b0}};
        end else if (clr_acc) begin
            for (ia1 = 0; ia1 < N_HID; ia1 = ia1 + 1)
                acc1[ia1] <= {ACC1_BITS{1'b0}};
        end else if (mac_valid && (layer_r == 1'b0)) begin
            for (ia1 = 0; ia1 < N_HID; ia1 = ia1 + 1)
                acc1[ia1] <= acc1[ia1] + l1_sel_ext[ia1];
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            for (ia2 = 0; ia2 < N_OUT; ia2 = ia2 + 1)
                acc2[ia2] <= {ACC2_BITS{1'b0}};
        end else if (clr_acc) begin
            for (ia2 = 0; ia2 < N_OUT; ia2 = ia2 + 1)
                acc2[ia2] <= {ACC2_BITS{1'b0}};
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
    // unsigned 24-bit temporary: one bit wider than the architectural
    // accumulator purely to hold the sign-free value plus the rounding
    // constant, which removes every signed/unsigned shift ambiguity.  The
    // architectural accumulator itself stays signed 23-bit.
    // -----------------------------------------------------------------------
    wire signed [ACC1_BITS-1:0] l1_acc  = acc1[fin_idx[4:0]];
    wire signed [ACC1_BITS-1:0] l1_bias =
        $signed({{1{bmem_data[21]}}, bmem_data});
    wire signed [ACC1_BITS-1:0] l1_accb = l1_acc + l1_bias;

    wire [ACC1_BITS:0] l1_relu  = l1_accb[ACC1_BITS-1] ? {(ACC1_BITS+1){1'b0}}
                                                       : {1'b0, l1_accb};
    wire [ACC1_BITS:0] l1_round = l1_relu + RQ_ROUND;
    wire [ACC1_BITS:0] l1_shift = l1_round >> RQ_SHIFT;
    wire [ACT_BITS-1:0] hid_next = (l1_shift > ACT_MAX) ? ACT_MAX
                                                        : l1_shift[ACT_BITS-1:0];

    wire signed [ACC2_BITS-1:0] l2_acc  = acc2[fin_idx[3:0]];
    wire signed [ACC2_BITS-1:0] l2_bias =
        $signed(bmem_data[17:0]);
    wire signed [ACC2_BITS-1:0] logit_next = l2_acc + l2_bias;

    // -----------------------------------------------------------------------
    // Control FSM + finalisation writeback + argmax
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            state      <= S_IDLE;
            in_cnt     <= {10{1'b0}};
            fin_cnt    <= {6{1'b0}};
            fin_idx    <= {6{1'b0}};
            mac_valid  <= 1'b0;
            fin_valid  <= 1'b0;
            layer_r    <= 1'b0;
            clr_acc    <= 1'b0;
            act_pipe   <= {ACT_BITS{1'b0}};
            best_logit <= {ACC2_BITS{1'b0}};
            best_idx   <= {4{1'b0}};
            have_best  <= 1'b0;
            pvalid_r   <= 1'b0;
            for (ic = 0; ic < N_HID; ic = ic + 1)
                hidden[ic] <= {ACT_BITS{1'b0}};
            for (ic = 0; ic < N_OUT; ic = ic + 1)
                logit_reg[ic] <= {ACC2_BITS{1'b0}};
        end else begin
            mac_valid <= 1'b0;
            fin_valid <= 1'b0;
            clr_acc   <= 1'b0;

            // ---- finalisation stage B ----------------------------------
            if (fin_valid) begin
                if (layer_r == 1'b0) begin
                    hidden[fin_idx[4:0]] <= hid_next;
                end else begin
                    logit_reg[fin_idx[3:0]] <= logit_next;
                    if ((have_best == 1'b0) || (logit_next > best_logit)) begin
                        best_logit <= logit_next;
                        best_idx   <= fin_idx[3:0];
                        have_best  <= 1'b1;
                    end
                end
            end

            // ---- control ------------------------------------------------
            case (state)
                S_IDLE: begin
                    if (start) begin
                        clr_acc   <= 1'b1;
                        in_cnt    <= {10{1'b0}};
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
                    fin_cnt <= {6{1'b0}};
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
                    in_cnt  <= {10{1'b0}};
                    state   <= S_L2_STREAM;
                end

                S_L2_STREAM: begin
                    act_pipe  <= hidden[in_cnt[4:0]];
                    mac_valid <= 1'b1;
                    in_cnt    <= in_cnt + 1'b1;
                    if (in_cnt == N_HID - 1)
                        state <= S_L2_DRAIN;
                end

                S_L2_DRAIN: begin       // last layer-2 MAC retires this cycle
                    fin_cnt <= {6{1'b0}};
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
