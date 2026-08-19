// ===========================================================================
// mnist_mlp_params_openrom_phys.v -- PHYSICAL OpenROM backend (Stage 5)
//
// GENERATED FILE -- do not edit by hand.
//
// Stage-2 parameter-storage backend for the model2rtl MNIST MLP.
// It presents exactly the memory interface that rtl/mnist_mlp_fabric.v already
// declares; the fabric is unchanged and cannot tell which backend is attached.
//
// TIMING CONTRACT (identical for every Stage-2 backend)
//   Synchronous read, 1 cycle latency, enable gated with hold: an address and layer driven during cycle T are captured on the posedge that ends cycle T; the corresponding data must be presented throughout cycle T+1. When en is low the previously captured data must be held unchanged.
//   Reference model:
//       always @(posedge clk) if (en) data_r <= MEM[{layer, addr}];
//       assign data = data_r;
//
// WEIGHT WORD PACKING
//   weight_index[i][j] = wmem_data[j*4 +: 4]
//   orientation [in_features, out_features] (Stage-0 orientation, not transposed)
//   neuron 0 occupies the least significant nibble
//   layer 1 -> bits [127:0] of wmem_data
//   layer 2 -> bits [39:0] of wmem_data; the unused high bits
//   [127:40] are driven to ZERO and hold no model data.
//
// BIAS
//   layer 1 biases are 22-bit signed and occupy the whole 22-bit bus.
//   layer 2 biases are 17-bit signed and are SIGN EXTENDED to 22 bits,
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
// PHYSICAL ORGANISATION (Stage 5)
//   The installed OpenROM cannot route a 784 x 128 array and cannot
//   express a 22-bit or 17-bit word (word_size is in BYTES). Two
//   approved, exactly reversible physical transformations are used:
//     * weights_l1 is split into 4 parallel banks of 784 x 32 bits;
//       every bank sees the same address and all are read together,
//       so the external read latency is still ONE cycle.
//     * both bias memories are stored as 24-bit SIGN EXTENDED words
//       and truncated back to their logical width here.
//   The logical memories, the bit packing and the fabric interface
//   are unchanged. The canonical Stage-2 images remain authoritative.
//
// OpenROM DATA CONVENTION (proven empirically, Stage 2 and Stage 5)
//   OpenROM stores the input file as a big-endian bit stream, first bit
//   first. Word A of the file lands at addr0 = A. Within a word, the macro
//   drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value,
//   i.e. dout0 is BIT REVERSED with respect to a Verilog [word_bits-1:0]
//   literal. This was proven empirically against a generated SPICE netlist,
//   not assumed.
//
// PHYSICAL MACRO STATUS AT GENERATION TIME
//   weights_l1_b0  physical macro generated (gds, lef, log, lvs.sp, py, sp, v), contents verified 25088/25088 bits
//   weights_l1_b1  physical macro generated (gds, lef, log, lvs.sp, py, sp, v), contents verified 25088/25088 bits
//   weights_l1_b2  physical macro NOT generated: not attempted
//   weights_l1_b3  physical macro NOT generated: not attempted
//   weights_l2     physical macro NOT generated: not attempted
//   bias_l1        physical macro NOT generated: not attempted
//   bias_l2        physical macro NOT generated: not attempted
//
// PHYSICAL IMAGES (model2rtl-phys-image-v1)
//   weights_l1_b0   784 x  32  <- weights_l1  [31:0]  sha256 53ac6dd7e7011873f8648240e1202e34fdc824c0db85e97f2408b955e157f8d0
//   weights_l1_b1   784 x  32  <- weights_l1  [63:32]  sha256 9fcbdaed9ac116404d64602cc82bf1b8ca4074b1851fe2c7e7c9d959d7a537a3
//   weights_l1_b2   784 x  32  <- weights_l1  [95:64]  sha256 b676a3b5f89cb4f054730f059b08a7e117ebdff3fc499a789052028fd2441ece
//   weights_l1_b3   784 x  32  <- weights_l1  [127:96]  sha256 8c38b42b18a653797f39ea846fc8a6fd91ff8e175e4fd5e657a39c6d7b773a2e
//   weights_l2       32 x  40  <- weights_l2  [39:0]  sha256 0f475f7ea7b7dff0fd6f14cf958f157e1239adebeecbb98f7e0357dc2d314a0c
//   bias_l1          32 x  24  <- bias_l1     [21:0]  sha256 bd8e7f6a00b5e5530cf80dd08f5cee1fb1803b956a3412e7f896f39826ada9a3
//   bias_l2          10 x  24  <- bias_l2     [16:0]  sha256 86d4111b7cb6b5d8291d0f99da06f7901c7f0cf66889ed2dbcf28efbfe8ea8b2
// ===========================================================================

`default_nettype none

// ---------------------------------------------------------------------------
// rom_phys_weights_l1_b0
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "weights_l1_b0" (784 words x 32 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/weights_l1_b0/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "weights_l1"
// (784 x 128):
//   bank 0 of 4, logical bits [31:0]
//   physical_row = (logical_row >> 0) & 0xffffffff; all 4 banks share one address and are read in parallel
// Physical image sha256 53ac6dd7e7011873f8648240e1202e34fdc824c0db85e97f2408b955e157f8d0
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_weights_l1_b0 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [9:0]          addr0,
    output reg  [31:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                10'd0: dout0 <= 32'h19a95115;
                10'd1: dout0 <= 32'h159ea116;
                10'd2: dout0 <= 32'hd11d9d55;
                10'd3: dout0 <= 32'h6eaaeae1;
                10'd4: dout0 <= 32'h1612991e;
                10'd5: dout0 <= 32'h69ae95e6;
                10'd6: dout0 <= 32'he655eee9;
                10'd7: dout0 <= 32'h965e161e;
                10'd8: dout0 <= 32'h9e999dde;
                10'd9: dout0 <= 32'h91d95619;
                10'd10: dout0 <= 32'he9599e9a;
                10'd11: dout0 <= 32'he559e191;
                10'd12: dout0 <= 32'he66695ee;
                10'd13: dout0 <= 32'h9e61ee15;
                10'd14: dout0 <= 32'h612ee195;
                10'd15: dout0 <= 32'hd19ae3e1;
                10'd16: dout0 <= 32'h66119651;
                10'd17: dout0 <= 32'h19e69699;
                10'd18: dout0 <= 32'h9de15911;
                10'd19: dout0 <= 32'h9e519e19;
                10'd20: dout0 <= 32'h1ad5e5e9;
                10'd21: dout0 <= 32'h1e9ee519;
                10'd22: dout0 <= 32'h959ce555;
                10'd23: dout0 <= 32'he9e19e51;
                10'd24: dout0 <= 32'h1eae9511;
                10'd25: dout0 <= 32'h3319a951;
                10'd26: dout0 <= 32'he616ee5e;
                10'd27: dout0 <= 32'h11e91995;
                10'd28: dout0 <= 32'h1991d669;
                10'd29: dout0 <= 32'h6651e1ee;
                10'd30: dout0 <= 32'h5eece19e;
                10'd31: dout0 <= 32'h6e1e1659;
                10'd32: dout0 <= 32'hee1ea599;
                10'd33: dout0 <= 32'h1e151199;
                10'd34: dout0 <= 32'h9e6a5ea2;
                10'd35: dout0 <= 32'h1e699ee6;
                10'd36: dout0 <= 32'h9e11dea6;
                10'd37: dout0 <= 32'hee65791a;
                10'd38: dout0 <= 32'hd29e7e16;
                10'd39: dout0 <= 32'ha69b9651;
                10'd40: dout0 <= 32'ha22be9dc;
                10'd41: dout0 <= 32'hcca3d9d6;
                10'd42: dout0 <= 32'h66e1a123;
                10'd43: dout0 <= 32'h9ce72dab;
                10'd44: dout0 <= 32'h14ebada3;
                10'd45: dout0 <= 32'h9a176e95;
                10'd46: dout0 <= 32'hea93791e;
                10'd47: dout0 <= 32'h1ee3d1a6;
                10'd48: dout0 <= 32'h5e1d5ee6;
                10'd49: dout0 <= 32'h1615d1e6;
                10'd50: dout0 <= 32'h11e9dee6;
                10'd51: dout0 <= 32'h3961151e;
                10'd52: dout0 <= 32'h1e1e1599;
                10'd53: dout0 <= 32'h115d6a1e;
                10'd54: dout0 <= 32'h1596d51e;
                10'd55: dout0 <= 32'h916ae1e1;
                10'd56: dout0 <= 32'h19e96915;
                10'd57: dout0 <= 32'heee16e13;
                10'd58: dout0 <= 32'h56e9ee91;
                10'd59: dout0 <= 32'h61d3a51b;
                10'd60: dout0 <= 32'h965f56b5;
                10'd61: dout0 <= 32'h6eee5ee1;
                10'd62: dout0 <= 32'h5e113e66;
                10'd63: dout0 <= 32'h1ce52ed9;
                10'd64: dout0 <= 32'h161de166;
                10'd65: dout0 <= 32'hf26e4d68;
                10'd66: dout0 <= 32'hfc236ea0;
                10'd67: dout0 <= 32'h36a336a0;
                10'd68: dout0 <= 32'hd12191e8;
                10'd69: dout0 <= 32'h16a6c295;
                10'd70: dout0 <= 32'h81269212;
                10'd71: dout0 <= 32'h03695ed6;
                10'd72: dout0 <= 32'h039d5166;
                10'd73: dout0 <= 32'h8d1d3e20;
                10'd74: dout0 <= 32'h4efe5ae4;
                10'd75: dout0 <= 32'h40f3dee0;
                10'd76: dout0 <= 32'he8b5ee14;
                10'd77: dout0 <= 32'hde99e5e4;
                10'd78: dout0 <= 32'h1a911a10;
                10'd79: dout0 <= 32'h661d51a2;
                10'd80: dout0 <= 32'h6ee92556;
                10'd81: dout0 <= 32'h99964e51;
                10'd82: dout0 <= 32'h99e61e15;
                10'd83: dout0 <= 32'h99eee6ed;
                10'd84: dout0 <= 32'he1199e1d;
                10'd85: dout0 <= 32'h6661596a;
                10'd86: dout0 <= 32'h1ed12931;
                10'd87: dout0 <= 32'h961f9191;
                10'd88: dout0 <= 32'he2ed11d6;
                10'd89: dout0 <= 32'h599d992e;
                10'd90: dout0 <= 32'h1ad139cc;
                10'd91: dout0 <= 32'h1469d32c;
                10'd92: dout0 <= 32'h7c69d368;
                10'd93: dout0 <= 32'h76cd59ca;
                10'd94: dout0 <= 32'hb9a56160;
                10'd95: dout0 <= 32'h519dee1c;
                10'd96: dout0 <= 32'h1a3dd66e;
                10'd97: dout0 <= 32'h0ead5e66;
                10'd98: dout0 <= 32'h0d1bda56;
                10'd99: dout0 <= 32'h0d63da11;
                10'd100: dout0 <= 32'h0d131eb1;
                10'd101: dout0 <= 32'h8fd5a65e;
                10'd102: dout0 <= 32'h0dd9d15d;
                10'd103: dout0 <= 32'h615d395c;
                10'd104: dout0 <= 32'h921556ea;
                10'd105: dout0 <= 32'hac5e3664;
                10'd106: dout0 <= 32'h12ecfb94;
                10'd107: dout0 <= 32'hca165346;
                10'd108: dout0 <= 32'h2a5711aa;
                10'd109: dout0 <= 32'hca671913;
                10'd110: dout0 <= 32'h225151ce;
                10'd111: dout0 <= 32'h912e5e66;
                10'd112: dout0 <= 32'h1551d111;
                10'd113: dout0 <= 32'heee19929;
                10'd114: dout0 <= 32'hed1511ae;
                10'd115: dout0 <= 32'hd57fd1ae;
                10'd116: dout0 <= 32'h3a3c9d68;
                10'd117: dout0 <= 32'h59e7c142;
                10'd118: dout0 <= 32'ha96e69e0;
                10'd119: dout0 <= 32'hd56991e8;
                10'd120: dout0 <= 32'hdae75542;
                10'd121: dout0 <= 32'h9667194a;
                10'd122: dout0 <= 32'h291dd1aa;
                10'd123: dout0 <= 32'h5155ee5e;
                10'd124: dout0 <= 32'h29d111ea;
                10'd125: dout0 <= 32'h01ade111;
                10'd126: dout0 <= 32'h09a9736e;
                10'd127: dout0 <= 32'h45d1d55e;
                10'd128: dout0 <= 32'hc99196a5;
                10'd129: dout0 <= 32'h6d919a3e;
                10'd130: dout0 <= 32'h95153e3e;
                10'd131: dout0 <= 32'hd115de6a;
                10'd132: dout0 <= 32'h5d669a11;
                10'd133: dout0 <= 32'h66b21999;
                10'd134: dout0 <= 32'h2e51179d;
                10'd135: dout0 <= 32'h64fc39e8;
                10'd136: dout0 <= 32'ha498b52a;
                10'd137: dout0 <= 32'h827a7111;
                10'd138: dout0 <= 32'h463e91ce;
                10'd139: dout0 <= 32'h2e5e9161;
                10'd140: dout0 <= 32'h1d9e9e99;
                10'd141: dout0 <= 32'he115611e;
                10'd142: dout0 <= 32'h9d599e2e;
                10'd143: dout0 <= 32'hed9b1dd2;
                10'd144: dout0 <= 32'h31e51364;
                10'd145: dout0 <= 32'hb15ac1ad;
                10'd146: dout0 <= 32'hd596cde6;
                10'd147: dout0 <= 32'hd1165511;
                10'd148: dout0 <= 32'hea562a66;
                10'd149: dout0 <= 32'h56366919;
                10'd150: dout0 <= 32'h1195155a;
                10'd151: dout0 <= 32'h5a95e91e;
                10'd152: dout0 <= 32'h269159d9;
                10'd153: dout0 <= 32'h2111119d;
                10'd154: dout0 <= 32'ha9699d95;
                10'd155: dout0 <= 32'h1ae5e11d;
                10'd156: dout0 <= 32'ha99a1e59;
                10'd157: dout0 <= 32'h65995a11;
                10'd158: dout0 <= 32'h1919ea51;
                10'd159: dout0 <= 32'h2d99e656;
                10'd160: dout0 <= 32'h691e3a9e;
                10'd161: dout0 <= 32'he91e5539;
                10'd162: dout0 <= 32'h913e1e99;
                10'd163: dout0 <= 32'hd296931c;
                10'd164: dout0 <= 32'h11ee3542;
                10'd165: dout0 <= 32'h8ab93506;
                10'd166: dout0 <= 32'h2ea1b1ae;
                10'd167: dout0 <= 32'ha22ed166;
                10'd168: dout0 <= 32'h9e19e11a;
                10'd169: dout0 <= 32'h6699e596;
                10'd170: dout0 <= 32'h16de65d5;
                10'd171: dout0 <= 32'h5fa3295e;
                10'd172: dout0 <= 32'h3959e9ee;
                10'd173: dout0 <= 32'hda61191e;
                10'd174: dout0 <= 32'h9d5569a5;
                10'd175: dout0 <= 32'hee1e1696;
                10'd176: dout0 <= 32'h611115ea;
                10'd177: dout0 <= 32'hd91e31ea;
                10'd178: dout0 <= 32'h35de19d5;
                10'd179: dout0 <= 32'h1e5e11e5;
                10'd180: dout0 <= 32'h62911595;
                10'd181: dout0 <= 32'ha59e1193;
                10'd182: dout0 <= 32'h1199e9d5;
                10'd183: dout0 <= 32'heeaa1115;
                10'd184: dout0 <= 32'he9e1e611;
                10'd185: dout0 <= 32'h1e19acd3;
                10'd186: dout0 <= 32'he515a6e9;
                10'd187: dout0 <= 32'h5ee11e91;
                10'd188: dout0 <= 32'h9d1e9ad9;
                10'd189: dout0 <= 32'h69a5aa93;
                10'd190: dout0 <= 32'h1e516166;
                10'd191: dout0 <= 32'h12ee17c9;
                10'd192: dout0 <= 32'h9ce67ec4;
                10'd193: dout0 <= 32'hcdd6f181;
                10'd194: dout0 <= 32'hae59b662;
                10'd195: dout0 <= 32'h6d96dee6;
                10'd196: dout0 <= 32'h16e91191;
                10'd197: dout0 <= 32'hce5d11c5;
                10'd198: dout0 <= 32'h3e91ae5d;
                10'd199: dout0 <= 32'h6da32dd1;
                10'd200: dout0 <= 32'h9d199961;
                10'd201: dout0 <= 32'hc9d556e2;
                10'd202: dout0 <= 32'h41e19e99;
                10'd203: dout0 <= 32'h1e695921;
                10'd204: dout0 <= 32'h21115616;
                10'd205: dout0 <= 32'he15e51e9;
                10'd206: dout0 <= 32'h915e1691;
                10'd207: dout0 <= 32'he9191191;
                10'd208: dout0 <= 32'he6566599;
                10'd209: dout0 <= 32'h61ea9311;
                10'd210: dout0 <= 32'he2a1e99e;
                10'd211: dout0 <= 32'h16e1e911;
                10'd212: dout0 <= 32'hd95d6e11;
                10'd213: dout0 <= 32'h55691e1d;
                10'd214: dout0 <= 32'h1dedcee3;
                10'd215: dout0 <= 32'h5d15695d;
                10'd216: dout0 <= 32'hd555ae65;
                10'd217: dout0 <= 32'hee19a996;
                10'd218: dout0 <= 32'h1ae96e93;
                10'd219: dout0 <= 32'h98e1e12d;
                10'd220: dout0 <= 32'h80111611;
                10'd221: dout0 <= 32'h2c5ad612;
                10'd222: dout0 <= 32'h5656de60;
                10'd223: dout0 <= 32'h6511de61;
                10'd224: dout0 <= 32'h16e5e916;
                10'd225: dout0 <= 32'h5c1e4113;
                10'd226: dout0 <= 32'ha1d91915;
                10'd227: dout0 <= 32'ha599e96b;
                10'd228: dout0 <= 32'h259a23ae;
                10'd229: dout0 <= 32'haed6e451;
                10'd230: dout0 <= 32'h2ee2e2eb;
                10'd231: dout0 <= 32'h2e16eda9;
                10'd232: dout0 <= 32'ha6e515e9;
                10'd233: dout0 <= 32'h6e9ee99e;
                10'd234: dout0 <= 32'he6ee11e9;
                10'd235: dout0 <= 32'hae12111e;
                10'd236: dout0 <= 32'h16151519;
                10'd237: dout0 <= 32'h49a655a9;
                10'd238: dout0 <= 32'h8699a919;
                10'd239: dout0 <= 32'hec6de5d1;
                10'd240: dout0 <= 32'h16e19699;
                10'd241: dout0 <= 32'h5d59e895;
                10'd242: dout0 <= 32'hebd61e1b;
                10'd243: dout0 <= 32'h93e6125a;
                10'd244: dout0 <= 32'h1d1196d9;
                10'd245: dout0 <= 32'h6169565e;
                10'd246: dout0 <= 32'h9a3ea96d;
                10'd247: dout0 <= 32'ha0ea1ead;
                10'd248: dout0 <= 32'ha01a1eea;
                10'd249: dout0 <= 32'h605a7e6a;
                10'd250: dout0 <= 32'h591abd6a;
                10'd251: dout0 <= 32'heeeab9c9;
                10'd252: dout0 <= 32'h96e559e1;
                10'd253: dout0 <= 32'h149e095f;
                10'd254: dout0 <= 32'ha5d6ee69;
                10'd255: dout0 <= 32'h69b1ae1d;
                10'd256: dout0 <= 32'haed1a965;
                10'd257: dout0 <= 32'h1e6eee11;
                10'd258: dout0 <= 32'h2e96e55d;
                10'd259: dout0 <= 32'h66d9e991;
                10'd260: dout0 <= 32'he9665551;
                10'd261: dout0 <= 32'h615e5999;
                10'd262: dout0 <= 32'hee115eda;
                10'd263: dout0 <= 32'h66e216de;
                10'd264: dout0 <= 32'h419e1ae1;
                10'd265: dout0 <= 32'h0a19e511;
                10'd266: dout0 <= 32'hc421eea9;
                10'd267: dout0 <= 32'h56e59699;
                10'd268: dout0 <= 32'hb5599291;
                10'd269: dout0 <= 32'hbbae9ae9;
                10'd270: dout0 <= 32'h339ea6b2;
                10'd271: dout0 <= 32'h9315e99d;
                10'd272: dout0 <= 32'h11961e5e;
                10'd273: dout0 <= 32'h59e61515;
                10'd274: dout0 <= 32'hace55ea9;
                10'd275: dout0 <= 32'h04a9e659;
                10'd276: dout0 <= 32'he0e196e5;
                10'd277: dout0 <= 32'hc496b615;
                10'd278: dout0 <= 32'h9e165689;
                10'd279: dout0 <= 32'hbadd2123;
                10'd280: dout0 <= 32'hd959e111;
                10'd281: dout0 <= 32'he222c51b;
                10'd282: dout0 <= 32'hdc55cd35;
                10'd283: dout0 <= 32'hab7d2151;
                10'd284: dout0 <= 32'h629a11a9;
                10'd285: dout0 <= 32'he266a31a;
                10'd286: dout0 <= 32'haaae5596;
                10'd287: dout0 <= 32'heeee555d;
                10'd288: dout0 <= 32'h915aee96;
                10'd289: dout0 <= 32'h62116a99;
                10'd290: dout0 <= 32'haa5692a2;
                10'd291: dout0 <= 32'h899614e9;
                10'd292: dout0 <= 32'h0e111a99;
                10'd293: dout0 <= 32'h82ee1161;
                10'd294: dout0 <= 32'hae61e5c5;
                10'd295: dout0 <= 32'hf9a65d19;
                10'd296: dout0 <= 32'hb7659e95;
                10'd297: dout0 <= 32'h936eecde;
                10'd298: dout0 <= 32'hb3a69151;
                10'd299: dout0 <= 32'h7d2e911e;
                10'd300: dout0 <= 32'h7965199d;
                10'd301: dout0 <= 32'h989a6165;
                10'd302: dout0 <= 32'h906521ed;
                10'd303: dout0 <= 32'h60ae16e5;
                10'd304: dout0 <= 32'h30e5521c;
                10'd305: dout0 <= 32'h7e5a53ee;
                10'd306: dout0 <= 32'hbedd3ec6;
                10'd307: dout0 <= 32'hf15e251b;
                10'd308: dout0 <= 32'h1ee99995;
                10'd309: dout0 <= 32'h9666aaa5;
                10'd310: dout0 <= 32'h3c610a27;
                10'd311: dout0 <= 32'h95cec945;
                10'd312: dout0 <= 32'hba6aee81;
                10'd313: dout0 <= 32'h5e111e11;
                10'd314: dout0 <= 32'h661e5679;
                10'd315: dout0 <= 32'h1115e91d;
                10'd316: dout0 <= 32'ha1d11ae9;
                10'd317: dout0 <= 32'ha61e1251;
                10'd318: dout0 <= 32'hc919ee99;
                10'd319: dout0 <= 32'ha21de11d;
                10'd320: dout0 <= 32'h66119625;
                10'd321: dout0 <= 32'h1a1db925;
                10'd322: dout0 <= 32'h19eedecf;
                10'd323: dout0 <= 32'hb551d329;
                10'd324: dout0 <= 32'hdbe6de15;
                10'd325: dout0 <= 32'h5b93e65d;
                10'd326: dout0 <= 32'hdde99215;
                10'd327: dout0 <= 32'hd3a15191;
                10'd328: dout0 <= 32'h369e169d;
                10'd329: dout0 <= 32'h706dae55;
                10'd330: dout0 <= 32'h90ae21e7;
                10'd331: dout0 <= 32'hdc996e55;
                10'd332: dout0 <= 32'h11925293;
                10'd333: dout0 <= 32'hb59233e6;
                10'd334: dout0 <= 32'h5358f9e3;
                10'd335: dout0 <= 32'hba5d9963;
                10'd336: dout0 <= 32'he9d111e1;
                10'd337: dout0 <= 32'h3c2621a3;
                10'd338: dout0 <= 32'h3aee0925;
                10'd339: dout0 <= 32'hf58a296d;
                10'd340: dout0 <= 32'h3016111d;
                10'd341: dout0 <= 32'h1aa11113;
                10'd342: dout0 <= 32'hce9d9159;
                10'd343: dout0 <= 32'h1e9eee69;
                10'd344: dout0 <= 32'h5a15eed6;
                10'd345: dout0 <= 32'hd1991519;
                10'd346: dout0 <= 32'h619991e6;
                10'd347: dout0 <= 32'ha5d51ae6;
                10'd348: dout0 <= 32'h5559dae9;
                10'd349: dout0 <= 32'h955139a9;
                10'd350: dout0 <= 32'hd19956c3;
                10'd351: dout0 <= 32'hdd6191a5;
                10'd352: dout0 <= 32'hdd5916c9;
                10'd353: dout0 <= 32'h1be111e1;
                10'd354: dout0 <= 32'h9ee51695;
                10'd355: dout0 <= 32'h5e619959;
                10'd356: dout0 <= 32'hdcbeaa99;
                10'd357: dout0 <= 32'hd0519ee3;
                10'd358: dout0 <= 32'he03dae19;
                10'd359: dout0 <= 32'h1e76e45d;
                10'd360: dout0 <= 32'he5ece195;
                10'd361: dout0 <= 32'h359c2626;
                10'd362: dout0 <= 32'hf362eec7;
                10'd363: dout0 <= 32'hfce52963;
                10'd364: dout0 <= 32'h9e59166e;
                10'd365: dout0 <= 32'h9e99a19d;
                10'd366: dout0 <= 32'hf2ac0a2f;
                10'd367: dout0 <= 32'h792e23a3;
                10'd368: dout0 <= 32'hba556edd;
                10'd369: dout0 <= 32'hd6d961ed;
                10'd370: dout0 <= 32'h1a9369ed;
                10'd371: dout0 <= 32'h5115119e;
                10'd372: dout0 <= 32'h59db92e9;
                10'd373: dout0 <= 32'h11959111;
                10'd374: dout0 <= 32'ha91dd696;
                10'd375: dout0 <= 32'h1e595615;
                10'd376: dout0 <= 32'hd99d3ee6;
                10'd377: dout0 <= 32'h139976a1;
                10'd378: dout0 <= 32'h3d9659c5;
                10'd379: dout0 <= 32'h1316d9c9;
                10'd380: dout0 <= 32'h9556e661;
                10'd381: dout0 <= 32'h9e91aaae;
                10'd382: dout0 <= 32'h99e51e5d;
                10'd383: dout0 <= 32'h661119e5;
                10'd384: dout0 <= 32'h6e115de9;
                10'd385: dout0 <= 32'he4d9651d;
                10'd386: dout0 <= 32'hea5919d9;
                10'd387: dout0 <= 32'h66391999;
                10'd388: dout0 <= 32'ha136eae1;
                10'd389: dout0 <= 32'h5564aa9d;
                10'd390: dout0 <= 32'h9d04a9a1;
                10'd391: dout0 <= 32'h9b65e963;
                10'd392: dout0 <= 32'h9c55d9ee;
                10'd393: dout0 <= 32'hb169e1e5;
                10'd394: dout0 <= 32'h32424d8f;
                10'd395: dout0 <= 32'hf1a1ede9;
                10'd396: dout0 <= 32'h3df126d5;
                10'd397: dout0 <= 32'hddb569e5;
                10'd398: dout0 <= 32'hae331551;
                10'd399: dout0 <= 32'h1159a9dd;
                10'd400: dout0 <= 32'h999561e5;
                10'd401: dout0 <= 32'h1dd16699;
                10'd402: dout0 <= 32'hea9e91ed;
                10'd403: dout0 <= 32'h9e991521;
                10'd404: dout0 <= 32'h5ed119ec;
                10'd405: dout0 <= 32'h11e13a6e;
                10'd406: dout0 <= 32'h551e56a9;
                10'd407: dout0 <= 32'ha159dea9;
                10'd408: dout0 <= 32'h695e9e6e;
                10'd409: dout0 <= 32'h15ee5ae9;
                10'd410: dout0 <= 32'ha15e6e11;
                10'd411: dout0 <= 32'hdee16e19;
                10'd412: dout0 <= 32'he1e12359;
                10'd413: dout0 <= 32'hc5ed6515;
                10'd414: dout0 <= 32'he559e5d6;
                10'd415: dout0 <= 32'h61392e53;
                10'd416: dout0 <= 32'h1ed36e91;
                10'd417: dout0 <= 32'hef212ae9;
                10'd418: dout0 <= 32'heb4dce55;
                10'd419: dout0 <= 32'h9391a195;
                10'd420: dout0 <= 32'h511ed6a1;
                10'd421: dout0 <= 32'h5d3669a5;
                10'd422: dout0 <= 32'h99125502;
                10'd423: dout0 <= 32'h132ce1ee;
                10'd424: dout0 <= 32'hebd36a5e;
                10'd425: dout0 <= 32'h699d2ee1;
                10'd426: dout0 <= 32'heddd61e1;
                10'd427: dout0 <= 32'hb1e9135d;
                10'd428: dout0 <= 32'h9956919d;
                10'd429: dout0 <= 32'hde7a951d;
                10'd430: dout0 <= 32'hd6be1115;
                10'd431: dout0 <= 32'he191d165;
                10'd432: dout0 <= 32'h16de3a1a;
                10'd433: dout0 <= 32'h11119969;
                10'd434: dout0 <= 32'h1d1e3ec1;
                10'd435: dout0 <= 32'h955aeaae;
                10'd436: dout0 <= 32'h55ee92a1;
                10'd437: dout0 <= 32'h1e9ece12;
                10'd438: dout0 <= 32'h1a11e6d9;
                10'd439: dout0 <= 32'h911395d3;
                10'd440: dout0 <= 32'hdd1369dd;
                10'd441: dout0 <= 32'h111d1555;
                10'd442: dout0 <= 32'hade1a155;
                10'd443: dout0 <= 32'h8596e691;
                10'd444: dout0 <= 32'h21d39ee5;
                10'd445: dout0 <= 32'h6d6e929e;
                10'd446: dout0 <= 32'h5f5b6672;
                10'd447: dout0 <= 32'h2fa16619;
                10'd448: dout0 <= 32'h1daa6a15;
                10'd449: dout0 <= 32'h1395ee23;
                10'd450: dout0 <= 32'h97ba11a9;
                10'd451: dout0 <= 32'h6d12d92a;
                10'd452: dout0 <= 32'h95ad6ee6;
                10'd453: dout0 <= 32'hd9239ada;
                10'd454: dout0 <= 32'h662aed11;
                10'd455: dout0 <= 32'h616cc959;
                10'd456: dout0 <= 32'h95ee6591;
                10'd457: dout0 <= 32'hedd2e999;
                10'd458: dout0 <= 32'h6936a921;
                10'd459: dout0 <= 32'h91d616e5;
                10'd460: dout0 <= 32'h513c16ee;
                10'd461: dout0 <= 32'hedda1961;
                10'd462: dout0 <= 32'he11a9ece;
                10'd463: dout0 <= 32'hd1311629;
                10'd464: dout0 <= 32'h9e1e66ed;
                10'd465: dout0 <= 32'h9256e6e6;
                10'd466: dout0 <= 32'hea1d51d9;
                10'd467: dout0 <= 32'h166591a2;
                10'd468: dout0 <= 32'h9e59ebd1;
                10'd469: dout0 <= 32'h9eade1e6;
                10'd470: dout0 <= 32'h4e196e1d;
                10'd471: dout0 <= 32'hab1a1a6e;
                10'd472: dout0 <= 32'h2b951121;
                10'd473: dout0 <= 32'heb025c30;
                10'd474: dout0 <= 32'h1f8625ba;
                10'd475: dout0 <= 32'h76ebe652;
                10'd476: dout0 <= 32'ha1965d9e;
                10'd477: dout0 <= 32'h15115e65;
                10'd478: dout0 <= 32'h6f729a1c;
                10'd479: dout0 <= 32'he56339aa;
                10'd480: dout0 <= 32'h9e091a62;
                10'd481: dout0 <= 32'h1c039e51;
                10'd482: dout0 <= 32'h692e969a;
                10'd483: dout0 <= 32'ha1469115;
                10'd484: dout0 <= 32'h1d069dde;
                10'd485: dout0 <= 32'h1182ee5e;
                10'd486: dout0 <= 32'h1922e696;
                10'd487: dout0 <= 32'h5e6e169e;
                10'd488: dout0 <= 32'h1192111e;
                10'd489: dout0 <= 32'hdda4d593;
                10'd490: dout0 <= 32'haee2a125;
                10'd491: dout0 <= 32'h6e5a619e;
                10'd492: dout0 <= 32'h9e61e111;
                10'd493: dout0 <= 32'he9e35dd1;
                10'd494: dout0 <= 32'h15969d5e;
                10'd495: dout0 <= 32'h5ee39d96;
                10'd496: dout0 <= 32'hd62115ea;
                10'd497: dout0 <= 32'h95e19559;
                10'd498: dout0 <= 32'h69e19966;
                10'd499: dout0 <= 32'ha996156d;
                10'd500: dout0 <= 32'h39666e11;
                10'd501: dout0 <= 32'hb126cad6;
                10'd502: dout0 <= 32'hfd2e2539;
                10'd503: dout0 <= 32'hd66529b1;
                10'd504: dout0 <= 32'hbae529eb;
                10'd505: dout0 <= 32'h31959ee1;
                10'd506: dout0 <= 32'h177665a7;
                10'd507: dout0 <= 32'h6ba17198;
                10'd508: dout0 <= 32'h650e11e1;
                10'd509: dout0 <= 32'h410eda21;
                10'd510: dout0 <= 32'h2905319c;
                10'd511: dout0 <= 32'h69893596;
                10'd512: dout0 <= 32'h3d0ed536;
                10'd513: dout0 <= 32'h5e0e1d9e;
                10'd514: dout0 <= 32'hd102a556;
                10'd515: dout0 <= 32'hde0215da;
                10'd516: dout0 <= 32'h7982e6e1;
                10'd517: dout0 <= 32'h358691c9;
                10'd518: dout0 <= 32'he1a15561;
                10'd519: dout0 <= 32'h11e1d5d2;
                10'd520: dout0 <= 32'hee951d3e;
                10'd521: dout0 <= 32'he511d131;
                10'd522: dout0 <= 32'h59e1e9b1;
                10'd523: dout0 <= 32'h95da1e3e;
                10'd524: dout0 <= 32'h411195e6;
                10'd525: dout0 <= 32'h85d1655e;
                10'd526: dout0 <= 32'h65151919;
                10'd527: dout0 <= 32'h293a67e6;
                10'd528: dout0 <= 32'h15e26d9a;
                10'd529: dout0 <= 32'h39642c5e;
                10'd530: dout0 <= 32'h7e6a86c3;
                10'd531: dout0 <= 32'h9de1c6cc;
                10'd532: dout0 <= 32'h915eed9e;
                10'd533: dout0 <= 32'he193155a;
                10'd534: dout0 <= 32'h3ad1a191;
                10'd535: dout0 <= 32'hbb1dd990;
                10'd536: dout0 <= 32'hc36e91e6;
                10'd537: dout0 <= 32'hce253e9a;
                10'd538: dout0 <= 32'h25835a1e;
                10'd539: dout0 <= 32'h15899912;
                10'd540: dout0 <= 32'hd10e659e;
                10'd541: dout0 <= 32'h5909ed96;
                10'd542: dout0 <= 32'hde0de93e;
                10'd543: dout0 <= 32'hf6011152;
                10'd544: dout0 <= 32'hb60be59e;
                10'd545: dout0 <= 32'h5e451eee;
                10'd546: dout0 <= 32'hcd631995;
                10'd547: dout0 <= 32'haa199e96;
                10'd548: dout0 <= 32'h69e65ed1;
                10'd549: dout0 <= 32'he1199251;
                10'd550: dout0 <= 32'h1121d29a;
                10'd551: dout0 <= 32'h11191a55;
                10'd552: dout0 <= 32'hc6ea15d6;
                10'd553: dout0 <= 32'h05ea5961;
                10'd554: dout0 <= 32'h29e965de;
                10'd555: dout0 <= 32'h691d535e;
                10'd556: dout0 <= 32'h5e166d15;
                10'd557: dout0 <= 32'h95d212e5;
                10'd558: dout0 <= 32'h17e26e86;
                10'd559: dout0 <= 32'h95116961;
                10'd560: dout0 <= 32'hdea1516e;
                10'd561: dout0 <= 32'h22599e36;
                10'd562: dout0 <= 32'h165611d8;
                10'd563: dout0 <= 32'habd59994;
                10'd564: dout0 <= 32'h25e5d69a;
                10'd565: dout0 <= 32'he9c17ab1;
                10'd566: dout0 <= 32'ha68e9ed6;
                10'd567: dout0 <= 32'h66e9d19e;
                10'd568: dout0 <= 32'h2ea55b91;
                10'd569: dout0 <= 32'he12d599e;
                10'd570: dout0 <= 32'h16cb191a;
                10'd571: dout0 <= 32'hdacb9651;
                10'd572: dout0 <= 32'h9cafe9da;
                10'd573: dout0 <= 32'h16e79e15;
                10'd574: dout0 <= 32'haed711d9;
                10'd575: dout0 <= 32'hae95de15;
                10'd576: dout0 <= 32'he5d51a36;
                10'd577: dout0 <= 32'h2639d29e;
                10'd578: dout0 <= 32'he9999a51;
                10'd579: dout0 <= 32'h21129e59;
                10'd580: dout0 <= 32'h29115111;
                10'd581: dout0 <= 32'h8de65516;
                10'd582: dout0 <= 32'h6939dde6;
                10'd583: dout0 <= 32'h69939b59;
                10'd584: dout0 <= 32'h55e565dd;
                10'd585: dout0 <= 32'h3132a11e;
                10'd586: dout0 <= 32'h9391ca61;
                10'd587: dout0 <= 32'h9199e919;
                10'd588: dout0 <= 32'h99ee1969;
                10'd589: dout0 <= 32'h15111e1e;
                10'd590: dout0 <= 32'ha7b161da;
                10'd591: dout0 <= 32'h8d3919d6;
                10'd592: dout0 <= 32'ha1f69616;
                10'd593: dout0 <= 32'h695e913d;
                10'd594: dout0 <= 32'h15965e5e;
                10'd595: dout0 <= 32'h26599a15;
                10'd596: dout0 <= 32'he19d9c96;
                10'd597: dout0 <= 32'h1ae95e15;
                10'd598: dout0 <= 32'h5e5d6111;
                10'd599: dout0 <= 32'head39a9a;
                10'd600: dout0 <= 32'h96d3929d;
                10'd601: dout0 <= 32'h6659541e;
                10'd602: dout0 <= 32'h69955c95;
                10'd603: dout0 <= 32'h2911d651;
                10'd604: dout0 <= 32'hae295259;
                10'd605: dout0 <= 32'ha156d41e;
                10'd606: dout0 <= 32'h2d96149c;
                10'd607: dout0 <= 32'h6991e25e;
                10'd608: dout0 <= 32'h851a5616;
                10'd609: dout0 <= 32'he9195556;
                10'd610: dout0 <= 32'he5a9535c;
                10'd611: dout0 <= 32'hd5e1b79a;
                10'd612: dout0 <= 32'h5ee6a3d5;
                10'd613: dout0 <= 32'h1190e119;
                10'd614: dout0 <= 32'hfcefe1a6;
                10'd615: dout0 <= 32'h969aa691;
                10'd616: dout0 <= 32'h9195eee3;
                10'd617: dout0 <= 32'h959e99a5;
                10'd618: dout0 <= 32'h13b55e9c;
                10'd619: dout0 <= 32'h4b9e5e92;
                10'd620: dout0 <= 32'h1ab21ea9;
                10'd621: dout0 <= 32'h5152a1d1;
                10'd622: dout0 <= 32'h955e1453;
                10'd623: dout0 <= 32'h5e9a1cee;
                10'd624: dout0 <= 32'h9e512ee1;
                10'd625: dout0 <= 32'he19966d1;
                10'd626: dout0 <= 32'h9639961e;
                10'd627: dout0 <= 32'ha159149e;
                10'd628: dout0 <= 32'h6e519695;
                10'd629: dout0 <= 32'h9e59ecd6;
                10'd630: dout0 <= 32'h665ee559;
                10'd631: dout0 <= 32'hc9191159;
                10'd632: dout0 <= 32'haee6ee1e;
                10'd633: dout0 <= 32'hede59cde;
                10'd634: dout0 <= 32'h2eeae2ee;
                10'd635: dout0 <= 32'ha9169e5e;
                10'd636: dout0 <= 32'h2111d216;
                10'd637: dout0 <= 32'h1999e951;
                10'd638: dout0 <= 32'h91119d56;
                10'd639: dout0 <= 32'h61e95356;
                10'd640: dout0 <= 32'ha96cd7d9;
                10'd641: dout0 <= 32'h9662e599;
                10'd642: dout0 <= 32'hb29f592a;
                10'd643: dout0 <= 32'h15e119a1;
                10'd644: dout0 <= 32'h51116195;
                10'd645: dout0 <= 32'h5955e113;
                10'd646: dout0 <= 32'h27337aa2;
                10'd647: dout0 <= 32'hcb39b698;
                10'd648: dout0 <= 32'he2fab522;
                10'd649: dout0 <= 32'h961159e9;
                10'd650: dout0 <= 32'h31d619e1;
                10'd651: dout0 <= 32'hde9961d9;
                10'd652: dout0 <= 32'h55519e91;
                10'd653: dout0 <= 32'h9611ee91;
                10'd654: dout0 <= 32'h91d5ea69;
                10'd655: dout0 <= 32'h515d9ee6;
                10'd656: dout0 <= 32'h565512d5;
                10'd657: dout0 <= 32'hd15e6ce1;
                10'd658: dout0 <= 32'ha69191d9;
                10'd659: dout0 <= 32'h2e1d1195;
                10'd660: dout0 <= 32'h4191565e;
                10'd661: dout0 <= 32'h0619ee19;
                10'd662: dout0 <= 32'h292d9916;
                10'd663: dout0 <= 32'h21611266;
                10'd664: dout0 <= 32'hcd629e9a;
                10'd665: dout0 <= 32'h63261692;
                10'd666: dout0 <= 32'h39ea5199;
                10'd667: dout0 <= 32'h191ed3aa;
                10'd668: dout0 <= 32'h76a9ed16;
                10'd669: dout0 <= 32'hdee29d66;
                10'd670: dout0 <= 32'h5b1dd5c6;
                10'd671: dout0 <= 32'he99e1615;
                10'd672: dout0 <= 32'he61995ee;
                10'd673: dout0 <= 32'h6115155d;
                10'd674: dout0 <= 32'h731a65d3;
                10'd675: dout0 <= 32'h51dd55a9;
                10'd676: dout0 <= 32'h65d33e51;
                10'd677: dout0 <= 32'h393e6e53;
                10'd678: dout0 <= 32'h913e19a1;
                10'd679: dout0 <= 32'he13e3ae1;
                10'd680: dout0 <= 32'h51e9d599;
                10'd681: dout0 <= 32'h19565611;
                10'd682: dout0 <= 32'h69593a11;
                10'd683: dout0 <= 32'h1192e6ee;
                10'd684: dout0 <= 32'h91565ad1;
                10'd685: dout0 <= 32'h5196996d;
                10'd686: dout0 <= 32'h56d1de1a;
                10'd687: dout0 <= 32'h6e559a99;
                10'd688: dout0 <= 32'h066939e1;
                10'd689: dout0 <= 32'h091b9256;
                10'd690: dout0 <= 32'h855a5a1a;
                10'd691: dout0 <= 32'h81e4169e;
                10'd692: dout0 <= 32'h899c11e9;
                10'd693: dout0 <= 32'h539456ae;
                10'd694: dout0 <= 32'h593ade32;
                10'd695: dout0 <= 32'h61d61e71;
                10'd696: dout0 <= 32'h3c5e3914;
                10'd697: dout0 <= 32'he9a15958;
                10'd698: dout0 <= 32'he3916515;
                10'd699: dout0 <= 32'h51596e69;
                10'd700: dout0 <= 32'h1155191e;
                10'd701: dout0 <= 32'he6a51116;
                10'd702: dout0 <= 32'h1d5dded4;
                10'd703: dout0 <= 32'hb2715a31;
                10'd704: dout0 <= 32'hb67d6e5d;
                10'd705: dout0 <= 32'hbdf99e59;
                10'd706: dout0 <= 32'hc1f6d96e;
                10'd707: dout0 <= 32'h6ef69929;
                10'd708: dout0 <= 32'h1ede1265;
                10'd709: dout0 <= 32'haed556ae;
                10'd710: dout0 <= 32'ha53c5e21;
                10'd711: dout0 <= 32'heed299e9;
                10'd712: dout0 <= 32'h115256ae;
                10'd713: dout0 <= 32'h91d49ae1;
                10'd714: dout0 <= 32'h29586aa5;
                10'd715: dout0 <= 32'ha150d5c9;
                10'd716: dout0 <= 32'h89d0e1a1;
                10'd717: dout0 <= 32'hc918e4ee;
                10'd718: dout0 <= 32'h81e0991e;
                10'd719: dout0 <= 32'h66145113;
                10'd720: dout0 <= 32'hae5c9131;
                10'd721: dout0 <= 32'h1a5c1cd9;
                10'd722: dout0 <= 32'h1afeeaea;
                10'd723: dout0 <= 32'hd8fdba1a;
                10'd724: dout0 <= 32'h147e7c99;
                10'd725: dout0 <= 32'h1e5e611e;
                10'd726: dout0 <= 32'h5d1e61e6;
                10'd727: dout0 <= 32'h991e9911;
                10'd728: dout0 <= 32'he11ee5e5;
                10'd729: dout0 <= 32'he16d1115;
                10'd730: dout0 <= 32'ha6e151e6;
                10'd731: dout0 <= 32'h6e9eee1e;
                10'd732: dout0 <= 32'ha59656e1;
                10'd733: dout0 <= 32'h16f29e1e;
                10'd734: dout0 <= 32'hdcfea95e;
                10'd735: dout0 <= 32'h16a4aee3;
                10'd736: dout0 <= 32'h22e0a96d;
                10'd737: dout0 <= 32'h2e166917;
                10'd738: dout0 <= 32'he1d6eaa3;
                10'd739: dout0 <= 32'h31d4954d;
                10'd740: dout0 <= 32'hb1dc9e1d;
                10'd741: dout0 <= 32'h3a2eae33;
                10'd742: dout0 <= 32'h16e9a6e7;
                10'd743: dout0 <= 32'h1e91ee29;
                10'd744: dout0 <= 32'hde6219ed;
                10'd745: dout0 <= 32'h91169e13;
                10'd746: dout0 <= 32'h295a1ee7;
                10'd747: dout0 <= 32'hcad64115;
                10'd748: dout0 <= 32'hce726d53;
                10'd749: dout0 <= 32'h611aeced;
                10'd750: dout0 <= 32'hee5566eb;
                10'd751: dout0 <= 32'he11594dd;
                10'd752: dout0 <= 32'h36e126fd;
                10'd753: dout0 <= 32'h1665515d;
                10'd754: dout0 <= 32'h11919e6a;
                10'd755: dout0 <= 32'h99911951;
                10'd756: dout0 <= 32'h915e9591;
                10'd757: dout0 <= 32'he99ee1e1;
                10'd758: dout0 <= 32'h91596e65;
                10'd759: dout0 <= 32'h99116a1e;
                10'd760: dout0 <= 32'hd915a1e1;
                10'd761: dout0 <= 32'he159e9e9;
                10'd762: dout0 <= 32'h3a62a9e9;
                10'd763: dout0 <= 32'h3c9161e9;
                10'd764: dout0 <= 32'h5c19a91b;
                10'd765: dout0 <= 32'he6c666e3;
                10'd766: dout0 <= 32'hd42ded1f;
                10'd767: dout0 <= 32'h99e165ad;
                10'd768: dout0 <= 32'h6d961e9d;
                10'd769: dout0 <= 32'hd613212f;
                10'd770: dout0 <= 32'hd9e92ec7;
                10'd771: dout0 <= 32'h93deee25;
                10'd772: dout0 <= 32'h3299aaa3;
                10'd773: dout0 <= 32'h1a614627;
                10'd774: dout0 <= 32'hc596e155;
                10'd775: dout0 <= 32'h21656e9f;
                10'd776: dout0 <= 32'h1dee2995;
                10'd777: dout0 <= 32'hd145ca67;
                10'd778: dout0 <= 32'h52292e27;
                10'd779: dout0 <= 32'h9ce9ae47;
                10'd780: dout0 <= 32'ha96e11d9;
                10'd781: dout0 <= 32'h1165e161;
                10'd782: dout0 <= 32'h5e11e66e;
                10'd783: dout0 <= 32'he5e199ee;
                default: dout0 <= {32{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_phys_weights_l1_b1
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "weights_l1_b1" (784 words x 32 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/weights_l1_b1/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "weights_l1"
// (784 x 128):
//   bank 1 of 4, logical bits [63:32]
//   physical_row = (logical_row >> 32) & 0xffffffff; all 4 banks share one address and are read in parallel
// Physical image sha256 9fcbdaed9ac116404d64602cc82bf1b8ca4074b1851fe2c7e7c9d959d7a537a3
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_weights_l1_b1 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [9:0]          addr0,
    output reg  [31:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                10'd0: dout0 <= 32'h11e66951;
                10'd1: dout0 <= 32'h5a1195e5;
                10'd2: dout0 <= 32'h119e656e;
                10'd3: dout0 <= 32'h5e5196e1;
                10'd4: dout0 <= 32'h116925e1;
                10'd5: dout0 <= 32'heee59e96;
                10'd6: dout0 <= 32'h9e6d6e1d;
                10'd7: dout0 <= 32'he6591959;
                10'd8: dout0 <= 32'h91ad6156;
                10'd9: dout0 <= 32'h61e61166;
                10'd10: dout0 <= 32'h696ed919;
                10'd11: dout0 <= 32'h19169e61;
                10'd12: dout0 <= 32'h5a619e9d;
                10'd13: dout0 <= 32'h1e961e69;
                10'd14: dout0 <= 32'h1911e919;
                10'd15: dout0 <= 32'h11659191;
                10'd16: dout0 <= 32'h5ae56e19;
                10'd17: dout0 <= 32'h91da9195;
                10'd18: dout0 <= 32'h1995e21a;
                10'd19: dout0 <= 32'h1156e119;
                10'd20: dout0 <= 32'h1e159221;
                10'd21: dout0 <= 32'h15a9e591;
                10'd22: dout0 <= 32'h99199e1e;
                10'd23: dout0 <= 32'h695ae91e;
                10'd24: dout0 <= 32'h15519eee;
                10'd25: dout0 <= 32'h19919e91;
                10'd26: dout0 <= 32'h991ea599;
                10'd27: dout0 <= 32'h6ee11e5e;
                10'd28: dout0 <= 32'he15ee9e5;
                10'd29: dout0 <= 32'he63a119e;
                10'd30: dout0 <= 32'h59119911;
                10'd31: dout0 <= 32'h99e9e155;
                10'd32: dout0 <= 32'hee19659d;
                10'd33: dout0 <= 32'h16196191;
                10'd34: dout0 <= 32'h2669d59d;
                10'd35: dout0 <= 32'ha1e695a5;
                10'd36: dout0 <= 32'h5926e997;
                10'd37: dout0 <= 32'h1421a2db;
                10'd38: dout0 <= 32'ha225a2df;
                10'd39: dout0 <= 32'ha4caa657;
                10'd40: dout0 <= 32'ha6ae8efb;
                10'd41: dout0 <= 32'h2c6ec2ff;
                10'd42: dout0 <= 32'ha2cbd3ef;
                10'd43: dout0 <= 32'h294257ef;
                10'd44: dout0 <= 32'hce401ec3;
                10'd45: dout0 <= 32'h2aace19d;
                10'd46: dout0 <= 32'h2269e637;
                10'd47: dout0 <= 32'hcaa6aed9;
                10'd48: dout0 <= 32'h62aea613;
                10'd49: dout0 <= 32'h161615dd;
                10'd50: dout0 <= 32'h29eea651;
                10'd51: dout0 <= 32'h1115919e;
                10'd52: dout0 <= 32'hd1695999;
                10'd53: dout0 <= 32'h1991965e;
                10'd54: dout0 <= 32'h1a5e1199;
                10'd55: dout0 <= 32'h6a61999e;
                10'd56: dout0 <= 32'h93e16191;
                10'd57: dout0 <= 32'h1aed5169;
                10'd58: dout0 <= 32'h9ee99199;
                10'd59: dout0 <= 32'hc8e1e666;
                10'd60: dout0 <= 32'ha69daee3;
                10'd61: dout0 <= 32'h5e1ee1e9;
                10'd62: dout0 <= 32'h646e61e5;
                10'd63: dout0 <= 32'hcce6e5f6;
                10'd64: dout0 <= 32'hac119939;
                10'd65: dout0 <= 32'hb6ec3b64;
                10'd66: dout0 <= 32'hd8405f2a;
                10'd67: dout0 <= 32'hd108e3e9;
                10'd68: dout0 <= 32'h1d0c5356;
                10'd69: dout0 <= 32'h692157e9;
                10'd70: dout0 <= 32'hcdcae563;
                10'd71: dout0 <= 32'h550a5bcd;
                10'd72: dout0 <= 32'hed025d67;
                10'd73: dout0 <= 32'h170d99a7;
                10'd74: dout0 <= 32'h67ca9d3f;
                10'd75: dout0 <= 32'hea1b59df;
                10'd76: dout0 <= 32'he59ad579;
                10'd77: dout0 <= 32'h1522d1f9;
                10'd78: dout0 <= 32'h191aa5f3;
                10'd79: dout0 <= 32'h19e091b3;
                10'd80: dout0 <= 32'hd5e69969;
                10'd81: dout0 <= 32'hd9e655ee;
                10'd82: dout0 <= 32'h99169119;
                10'd83: dout0 <= 32'hee96591e;
                10'd84: dout0 <= 32'h9d56e619;
                10'd85: dout0 <= 32'h55a96ebd;
                10'd86: dout0 <= 32'h69ee1ea1;
                10'd87: dout0 <= 32'h6c91e9a9;
                10'd88: dout0 <= 32'h41166e39;
                10'd89: dout0 <= 32'h3161ea9c;
                10'd90: dout0 <= 32'h296e5e1e;
                10'd91: dout0 <= 32'h26216565;
                10'd92: dout0 <= 32'h2e82991e;
                10'd93: dout0 <= 32'h29ac53a9;
                10'd94: dout0 <= 32'ha1243921;
                10'd95: dout0 <= 32'ha508ae5a;
                10'd96: dout0 <= 32'h210cbece;
                10'd97: dout0 <= 32'h1c0a7dad;
                10'd98: dout0 <= 32'hbe0a5e1e;
                10'd99: dout0 <= 32'h5ea213e1;
                10'd100: dout0 <= 32'hd14a59a1;
                10'd101: dout0 <= 32'he1a15119;
                10'd102: dout0 <= 32'hee66de1d;
                10'd103: dout0 <= 32'hee1e919b;
                10'd104: dout0 <= 32'h1d51dad5;
                10'd105: dout0 <= 32'hddda99eb;
                10'd106: dout0 <= 32'h39551593;
                10'd107: dout0 <= 32'h31199eb3;
                10'd108: dout0 <= 32'hf9112e93;
                10'd109: dout0 <= 32'h111b5813;
                10'd110: dout0 <= 32'he1a5e21b;
                10'd111: dout0 <= 32'h1e9119e9;
                10'd112: dout0 <= 32'hae919111;
                10'd113: dout0 <= 32'h65695139;
                10'd114: dout0 <= 32'ha959e69a;
                10'd115: dout0 <= 32'heae6661a;
                10'd116: dout0 <= 32'h616a8656;
                10'd117: dout0 <= 32'h615c77e6;
                10'd118: dout0 <= 32'hcd5e5fa6;
                10'd119: dout0 <= 32'h43a6e3ce;
                10'd120: dout0 <= 32'h8dc49f89;
                10'd121: dout0 <= 32'h81a69da1;
                10'd122: dout0 <= 32'h09c033ae;
                10'd123: dout0 <= 32'h26c83191;
                10'd124: dout0 <= 32'ha56cd5ae;
                10'd125: dout0 <= 32'h69e9951e;
                10'd126: dout0 <= 32'h25aee111;
                10'd127: dout0 <= 32'he1e63e69;
                10'd128: dout0 <= 32'he1a1bd55;
                10'd129: dout0 <= 32'h612519d6;
                10'd130: dout0 <= 32'h9e6eb96d;
                10'd131: dout0 <= 32'hae66ed5e;
                10'd132: dout0 <= 32'ha5a11993;
                10'd133: dout0 <= 32'h5d5aeadb;
                10'd134: dout0 <= 32'h516e6131;
                10'd135: dout0 <= 32'hd359293b;
                10'd136: dout0 <= 32'hdfe9601d;
                10'd137: dout0 <= 32'hed3698e3;
                10'd138: dout0 <= 32'he9ec3a9f;
                10'd139: dout0 <= 32'h69526131;
                10'd140: dout0 <= 32'h91e9a9e6;
                10'd141: dout0 <= 32'h6ded9d11;
                10'd142: dout0 <= 32'h26e35969;
                10'd143: dout0 <= 32'h2cd63da4;
                10'd144: dout0 <= 32'h0ea6e3c0;
                10'd145: dout0 <= 32'h61b6f955;
                10'd146: dout0 <= 32'h15567152;
                10'd147: dout0 <= 32'h1169b51a;
                10'd148: dout0 <= 32'h356cd616;
                10'd149: dout0 <= 32'h1b225116;
                10'd150: dout0 <= 32'ha5241a15;
                10'd151: dout0 <= 32'h61eaeae1;
                10'd152: dout0 <= 32'h2ee65996;
                10'd153: dout0 <= 32'he1e95a1e;
                10'd154: dout0 <= 32'h69655111;
                10'd155: dout0 <= 32'h6111e696;
                10'd156: dout0 <= 32'ha919d5a5;
                10'd157: dout0 <= 32'h69ee6695;
                10'd158: dout0 <= 32'he9e69115;
                10'd159: dout0 <= 32'he1a69d51;
                10'd160: dout0 <= 32'h99611921;
                10'd161: dout0 <= 32'h69ea1513;
                10'd162: dout0 <= 32'h26e2dd29;
                10'd163: dout0 <= 32'h696d13eb;
                10'd164: dout0 <= 32'h996a65f9;
                10'd165: dout0 <= 32'h6eb9326b;
                10'd166: dout0 <= 32'hac522e95;
                10'd167: dout0 <= 32'h665eee59;
                10'd168: dout0 <= 32'h9e991916;
                10'd169: dout0 <= 32'h9652e365;
                10'd170: dout0 <= 32'h59e1d41a;
                10'd171: dout0 <= 32'h517a9da8;
                10'd172: dout0 <= 32'hc9ad616e;
                10'd173: dout0 <= 32'he513ba5e;
                10'd174: dout0 <= 32'h65955391;
                10'd175: dout0 <= 32'h9192565e;
                10'd176: dout0 <= 32'h55d01651;
                10'd177: dout0 <= 32'h3154d299;
                10'd178: dout0 <= 32'h5e16d696;
                10'd179: dout0 <= 32'h3e316e19;
                10'd180: dout0 <= 32'h91e95691;
                10'd181: dout0 <= 32'h66ae996e;
                10'd182: dout0 <= 32'h91931e15;
                10'd183: dout0 <= 32'h6611a6ed;
                10'd184: dout0 <= 32'hda66e955;
                10'd185: dout0 <= 32'h91916115;
                10'd186: dout0 <= 32'h5999a5e5;
                10'd187: dout0 <= 32'h691e151d;
                10'd188: dout0 <= 32'hee6911e9;
                10'd189: dout0 <= 32'h1c59e955;
                10'd190: dout0 <= 32'haa19915b;
                10'd191: dout0 <= 32'he5619653;
                10'd192: dout0 <= 32'ha495eeaf;
                10'd193: dout0 <= 32'h2e3e5e2f;
                10'd194: dout0 <= 32'h62da661f;
                10'd195: dout0 <= 32'he13215ed;
                10'd196: dout0 <= 32'h199e1999;
                10'd197: dout0 <= 32'h36b0fe6a;
                10'd198: dout0 <= 32'h3df6541c;
                10'd199: dout0 <= 32'h535a55ac;
                10'd200: dout0 <= 32'he1e6f36a;
                10'd201: dout0 <= 32'ha35bd2ae;
                10'd202: dout0 <= 32'h55d1e9aa;
                10'd203: dout0 <= 32'hd6e0e6e1;
                10'd204: dout0 <= 32'h9ddca11e;
                10'd205: dout0 <= 32'h9dba9a59;
                10'd206: dout0 <= 32'h1d52e115;
                10'd207: dout0 <= 32'he2916659;
                10'd208: dout0 <= 32'h5995dee9;
                10'd209: dout0 <= 32'hdee91611;
                10'd210: dout0 <= 32'haaed1be3;
                10'd211: dout0 <= 32'h59e96559;
                10'd212: dout0 <= 32'h1de51597;
                10'd213: dout0 <= 32'he99961e5;
                10'd214: dout0 <= 32'h19e69937;
                10'd215: dout0 <= 32'h6559115f;
                10'd216: dout0 <= 32'he2ed5e5b;
                10'd217: dout0 <= 32'he5591d53;
                10'd218: dout0 <= 32'he3e5d99d;
                10'd219: dout0 <= 32'h22e59e95;
                10'd220: dout0 <= 32'h1a111ae3;
                10'd221: dout0 <= 32'h611ae623;
                10'd222: dout0 <= 32'he1393eef;
                10'd223: dout0 <= 32'h91fccdd5;
                10'd224: dout0 <= 32'he961165e;
                10'd225: dout0 <= 32'hbe787861;
                10'd226: dout0 <= 32'h59e63c32;
                10'd227: dout0 <= 32'had91b16a;
                10'd228: dout0 <= 32'h5596592c;
                10'd229: dout0 <= 32'hed9e6ae1;
                10'd230: dout0 <= 32'h99d1daee;
                10'd231: dout0 <= 32'h1dd63ee1;
                10'd232: dout0 <= 32'h99de6ad1;
                10'd233: dout0 <= 32'h139a1459;
                10'd234: dout0 <= 32'h99da5e6e;
                10'd235: dout0 <= 32'h911e16e5;
                10'd236: dout0 <= 32'h9639de9e;
                10'd237: dout0 <= 32'h129d51d5;
                10'd238: dout0 <= 32'h6e931e91;
                10'd239: dout0 <= 32'h199955e9;
                10'd240: dout0 <= 32'he15eae11;
                10'd241: dout0 <= 32'h619191e5;
                10'd242: dout0 <= 32'h1e659e1e;
                10'd243: dout0 <= 32'h5e995d11;
                10'd244: dout0 <= 32'h61511e1e;
                10'd245: dout0 <= 32'h5663e199;
                10'd246: dout0 <= 32'hee55bd5e;
                10'd247: dout0 <= 32'hc66199a6;
                10'd248: dout0 <= 32'h1e6b506c;
                10'd249: dout0 <= 32'he5edd26a;
                10'd250: dout0 <= 32'ha1d9fbe1;
                10'd251: dout0 <= 32'haee1b169;
                10'd252: dout0 <= 32'h9d165e95;
                10'd253: dout0 <= 32'hb3fa3c19;
                10'd254: dout0 <= 32'hed1abe5e;
                10'd255: dout0 <= 32'h6954f641;
                10'd256: dout0 <= 32'he9ee515c;
                10'd257: dout0 <= 32'h5954eac4;
                10'd258: dout0 <= 32'he6509ade;
                10'd259: dout0 <= 32'h19325eee;
                10'd260: dout0 <= 32'h99bed691;
                10'd261: dout0 <= 32'h993ee69e;
                10'd262: dout0 <= 32'h3956ae51;
                10'd263: dout0 <= 32'h513195e5;
                10'd264: dout0 <= 32'h523d5111;
                10'd265: dout0 <= 32'h1c333e5a;
                10'd266: dout0 <= 32'h603d395c;
                10'd267: dout0 <= 32'h9e995d92;
                10'd268: dout0 <= 32'h6e161918;
                10'd269: dout0 <= 32'h115ed1e0;
                10'd270: dout0 <= 32'h113192e0;
                10'd271: dout0 <= 32'he5991990;
                10'd272: dout0 <= 32'he99e9a10;
                10'd273: dout0 <= 32'he9ee1690;
                10'd274: dout0 <= 32'hea115160;
                10'd275: dout0 <= 32'h1a999d20;
                10'd276: dout0 <= 32'h961392c0;
                10'd277: dout0 <= 32'h6415ba16;
                10'd278: dout0 <= 32'he9c6fe15;
                10'd279: dout0 <= 32'hdadb5a45;
                10'd280: dout0 <= 32'h599115eb;
                10'd281: dout0 <= 32'hfdde9ce5;
                10'd282: dout0 <= 32'h139ad2ee;
                10'd283: dout0 <= 32'h619c9926;
                10'd284: dout0 <= 32'h2936de51;
                10'd285: dout0 <= 32'h55d6ec46;
                10'd286: dout0 <= 32'hd630d116;
                10'd287: dout0 <= 32'h5e9ae6a5;
                10'd288: dout0 <= 32'hedda16a5;
                10'd289: dout0 <= 32'h55dc9691;
                10'd290: dout0 <= 32'hdd3a1e6e;
                10'd291: dout0 <= 32'h9d395561;
                10'd292: dout0 <= 32'hdadd6eee;
                10'd293: dout0 <= 32'h587dd99e;
                10'd294: dout0 <= 32'h983dee91;
                10'd295: dout0 <= 32'hd995a96c;
                10'd296: dout0 <= 32'h939aaee0;
                10'd297: dout0 <= 32'h659a51e0;
                10'd298: dout0 <= 32'he16ad6b0;
                10'd299: dout0 <= 32'h59e69160;
                10'd300: dout0 <= 32'h91161910;
                10'd301: dout0 <= 32'h951e5960;
                10'd302: dout0 <= 32'h11e91390;
                10'd303: dout0 <= 32'h6a616a90;
                10'd304: dout0 <= 32'he9e5a240;
                10'd305: dout0 <= 32'hba6f36aa;
                10'd306: dout0 <= 32'he4357e83;
                10'd307: dout0 <= 32'hd515b623;
                10'd308: dout0 <= 32'h19d69cad;
                10'd309: dout0 <= 32'h1bf1da11;
                10'd310: dout0 <= 32'hb6bd3e1e;
                10'd311: dout0 <= 32'h12a612ee;
                10'd312: dout0 <= 32'he9be5123;
                10'd313: dout0 <= 32'h693a5921;
                10'd314: dout0 <= 32'h9eb06e19;
                10'd315: dout0 <= 32'h59915e1a;
                10'd316: dout0 <= 32'hd19e9616;
                10'd317: dout0 <= 32'h9d1aeea1;
                10'd318: dout0 <= 32'h5d91ee51;
                10'd319: dout0 <= 32'h1d31a56a;
                10'd320: dout0 <= 32'h555d6696;
                10'd321: dout0 <= 32'h54db91d5;
                10'd322: dout0 <= 32'hd2e5ee39;
                10'd323: dout0 <= 32'h96e91e51;
                10'd324: dout0 <= 32'h51e6a5de;
                10'd325: dout0 <= 32'hd99666d1;
                10'd326: dout0 <= 32'hde52a356;
                10'd327: dout0 <= 32'h5d1e69e0;
                10'd328: dout0 <= 32'h1eece950;
                10'd329: dout0 <= 32'h19eee5d0;
                10'd330: dout0 <= 32'h6e625e50;
                10'd331: dout0 <= 32'he1196200;
                10'd332: dout0 <= 32'h6d1aa000;
                10'd333: dout0 <= 32'h399d9e08;
                10'd334: dout0 <= 32'h06fa169d;
                10'd335: dout0 <= 32'h1c9c1149;
                10'd336: dout0 <= 32'h59e16aea;
                10'd337: dout0 <= 32'hb7f15a11;
                10'd338: dout0 <= 32'h7e999196;
                10'd339: dout0 <= 32'h6b92e2ee;
                10'd340: dout0 <= 32'h5296eb8d;
                10'd341: dout0 <= 32'h955c9e29;
                10'd342: dout0 <= 32'h59ec1aee;
                10'd343: dout0 <= 32'hde1999e1;
                10'd344: dout0 <= 32'h99996111;
                10'd345: dout0 <= 32'hdd9e6e9e;
                10'd346: dout0 <= 32'h95dd2d1a;
                10'd347: dout0 <= 32'h93d54959;
                10'd348: dout0 <= 32'h6bd3e131;
                10'd349: dout0 <= 32'h1e6d6e51;
                10'd350: dout0 <= 32'h5c6de959;
                10'd351: dout0 <= 32'hd191a9b1;
                10'd352: dout0 <= 32'hd1ee1695;
                10'd353: dout0 <= 32'h1e9ea135;
                10'd354: dout0 <= 32'h519a1e5d;
                10'd355: dout0 <= 32'h5de6eba6;
                10'd356: dout0 <= 32'h9eae1196;
                10'd357: dout0 <= 32'h95aca912;
                10'd358: dout0 <= 32'h15622238;
                10'd359: dout0 <= 32'h26a4ac90;
                10'd360: dout0 <= 32'h8f821c80;
                10'd361: dout0 <= 32'h95d6e10c;
                10'd362: dout0 <= 32'h923c318d;
                10'd363: dout0 <= 32'h3c663aad;
                10'd364: dout0 <= 32'h6569ed1e;
                10'd365: dout0 <= 32'h65e19a51;
                10'd366: dout0 <= 32'hbdd5922e;
                10'd367: dout0 <= 32'he66cc145;
                10'd368: dout0 <= 32'h5e2c0125;
                10'd369: dout0 <= 32'h11a242a1;
                10'd370: dout0 <= 32'h11ea2de1;
                10'd371: dout0 <= 32'h39e92e95;
                10'd372: dout0 <= 32'hd9e11531;
                10'd373: dout0 <= 32'h61ae211a;
                10'd374: dout0 <= 32'h3e11461e;
                10'd375: dout0 <= 32'he3e5e5d1;
                10'd376: dout0 <= 32'h9123663e;
                10'd377: dout0 <= 32'h9ecd915e;
                10'd378: dout0 <= 32'h52619691;
                10'd379: dout0 <= 32'h91e56655;
                10'd380: dout0 <= 32'h56ee1976;
                10'd381: dout0 <= 32'h59955b91;
                10'd382: dout0 <= 32'h151e19d5;
                10'd383: dout0 <= 32'hed26c9d7;
                10'd384: dout0 <= 32'h9d596a55;
                10'd385: dout0 <= 32'h93666cd1;
                10'd386: dout0 <= 32'ha568a696;
                10'd387: dout0 <= 32'h21c0e4ca;
                10'd388: dout0 <= 32'hae601482;
                10'd389: dout0 <= 32'ha9e09548;
                10'd390: dout0 <= 32'h6d14bda9;
                10'd391: dout0 <= 32'hae96e9e1;
                10'd392: dout0 <= 32'ha613142d;
                10'd393: dout0 <= 32'h9259d13d;
                10'd394: dout0 <= 32'hd9be5e15;
                10'd395: dout0 <= 32'h5edaad2a;
                10'd396: dout0 <= 32'h36a8cec1;
                10'd397: dout0 <= 32'h672a8aaa;
                10'd398: dout0 <= 32'h19ac8589;
                10'd399: dout0 <= 32'h13a98149;
                10'd400: dout0 <= 32'h9dad45e1;
                10'd401: dout0 <= 32'he9e9c191;
                10'd402: dout0 <= 32'h1569aa55;
                10'd403: dout0 <= 32'h1de16ede;
                10'd404: dout0 <= 32'ha621e639;
                10'd405: dout0 <= 32'h9eade1de;
                10'd406: dout0 <= 32'heeee39e9;
                10'd407: dout0 <= 32'h9ee19991;
                10'd408: dout0 <= 32'h9e551319;
                10'd409: dout0 <= 32'h39d19e51;
                10'd410: dout0 <= 32'hdd51a1e5;
                10'd411: dout0 <= 32'hed91e195;
                10'd412: dout0 <= 32'hb5d31aa3;
                10'd413: dout0 <= 32'h1d1a9a95;
                10'd414: dout0 <= 32'h571ca267;
                10'd415: dout0 <= 32'h651660c5;
                10'd416: dout0 <= 32'h2191628e;
                10'd417: dout0 <= 32'hadbc118e;
                10'd418: dout0 <= 32'h9d727b0a;
                10'd419: dout0 <= 32'h99395522;
                10'd420: dout0 <= 32'h65d91e6d;
                10'd421: dout0 <= 32'h6a1eda55;
                10'd422: dout0 <= 32'h21d973ec;
                10'd423: dout0 <= 32'h511e61e4;
                10'd424: dout0 <= 32'h596d26ac;
                10'd425: dout0 <= 32'h11612e46;
                10'd426: dout0 <= 32'hd925c98e;
                10'd427: dout0 <= 32'h5742aeae;
                10'd428: dout0 <= 32'h11ce496e;
                10'd429: dout0 <= 32'h1d2ead39;
                10'd430: dout0 <= 32'h3dc91c56;
                10'd431: dout0 <= 32'hde2129de;
                10'd432: dout0 <= 32'h1aa91ad9;
                10'd433: dout0 <= 32'he6e1715e;
                10'd434: dout0 <= 32'h61953dde;
                10'd435: dout0 <= 32'h5e159619;
                10'd436: dout0 <= 32'h9d139591;
                10'd437: dout0 <= 32'h99e59ed9;
                10'd438: dout0 <= 32'h11d5e6e9;
                10'd439: dout0 <= 32'hb791d459;
                10'd440: dout0 <= 32'h56e11a11;
                10'd441: dout0 <= 32'h53e9ece9;
                10'd442: dout0 <= 32'hbd51e42e;
                10'd443: dout0 <= 32'h61e3982e;
                10'd444: dout0 <= 32'hc6de1e09;
                10'd445: dout0 <= 32'ha95a2e25;
                10'd446: dout0 <= 32'h9dbaddc8;
                10'd447: dout0 <= 32'hd3d2d5e6;
                10'd448: dout0 <= 32'hde39e1de;
                10'd449: dout0 <= 32'h11115951;
                10'd450: dout0 <= 32'he632f129;
                10'd451: dout0 <= 32'ha995b929;
                10'd452: dout0 <= 32'h35c3ae28;
                10'd453: dout0 <= 32'hd5c94a4c;
                10'd454: dout0 <= 32'h5986a966;
                10'd455: dout0 <= 32'hd94a4bae;
                10'd456: dout0 <= 32'h35c56155;
                10'd457: dout0 <= 32'he5a669de;
                10'd458: dout0 <= 32'h1621611e;
                10'd459: dout0 <= 32'h5ccda555;
                10'd460: dout0 <= 32'he6e59916;
                10'd461: dout0 <= 32'h66e6d99d;
                10'd462: dout0 <= 32'hea51dd95;
                10'd463: dout0 <= 32'h5b599ed1;
                10'd464: dout0 <= 32'h9d999991;
                10'd465: dout0 <= 32'hdb51e419;
                10'd466: dout0 <= 32'h9919161e;
                10'd467: dout0 <= 32'h539e1ce9;
                10'd468: dout0 <= 32'h553e18e1;
                10'd469: dout0 <= 32'h9bdedead;
                10'd470: dout0 <= 32'h39d652c5;
                10'd471: dout0 <= 32'h29d7e2ce;
                10'd472: dout0 <= 32'h2e34a545;
                10'd473: dout0 <= 32'h0d30632d;
                10'd474: dout0 <= 32'h9bf85b8e;
                10'd475: dout0 <= 32'h4ae41522;
                10'd476: dout0 <= 32'h191199e1;
                10'd477: dout0 <= 32'h6a19de9d;
                10'd478: dout0 <= 32'ha359f6e6;
                10'd479: dout0 <= 32'h2e21b9c3;
                10'd480: dout0 <= 32'he3cd51e6;
                10'd481: dout0 <= 32'hd989e5ca;
                10'd482: dout0 <= 32'h61091e22;
                10'd483: dout0 <= 32'h1e6de2a6;
                10'd484: dout0 <= 32'hd92a166e;
                10'd485: dout0 <= 32'h31c91e96;
                10'd486: dout0 <= 32'hd4691165;
                10'd487: dout0 <= 32'h54ae1511;
                10'd488: dout0 <= 32'h96a6559e;
                10'd489: dout0 <= 32'h55c9dde1;
                10'd490: dout0 <= 32'h9965d11d;
                10'd491: dout0 <= 32'h9d955e91;
                10'd492: dout0 <= 32'h131d561e;
                10'd493: dout0 <= 32'hd55d9c99;
                10'd494: dout0 <= 32'he9d162e5;
                10'd495: dout0 <= 32'h951a9211;
                10'd496: dout0 <= 32'h9996d2a9;
                10'd497: dout0 <= 32'h556c1629;
                10'd498: dout0 <= 32'ha5d9996d;
                10'd499: dout0 <= 32'h6a152eed;
                10'd500: dout0 <= 32'hc5b19121;
                10'd501: dout0 <= 32'h3edc1d0a;
                10'd502: dout0 <= 32'hbbba356a;
                10'd503: dout0 <= 32'h42bc2528;
                10'd504: dout0 <= 32'h7c565aee;
                10'd505: dout0 <= 32'h1156519e;
                10'd506: dout0 <= 32'h6c31fce5;
                10'd507: dout0 <= 32'ha1963e4f;
                10'd508: dout0 <= 32'h15a59925;
                10'd509: dout0 <= 32'hd3e5ddae;
                10'd510: dout0 <= 32'h15261146;
                10'd511: dout0 <= 32'h59213e6e;
                10'd512: dout0 <= 32'h119195a1;
                10'd513: dout0 <= 32'h9a613196;
                10'd514: dout0 <= 32'h90e29111;
                10'd515: dout0 <= 32'h50a991e1;
                10'd516: dout0 <= 32'h92c61e1e;
                10'd517: dout0 <= 32'h55aeb3e6;
                10'd518: dout0 <= 32'hdd155155;
                10'd519: dout0 <= 32'h3d319191;
                10'd520: dout0 <= 32'h1d915e99;
                10'd521: dout0 <= 32'hd3de16d6;
                10'd522: dout0 <= 32'h11eaee95;
                10'd523: dout0 <= 32'h5a16515e;
                10'd524: dout0 <= 32'h61a99a5b;
                10'd525: dout0 <= 32'h56511ea1;
                10'd526: dout0 <= 32'h5a9626ce;
                10'd527: dout0 <= 32'hca59e98e;
                10'd528: dout0 <= 32'had56a981;
                10'd529: dout0 <= 32'h3199e365;
                10'd530: dout0 <= 32'hfbfd76fc;
                10'd531: dout0 <= 32'heef91ec2;
                10'd532: dout0 <= 32'he59e55e1;
                10'd533: dout0 <= 32'h653136d5;
                10'd534: dout0 <= 32'h9eb5de6b;
                10'd535: dout0 <= 32'h39daeeed;
                10'd536: dout0 <= 32'h3e9551ad;
                10'd537: dout0 <= 32'h55e9d669;
                10'd538: dout0 <= 32'h66265969;
                10'd539: dout0 <= 32'h95699662;
                10'd540: dout0 <= 32'h6a953aee;
                10'd541: dout0 <= 32'ha4dcdec1;
                10'd542: dout0 <= 32'h60ec9eea;
                10'd543: dout0 <= 32'h62e6ee61;
                10'd544: dout0 <= 32'h11a9691e;
                10'd545: dout0 <= 32'h655391de;
                10'd546: dout0 <= 32'h13dd111d;
                10'd547: dout0 <= 32'h19591111;
                10'd548: dout0 <= 32'ha9991569;
                10'd549: dout0 <= 32'h19d25591;
                10'd550: dout0 <= 32'he116695e;
                10'd551: dout0 <= 32'h9e1e99e5;
                10'd552: dout0 <= 32'hee52e165;
                10'd553: dout0 <= 32'h92912e69;
                10'd554: dout0 <= 32'h2a1eee63;
                10'd555: dout0 <= 32'h6dba2145;
                10'd556: dout0 <= 32'h22d9518d;
                10'd557: dout0 <= 32'h6e35eb65;
                10'd558: dout0 <= 32'h3df599ea;
                10'd559: dout0 <= 32'h597355a6;
                10'd560: dout0 <= 32'h5599591a;
                10'd561: dout0 <= 32'h2156d1d9;
                10'd562: dout0 <= 32'hbd31e699;
                10'd563: dout0 <= 32'h353895ed;
                10'd564: dout0 <= 32'h1c9e6dd5;
                10'd565: dout0 <= 32'h69e359e1;
                10'd566: dout0 <= 32'h4e19f169;
                10'd567: dout0 <= 32'hc99ed11e;
                10'd568: dout0 <= 32'h2419d921;
                10'd569: dout0 <= 32'h629e116d;
                10'd570: dout0 <= 32'ha4ea59ad;
                10'd571: dout0 <= 32'h6a1a61ae;
                10'd572: dout0 <= 32'h63319559;
                10'd573: dout0 <= 32'he9116116;
                10'd574: dout0 <= 32'he55d59ee;
                10'd575: dout0 <= 32'h2d55e551;
                10'd576: dout0 <= 32'h2de51b16;
                10'd577: dout0 <= 32'haa111599;
                10'd578: dout0 <= 32'h266eeb21;
                10'd579: dout0 <= 32'hc1eeeb5d;
                10'd580: dout0 <= 32'hca9a97a5;
                10'd581: dout0 <= 32'h2d92e761;
                10'd582: dout0 <= 32'haae55123;
                10'd583: dout0 <= 32'h2c365d25;
                10'd584: dout0 <= 32'h3e516b25;
                10'd585: dout0 <= 32'h5c5d2d4d;
                10'd586: dout0 <= 32'h7db3dd5e;
                10'd587: dout0 <= 32'h1e1e9515;
                10'd588: dout0 <= 32'h9e93d9e9;
                10'd589: dout0 <= 32'h4ee6e591;
                10'd590: dout0 <= 32'h63bc9918;
                10'd591: dout0 <= 32'h1e9c9d99;
                10'd592: dout0 <= 32'h2e665113;
                10'd593: dout0 <= 32'ha1e16a13;
                10'd594: dout0 <= 32'h46113191;
                10'd595: dout0 <= 32'hcaee5eaa;
                10'd596: dout0 <= 32'h226a2e65;
                10'd597: dout0 <= 32'haa191e11;
                10'd598: dout0 <= 32'h255ae111;
                10'd599: dout0 <= 32'h2116e1e9;
                10'd600: dout0 <= 32'h19d1d96e;
                10'd601: dout0 <= 32'had1169e5;
                10'd602: dout0 <= 32'ha19151e1;
                10'd603: dout0 <= 32'h21511915;
                10'd604: dout0 <= 32'h91111111;
                10'd605: dout0 <= 32'h23e61d1e;
                10'd606: dout0 <= 32'h4e513595;
                10'd607: dout0 <= 32'h2e66e521;
                10'd608: dout0 <= 32'h4211536d;
                10'd609: dout0 <= 32'hc116156d;
                10'd610: dout0 <= 32'h2e1a5525;
                10'd611: dout0 <= 32'h6e5ed941;
                10'd612: dout0 <= 32'h61de2dc3;
                10'd613: dout0 <= 32'ha231252d;
                10'd614: dout0 <= 32'h82112ae1;
                10'd615: dout0 <= 32'h9ee91ee6;
                10'd616: dout0 <= 32'he61d119e;
                10'd617: dout0 <= 32'h5569551e;
                10'd618: dout0 <= 32'h69915190;
                10'd619: dout0 <= 32'haa251dea;
                10'd620: dout0 <= 32'h6a125965;
                10'd621: dout0 <= 32'hce127111;
                10'd622: dout0 <= 32'h6196d936;
                10'd623: dout0 <= 32'h6cde516e;
                10'd624: dout0 <= 32'h615aa195;
                10'd625: dout0 <= 32'he9d5ee91;
                10'd626: dout0 <= 32'he1915951;
                10'd627: dout0 <= 32'h6e9eeede;
                10'd628: dout0 <= 32'h19e919ee;
                10'd629: dout0 <= 32'hc19e95d1;
                10'd630: dout0 <= 32'h61e19d1d;
                10'd631: dout0 <= 32'h6e969de9;
                10'd632: dout0 <= 32'he6915e15;
                10'd633: dout0 <= 32'h6a59e5a5;
                10'd634: dout0 <= 32'h4ee95d6e;
                10'd635: dout0 <= 32'h4e9e5169;
                10'd636: dout0 <= 32'ha663ddc3;
                10'd637: dout0 <= 32'h21c999c5;
                10'd638: dout0 <= 32'hee6615c9;
                10'd639: dout0 <= 32'h6e95ee15;
                10'd640: dout0 <= 32'h91d51b9e;
                10'd641: dout0 <= 32'h961a3b25;
                10'd642: dout0 <= 32'h0665e693;
                10'd643: dout0 <= 32'hde9a1636;
                10'd644: dout0 <= 32'h5de11d11;
                10'd645: dout0 <= 32'h1e115959;
                10'd646: dout0 <= 32'ha4945342;
                10'd647: dout0 <= 32'he9cead29;
                10'd648: dout0 <= 32'h61991e69;
                10'd649: dout0 <= 32'h6e1196a1;
                10'd650: dout0 <= 32'h5a66e1a6;
                10'd651: dout0 <= 32'h5112ea56;
                10'd652: dout0 <= 32'h21e1e69e;
                10'd653: dout0 <= 32'h6a396e15;
                10'd654: dout0 <= 32'he1e11e1e;
                10'd655: dout0 <= 32'h9a155e6e;
                10'd656: dout0 <= 32'h29155591;
                10'd657: dout0 <= 32'ha9611515;
                10'd658: dout0 <= 32'ha5e51165;
                10'd659: dout0 <= 32'hae519595;
                10'd660: dout0 <= 32'h6966dd96;
                10'd661: dout0 <= 32'ha6199d16;
                10'd662: dout0 <= 32'hae6163e1;
                10'd663: dout0 <= 32'h29616d1e;
                10'd664: dout0 <= 32'h6969ab6d;
                10'd665: dout0 <= 32'h512aee6a;
                10'd666: dout0 <= 32'he9621fa6;
                10'd667: dout0 <= 32'h95e91b91;
                10'd668: dout0 <= 32'h9cda6f69;
                10'd669: dout0 <= 32'h1196de95;
                10'd670: dout0 <= 32'h8a1f9da5;
                10'd671: dout0 <= 32'h1a66ee19;
                10'd672: dout0 <= 32'h169eee1a;
                10'd673: dout0 <= 32'h515d9e1e;
                10'd674: dout0 <= 32'h595a95d4;
                10'd675: dout0 <= 32'he51a3e9d;
                10'd676: dout0 <= 32'hd1734e1a;
                10'd677: dout0 <= 32'h32dd9c53;
                10'd678: dout0 <= 32'hbc9c5c5d;
                10'd679: dout0 <= 32'hdc59a493;
                10'd680: dout0 <= 32'hd2196eee;
                10'd681: dout0 <= 32'h991155e9;
                10'd682: dout0 <= 32'h121ea199;
                10'd683: dout0 <= 32'h11ead196;
                10'd684: dout0 <= 32'h21e695ee;
                10'd685: dout0 <= 32'ha51e5a1e;
                10'd686: dout0 <= 32'he591996e;
                10'd687: dout0 <= 32'ha91e1995;
                10'd688: dout0 <= 32'h5dce9d51;
                10'd689: dout0 <= 32'h19d96529;
                10'd690: dout0 <= 32'h1e596ea9;
                10'd691: dout0 <= 32'he91539ed;
                10'd692: dout0 <= 32'h5ea9d199;
                10'd693: dout0 <= 32'h95eedbce;
                10'd694: dout0 <= 32'hd6e96369;
                10'd695: dout0 <= 32'h36ab493a;
                10'd696: dout0 <= 32'h9ad3a322;
                10'd697: dout0 <= 32'h2be399ae;
                10'd698: dout0 <= 32'h31d9dbe9;
                10'd699: dout0 <= 32'he96e92e1;
                10'd700: dout0 <= 32'he9551651;
                10'd701: dout0 <= 32'h691e1199;
                10'd702: dout0 <= 32'h5cc9e399;
                10'd703: dout0 <= 32'hd91152bd;
                10'd704: dout0 <= 32'h3bb9ac15;
                10'd705: dout0 <= 32'h74d9e25d;
                10'd706: dout0 <= 32'h5a5c19a9;
                10'd707: dout0 <= 32'h9896ee51;
                10'd708: dout0 <= 32'hea5a5171;
                10'd709: dout0 <= 32'h16155953;
                10'd710: dout0 <= 32'h6ce65edd;
                10'd711: dout0 <= 32'h51eee2d1;
                10'd712: dout0 <= 32'h9a36e525;
                10'd713: dout0 <= 32'h6ea1ad63;
                10'd714: dout0 <= 32'h599cebe9;
                10'd715: dout0 <= 32'h9d9a1165;
                10'd716: dout0 <= 32'h9d9a231d;
                10'd717: dout0 <= 32'h1b119511;
                10'd718: dout0 <= 32'h551c96dd;
                10'd719: dout0 <= 32'hee52912d;
                10'd720: dout0 <= 32'h9e49a166;
                10'd721: dout0 <= 32'hd16722ed;
                10'd722: dout0 <= 32'h364b2e35;
                10'd723: dout0 <= 32'he8efa95d;
                10'd724: dout0 <= 32'h927b1253;
                10'd725: dout0 <= 32'hd26ae1e9;
                10'd726: dout0 <= 32'ha5399ee6;
                10'd727: dout0 <= 32'he19e12ae;
                10'd728: dout0 <= 32'he1e1d11e;
                10'd729: dout0 <= 32'h6995561e;
                10'd730: dout0 <= 32'he12e5119;
                10'd731: dout0 <= 32'hb9aee1d9;
                10'd732: dout0 <= 32'h7e6f49f1;
                10'd733: dout0 <= 32'h14e324b5;
                10'd734: dout0 <= 32'h9895a455;
                10'd735: dout0 <= 32'h5cdd9afd;
                10'd736: dout0 <= 32'h9431b63f;
                10'd737: dout0 <= 32'hdc5e9235;
                10'd738: dout0 <= 32'hb4e6e953;
                10'd739: dout0 <= 32'he86155a2;
                10'd740: dout0 <= 32'h1e55c16e;
                10'd741: dout0 <= 32'h723e966b;
                10'd742: dout0 <= 32'hfc53e19f;
                10'd743: dout0 <= 32'h7ed7691f;
                10'd744: dout0 <= 32'hda57c9e5;
                10'd745: dout0 <= 32'hd61d1d1d;
                10'd746: dout0 <= 32'h5ade11db;
                10'd747: dout0 <= 32'hd1be92ef;
                10'd748: dout0 <= 32'h3816a1e3;
                10'd749: dout0 <= 32'hb2932eab;
                10'd750: dout0 <= 32'hb6e3c527;
                10'd751: dout0 <= 32'h522a935f;
                10'd752: dout0 <= 32'hb461e9d9;
                10'd753: dout0 <= 32'h661e5ee9;
                10'd754: dout0 <= 32'h595e2a51;
                10'd755: dout0 <= 32'he569e19b;
                10'd756: dout0 <= 32'h19ee159d;
                10'd757: dout0 <= 32'h696e19ee;
                10'd758: dout0 <= 32'h1e93e669;
                10'd759: dout0 <= 32'h6e1e52ee;
                10'd760: dout0 <= 32'h65111561;
                10'd761: dout0 <= 32'h65b61e19;
                10'd762: dout0 <= 32'hbad9da91;
                10'd763: dout0 <= 32'h5a995e59;
                10'd764: dout0 <= 32'hb196b619;
                10'd765: dout0 <= 32'h599e516b;
                10'd766: dout0 <= 32'h39735561;
                10'd767: dout0 <= 32'hb29d2395;
                10'd768: dout0 <= 32'hdc1bebd1;
                10'd769: dout0 <= 32'h79b5b33d;
                10'd770: dout0 <= 32'hf29b9fb6;
                10'd771: dout0 <= 32'h321b3331;
                10'd772: dout0 <= 32'hf557b65d;
                10'd773: dout0 <= 32'hf9f51135;
                10'd774: dout0 <= 32'h3155ed39;
                10'd775: dout0 <= 32'hf6592159;
                10'd776: dout0 <= 32'hf1eee9e5;
                10'd777: dout0 <= 32'h73de62e6;
                10'd778: dout0 <= 32'hf765cea3;
                10'd779: dout0 <= 32'h535e5e19;
                10'd780: dout0 <= 32'h66e6a1e1;
                10'd781: dout0 <= 32'h51e6eee9;
                10'd782: dout0 <= 32'hed1969e9;
                10'd783: dout0 <= 32'he165955e;
                default: dout0 <= {32{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_phys_weights_l1_b2
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "weights_l1_b2" (784 words x 32 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/weights_l1_b2/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "weights_l1"
// (784 x 128):
//   bank 2 of 4, logical bits [95:64]
//   physical_row = (logical_row >> 64) & 0xffffffff; all 4 banks share one address and are read in parallel
// Physical image sha256 b676a3b5f89cb4f054730f059b08a7e117ebdff3fc499a789052028fd2441ece
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_weights_l1_b2 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [9:0]          addr0,
    output reg  [31:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                10'd0: dout0 <= 32'h1ee1e191;
                10'd1: dout0 <= 32'he6911165;
                10'd2: dout0 <= 32'h6d19a11e;
                10'd3: dout0 <= 32'h51de115e;
                10'd4: dout0 <= 32'h5915e61a;
                10'd5: dout0 <= 32'hd1a95911;
                10'd6: dout0 <= 32'h696c611e;
                10'd7: dout0 <= 32'h95619e16;
                10'd8: dout0 <= 32'he1991562;
                10'd9: dout0 <= 32'h9edeee99;
                10'd10: dout0 <= 32'h119e6956;
                10'd11: dout0 <= 32'h56995195;
                10'd12: dout0 <= 32'he16e91e1;
                10'd13: dout0 <= 32'h1e551ed6;
                10'd14: dout0 <= 32'h61e91169;
                10'd15: dout0 <= 32'he1ee9919;
                10'd16: dout0 <= 32'h69191921;
                10'd17: dout0 <= 32'h96a1e195;
                10'd18: dout0 <= 32'h691ea659;
                10'd19: dout0 <= 32'h5ed62d59;
                10'd20: dout0 <= 32'h116e1696;
                10'd21: dout0 <= 32'he11916a1;
                10'd22: dout0 <= 32'hae11e311;
                10'd23: dout0 <= 32'he9e96e9e;
                10'd24: dout0 <= 32'he15d29a1;
                10'd25: dout0 <= 32'h991ee161;
                10'd26: dout0 <= 32'h9115a561;
                10'd27: dout0 <= 32'hea611eee;
                10'd28: dout0 <= 32'h15ee9196;
                10'd29: dout0 <= 32'h1115611e;
                10'd30: dout0 <= 32'h519163aa;
                10'd31: dout0 <= 32'h19ee5199;
                10'd32: dout0 <= 32'h599d9e69;
                10'd33: dout0 <= 32'h1e59e395;
                10'd34: dout0 <= 32'hdaa2311e;
                10'd35: dout0 <= 32'h3a6ad9a2;
                10'd36: dout0 <= 32'h5eae3919;
                10'd37: dout0 <= 32'hdc12d164;
                10'd38: dout0 <= 32'h9c9c99d6;
                10'd39: dout0 <= 32'h16b0b979;
                10'd40: dout0 <= 32'h1c92d9b1;
                10'd41: dout0 <= 32'h94d431b1;
                10'd42: dout0 <= 32'hcaa26391;
                10'd43: dout0 <= 32'h2a669d36;
                10'd44: dout0 <= 32'h96b9fd56;
                10'd45: dout0 <= 32'h1cde5e72;
                10'd46: dout0 <= 32'hbc6edeea;
                10'd47: dout0 <= 32'hfaacb11a;
                10'd48: dout0 <= 32'hdca4be12;
                10'd49: dout0 <= 32'h565ab962;
                10'd50: dout0 <= 32'h1a61559a;
                10'd51: dout0 <= 32'h96e995ae;
                10'd52: dout0 <= 32'h9661e119;
                10'd53: dout0 <= 32'h115959e6;
                10'd54: dout0 <= 32'h1e515551;
                10'd55: dout0 <= 32'h6a651566;
                10'd56: dout0 <= 32'h9199ee19;
                10'd57: dout0 <= 32'h111966ee;
                10'd58: dout0 <= 32'h16551ae5;
                10'd59: dout0 <= 32'hc2beb97c;
                10'd60: dout0 <= 32'hecd1d6ba;
                10'd61: dout0 <= 32'heeaa1516;
                10'd62: dout0 <= 32'h526c99d9;
                10'd63: dout0 <= 32'h32ea7991;
                10'd64: dout0 <= 32'hb4ee7b55;
                10'd65: dout0 <= 32'hfe5affc7;
                10'd66: dout0 <= 32'hf5e8ffc9;
                10'd67: dout0 <= 32'hf8ecff9e;
                10'd68: dout0 <= 32'h3e5ab515;
                10'd69: dout0 <= 32'h19503f11;
                10'd70: dout0 <= 32'h7a90dfc1;
                10'd71: dout0 <= 32'hec605fad;
                10'd72: dout0 <= 32'haac0171a;
                10'd73: dout0 <= 32'heaa469aa;
                10'd74: dout0 <= 32'h126a19c1;
                10'd75: dout0 <= 32'h12461301;
                10'd76: dout0 <= 32'h9626532a;
                10'd77: dout0 <= 32'hbee4fdce;
                10'd78: dout0 <= 32'h1cd1f5ac;
                10'd79: dout0 <= 32'hd4eef19c;
                10'd80: dout0 <= 32'h7936b315;
                10'd81: dout0 <= 32'h5a157da3;
                10'd82: dout0 <= 32'hae9e193e;
                10'd83: dout0 <= 32'h1561ee15;
                10'd84: dout0 <= 32'h5e5e915a;
                10'd85: dout0 <= 32'hee111999;
                10'd86: dout0 <= 32'he695d999;
                10'd87: dout0 <= 32'h9c525172;
                10'd88: dout0 <= 32'h1a1add5a;
                10'd89: dout0 <= 32'h66edb365;
                10'd90: dout0 <= 32'hd8c37762;
                10'd91: dout0 <= 32'he49973e8;
                10'd92: dout0 <= 32'hbe2b716e;
                10'd93: dout0 <= 32'h9edd3153;
                10'd94: dout0 <= 32'h16edda19;
                10'd95: dout0 <= 32'h9e9375ee;
                10'd96: dout0 <= 32'h9619d525;
                10'd97: dout0 <= 32'hd4e19151;
                10'd98: dout0 <= 32'h115a3955;
                10'd99: dout0 <= 32'h11dee5a2;
                10'd100: dout0 <= 32'h119add2a;
                10'd101: dout0 <= 32'h19911366;
                10'd102: dout0 <= 32'h5a6e5b21;
                10'd103: dout0 <= 32'h92a15d2a;
                10'd104: dout0 <= 32'h29155514;
                10'd105: dout0 <= 32'hd65955ac;
                10'd106: dout0 <= 32'h3c6719ea;
                10'd107: dout0 <= 32'h306d5ee6;
                10'd108: dout0 <= 32'h58175366;
                10'd109: dout0 <= 32'ha6156215;
                10'd110: dout0 <= 32'hacae529c;
                10'd111: dout0 <= 32'h51e151e1;
                10'd112: dout0 <= 32'h5eae1e95;
                10'd113: dout0 <= 32'h15911511;
                10'd114: dout0 <= 32'hada5d916;
                10'd115: dout0 <= 32'hd527351a;
                10'd116: dout0 <= 32'h11e99224;
                10'd117: dout0 <= 32'h9e253386;
                10'd118: dout0 <= 32'hd59e3dc1;
                10'd119: dout0 <= 32'h5dd53eae;
                10'd120: dout0 <= 32'h96659126;
                10'd121: dout0 <= 32'h9c15e1d9;
                10'd122: dout0 <= 32'h19151185;
                10'd123: dout0 <= 32'hee15d189;
                10'd124: dout0 <= 32'he1911ec9;
                10'd125: dout0 <= 32'h6de55169;
                10'd126: dout0 <= 32'h65611ee5;
                10'd127: dout0 <= 32'h2e5191e1;
                10'd128: dout0 <= 32'h9131b1a1;
                10'd129: dout0 <= 32'h9ee65111;
                10'd130: dout0 <= 32'he5dedaee;
                10'd131: dout0 <= 32'ha9561961;
                10'd132: dout0 <= 32'h959369a1;
                10'd133: dout0 <= 32'ha9d1c12c;
                10'd134: dout0 <= 32'h617561cc;
                10'd135: dout0 <= 32'h1a1d662a;
                10'd136: dout0 <= 32'hae9fe0e6;
                10'd137: dout0 <= 32'h15b96c15;
                10'd138: dout0 <= 32'h95936a1a;
                10'd139: dout0 <= 32'h7c9ed522;
                10'd140: dout0 <= 32'h151ea69e;
                10'd141: dout0 <= 32'h9e599511;
                10'd142: dout0 <= 32'h16ad5316;
                10'd143: dout0 <= 32'h279fdd91;
                10'd144: dout0 <= 32'hd961d912;
                10'd145: dout0 <= 32'h61a96516;
                10'd146: dout0 <= 32'h611d5d11;
                10'd147: dout0 <= 32'h55e5e6ae;
                10'd148: dout0 <= 32'h959ea6c6;
                10'd149: dout0 <= 32'he1916dee;
                10'd150: dout0 <= 32'he19d158a;
                10'd151: dout0 <= 32'h3199eeee;
                10'd152: dout0 <= 32'h199d5661;
                10'd153: dout0 <= 32'he6616e65;
                10'd154: dout0 <= 32'h9199e92e;
                10'd155: dout0 <= 32'hee1119ee;
                10'd156: dout0 <= 32'h9995d32e;
                10'd157: dout0 <= 32'h11e11665;
                10'd158: dout0 <= 32'hd195d9a1;
                10'd159: dout0 <= 32'h169e56c6;
                10'd160: dout0 <= 32'h51d3562e;
                10'd161: dout0 <= 32'h1635ee29;
                10'd162: dout0 <= 32'ha95ee6a1;
                10'd163: dout0 <= 32'hee36e982;
                10'd164: dout0 <= 32'h6e95a92e;
                10'd165: dout0 <= 32'h52bdda56;
                10'd166: dout0 <= 32'h52d1d16a;
                10'd167: dout0 <= 32'h3091db46;
                10'd168: dout0 <= 32'h1611d15a;
                10'd169: dout0 <= 32'hede355a6;
                10'd170: dout0 <= 32'h1559a211;
                10'd171: dout0 <= 32'h6fede9d6;
                10'd172: dout0 <= 32'h155569da;
                10'd173: dout0 <= 32'h29519932;
                10'd174: dout0 <= 32'h5e9e9139;
                10'd175: dout0 <= 32'h66e9119a;
                10'd176: dout0 <= 32'h99631e29;
                10'd177: dout0 <= 32'h11a5e5ae;
                10'd178: dout0 <= 32'he52b19e1;
                10'd179: dout0 <= 32'he6e1e911;
                10'd180: dout0 <= 32'h999d9ea1;
                10'd181: dout0 <= 32'h19e759e6;
                10'd182: dout0 <= 32'h999be99e;
                10'd183: dout0 <= 32'hd1631de9;
                10'd184: dout0 <= 32'hde13d5c1;
                10'd185: dout0 <= 32'hd96dd595;
                10'd186: dout0 <= 32'h96ed3195;
                10'd187: dout0 <= 32'h151152e6;
                10'd188: dout0 <= 32'ha9a9dae1;
                10'd189: dout0 <= 32'hee9555e1;
                10'd190: dout0 <= 32'ha5dad9de;
                10'd191: dout0 <= 32'h15d91626;
                10'd192: dout0 <= 32'h6566e188;
                10'd193: dout0 <= 32'h5cc46eae;
                10'd194: dout0 <= 32'h519a169e;
                10'd195: dout0 <= 32'hd21dd56e;
                10'd196: dout0 <= 32'h36e99991;
                10'd197: dout0 <= 32'h97933d58;
                10'd198: dout0 <= 32'h9599c95d;
                10'd199: dout0 <= 32'ha36969b8;
                10'd200: dout0 <= 32'hd156db51;
                10'd201: dout0 <= 32'hed163152;
                10'd202: dout0 <= 32'he3edaad6;
                10'd203: dout0 <= 32'hadea5dd1;
                10'd204: dout0 <= 32'heb659e16;
                10'd205: dout0 <= 32'h195e7699;
                10'd206: dout0 <= 32'h2595ed5e;
                10'd207: dout0 <= 32'h699d159e;
                10'd208: dout0 <= 32'h911bc9d6;
                10'd209: dout0 <= 32'h5193195e;
                10'd210: dout0 <= 32'h952f991e;
                10'd211: dout0 <= 32'h56ab915e;
                10'd212: dout0 <= 32'h191d99d5;
                10'd213: dout0 <= 32'h11151dd5;
                10'd214: dout0 <= 32'he6d5de99;
                10'd215: dout0 <= 32'h516ede19;
                10'd216: dout0 <= 32'h99169d11;
                10'd217: dout0 <= 32'h9e9a9d99;
                10'd218: dout0 <= 32'h9d589191;
                10'd219: dout0 <= 32'h2310e9de;
                10'd220: dout0 <= 32'h1d5016ea;
                10'd221: dout0 <= 32'h55b894e5;
                10'd222: dout0 <= 32'h6d36699c;
                10'd223: dout0 <= 32'hd41ddb16;
                10'd224: dout0 <= 32'h5ee55119;
                10'd225: dout0 <= 32'h93495d32;
                10'd226: dout0 <= 32'h2fed2119;
                10'd227: dout0 <= 32'ha1a6b152;
                10'd228: dout0 <= 32'h9556ddaa;
                10'd229: dout0 <= 32'h15261998;
                10'd230: dout0 <= 32'he5169a9e;
                10'd231: dout0 <= 32'habe93d1e;
                10'd232: dout0 <= 32'h91211e9a;
                10'd233: dout0 <= 32'h63991119;
                10'd234: dout0 <= 32'h5ee99111;
                10'd235: dout0 <= 32'h199115e6;
                10'd236: dout0 <= 32'h9919a931;
                10'd237: dout0 <= 32'he91ded3d;
                10'd238: dout0 <= 32'hee6be59a;
                10'd239: dout0 <= 32'h1519e579;
                10'd240: dout0 <= 32'h5119ed76;
                10'd241: dout0 <= 32'h195e3535;
                10'd242: dout0 <= 32'ha5e1517e;
                10'd243: dout0 <= 32'h99e6bed9;
                10'd244: dout0 <= 32'h1616d15e;
                10'd245: dout0 <= 32'he3eee116;
                10'd246: dout0 <= 32'h1d92b199;
                10'd247: dout0 <= 32'h13a01a9e;
                10'd248: dout0 <= 32'ha990c0b1;
                10'd249: dout0 <= 32'h2d70209e;
                10'd250: dout0 <= 32'h95e2a25d;
                10'd251: dout0 <= 32'h9ca1e651;
                10'd252: dout0 <= 32'h15155511;
                10'd253: dout0 <= 32'h33ee5bb2;
                10'd254: dout0 <= 32'h2ba6d991;
                10'd255: dout0 <= 32'hde957793;
                10'd256: dout0 <= 32'h99915e12;
                10'd257: dout0 <= 32'h159962dc;
                10'd258: dout0 <= 32'h9963e116;
                10'd259: dout0 <= 32'heea5695a;
                10'd260: dout0 <= 32'he32365e2;
                10'd261: dout0 <= 32'h9195a91e;
                10'd262: dout0 <= 32'heee5e1d6;
                10'd263: dout0 <= 32'h9161aede;
                10'd264: dout0 <= 32'h11519a1e;
                10'd265: dout0 <= 32'h9666a133;
                10'd266: dout0 <= 32'heaeeee5e;
                10'd267: dout0 <= 32'h91111159;
                10'd268: dout0 <= 32'h611eded5;
                10'd269: dout0 <= 32'he9e92ed9;
                10'd270: dout0 <= 32'he11e9a31;
                10'd271: dout0 <= 32'h91553a5e;
                10'd272: dout0 <= 32'h1de63691;
                10'd273: dout0 <= 32'h116ed695;
                10'd274: dout0 <= 32'h93ae96ee;
                10'd275: dout0 <= 32'h19ecbc19;
                10'd276: dout0 <= 32'he0b220b5;
                10'd277: dout0 <= 32'h121220fa;
                10'd278: dout0 <= 32'heaecc9de;
                10'd279: dout0 <= 32'h4ca9a970;
                10'd280: dout0 <= 32'h21561999;
                10'd281: dout0 <= 32'h99911d36;
                10'd282: dout0 <= 32'h456a53b2;
                10'd283: dout0 <= 32'h9331fc19;
                10'd284: dout0 <= 32'h61a18ad9;
                10'd285: dout0 <= 32'h1595e4e6;
                10'd286: dout0 <= 32'h1e1de5ea;
                10'd287: dout0 <= 32'he2ee939a;
                10'd288: dout0 <= 32'hde551eea;
                10'd289: dout0 <= 32'hea66691a;
                10'd290: dout0 <= 32'ha4516296;
                10'd291: dout0 <= 32'h5c1aec56;
                10'd292: dout0 <= 32'hae9a6a1d;
                10'd293: dout0 <= 32'h1eac6a3e;
                10'd294: dout0 <= 32'h99a21efd;
                10'd295: dout0 <= 32'h61a2e9de;
                10'd296: dout0 <= 32'ha69d15b9;
                10'd297: dout0 <= 32'h25156dd1;
                10'd298: dout0 <= 32'h699b6e3e;
                10'd299: dout0 <= 32'h13ad9a55;
                10'd300: dout0 <= 32'h5b1116d9;
                10'd301: dout0 <= 32'h69e6da19;
                10'd302: dout0 <= 32'hedadde9e;
                10'd303: dout0 <= 32'hd6d5fae5;
                10'd304: dout0 <= 32'haa58ec56;
                10'd305: dout0 <= 32'hcbab0a1a;
                10'd306: dout0 <= 32'h24c98df8;
                10'd307: dout0 <= 32'h0eaeeb3c;
                10'd308: dout0 <= 32'ha9a61915;
                10'd309: dout0 <= 32'hc99ae951;
                10'd310: dout0 <= 32'ha6edea3e;
                10'd311: dout0 <= 32'h6f994a95;
                10'd312: dout0 <= 32'h1ae562e6;
                10'd313: dout0 <= 32'hda664c2e;
                10'd314: dout0 <= 32'h1e5da66a;
                10'd315: dout0 <= 32'h1ed91296;
                10'd316: dout0 <= 32'he211129e;
                10'd317: dout0 <= 32'h921ea226;
                10'd318: dout0 <= 32'h6661a2e1;
                10'd319: dout0 <= 32'h969ea459;
                10'd320: dout0 <= 32'h1eece865;
                10'd321: dout0 <= 32'he64ed1ed;
                10'd322: dout0 <= 32'hd61e9d51;
                10'd323: dout0 <= 32'he1a6e599;
                10'd324: dout0 <= 32'ha169211e;
                10'd325: dout0 <= 32'heedd6aee;
                10'd326: dout0 <= 32'h6d99a266;
                10'd327: dout0 <= 32'h5d959695;
                10'd328: dout0 <= 32'h99c99919;
                10'd329: dout0 <= 32'hd6a631e1;
                10'd330: dout0 <= 32'h9615963a;
                10'd331: dout0 <= 32'h5a995a31;
                10'd332: dout0 <= 32'h14965479;
                10'd333: dout0 <= 32'h1e352851;
                10'd334: dout0 <= 32'h1c1b04fd;
                10'd335: dout0 <= 32'h4aa2ed94;
                10'd336: dout0 <= 32'he169d669;
                10'd337: dout0 <= 32'h6d116636;
                10'd338: dout0 <= 32'h9265c4d9;
                10'd339: dout0 <= 32'h61318e67;
                10'd340: dout0 <= 32'h5a154c15;
                10'd341: dout0 <= 32'h566ea21e;
                10'd342: dout0 <= 32'h5ee12016;
                10'd343: dout0 <= 32'h6c5120e1;
                10'd344: dout0 <= 32'h19eaa81e;
                10'd345: dout0 <= 32'hee162091;
                10'd346: dout0 <= 32'he56ee49a;
                10'd347: dout0 <= 32'h69ee94da;
                10'd348: dout0 <= 32'he99a56d9;
                10'd349: dout0 <= 32'h11e65e19;
                10'd350: dout0 <= 32'h6aa99be5;
                10'd351: dout0 <= 32'h6e611e1e;
                10'd352: dout0 <= 32'h9621aa25;
                10'd353: dout0 <= 32'he6ee521e;
                10'd354: dout0 <= 32'he1a9aeee;
                10'd355: dout0 <= 32'hd5e5c695;
                10'd356: dout0 <= 32'h5d1de961;
                10'd357: dout0 <= 32'h915e916b;
                10'd358: dout0 <= 32'hda1e15de;
                10'd359: dout0 <= 32'hd059925d;
                10'd360: dout0 <= 32'ha1d4d69a;
                10'd361: dout0 <= 32'hee92659a;
                10'd362: dout0 <= 32'h26292aea;
                10'd363: dout0 <= 32'h12a11f5a;
                10'd364: dout0 <= 32'heae21965;
                10'd365: dout0 <= 32'h615a165e;
                10'd366: dout0 <= 32'h2e2dce31;
                10'd367: dout0 <= 32'h66dbe51e;
                10'd368: dout0 <= 32'haa15e06d;
                10'd369: dout0 <= 32'h9e92a06e;
                10'd370: dout0 <= 32'heee250ed;
                10'd371: dout0 <= 32'h9156e099;
                10'd372: dout0 <= 32'hee59a09d;
                10'd373: dout0 <= 32'he196d8ee;
                10'd374: dout0 <= 32'ha9de5a5e;
                10'd375: dout0 <= 32'hed919e11;
                10'd376: dout0 <= 32'h153e99e5;
                10'd377: dout0 <= 32'h9ee933ed;
                10'd378: dout0 <= 32'h5961ed19;
                10'd379: dout0 <= 32'h912ea529;
                10'd380: dout0 <= 32'he96e2919;
                10'd381: dout0 <= 32'h1599a165;
                10'd382: dout0 <= 32'h1d59e6e9;
                10'd383: dout0 <= 32'h931e11a5;
                10'd384: dout0 <= 32'h99e961ad;
                10'd385: dout0 <= 32'hd619a519;
                10'd386: dout0 <= 32'hd4591e19;
                10'd387: dout0 <= 32'hd89c516a;
                10'd388: dout0 <= 32'hd1ea1b14;
                10'd389: dout0 <= 32'h159c9dde;
                10'd390: dout0 <= 32'hebde1dc5;
                10'd391: dout0 <= 32'hbe3dd9e3;
                10'd392: dout0 <= 32'h621ee3d1;
                10'd393: dout0 <= 32'hcb259511;
                10'd394: dout0 <= 32'h0aee1e7e;
                10'd395: dout0 <= 32'he9911163;
                10'd396: dout0 <= 32'he191a441;
                10'd397: dout0 <= 32'h6152d011;
                10'd398: dout0 <= 32'h519a5a55;
                10'd399: dout0 <= 32'he55e5a1d;
                10'd400: dout0 <= 32'h65965615;
                10'd401: dout0 <= 32'h659a3e11;
                10'd402: dout0 <= 32'h9111551e;
                10'd403: dout0 <= 32'h55399515;
                10'd404: dout0 <= 32'h95995fea;
                10'd405: dout0 <= 32'h95995bed;
                10'd406: dout0 <= 32'h516e91a9;
                10'd407: dout0 <= 32'h93ce615e;
                10'd408: dout0 <= 32'h99a12e6d;
                10'd409: dout0 <= 32'h1b1a61e9;
                10'd410: dout0 <= 32'h955d1911;
                10'd411: dout0 <= 32'h1bea6535;
                10'd412: dout0 <= 32'hded5e969;
                10'd413: dout0 <= 32'h9e5de361;
                10'd414: dout0 <= 32'hd159e111;
                10'd415: dout0 <= 32'h66bd959a;
                10'd416: dout0 <= 32'ha55ae9d1;
                10'd417: dout0 <= 32'hd3fc116f;
                10'd418: dout0 <= 32'hf33a331f;
                10'd419: dout0 <= 32'hdb5e9b1d;
                10'd420: dout0 <= 32'h61ea53de;
                10'd421: dout0 <= 32'hada9591e;
                10'd422: dout0 <= 32'h455a1619;
                10'd423: dout0 <= 32'ha9311daf;
                10'd424: dout0 <= 32'hab5e1611;
                10'd425: dout0 <= 32'h631cded5;
                10'd426: dout0 <= 32'h5e661911;
                10'd427: dout0 <= 32'hae521959;
                10'd428: dout0 <= 32'h1651dd93;
                10'd429: dout0 <= 32'he95c5b15;
                10'd430: dout0 <= 32'hd936e351;
                10'd431: dout0 <= 32'hd33a5b69;
                10'd432: dout0 <= 32'h35511795;
                10'd433: dout0 <= 32'hb11e1b65;
                10'd434: dout0 <= 32'h1995196e;
                10'd435: dout0 <= 32'h1d5edea1;
                10'd436: dout0 <= 32'hdd111165;
                10'd437: dout0 <= 32'h55669565;
                10'd438: dout0 <= 32'h5995a116;
                10'd439: dout0 <= 32'h35d195e9;
                10'd440: dout0 <= 32'hd65e6ee9;
                10'd441: dout0 <= 32'h511d95ec;
                10'd442: dout0 <= 32'he9555e6a;
                10'd443: dout0 <= 32'ha157599a;
                10'd444: dout0 <= 32'ha1de5b75;
                10'd445: dout0 <= 32'h9978e967;
                10'd446: dout0 <= 32'h6b7c592b;
                10'd447: dout0 <= 32'hd3595d35;
                10'd448: dout0 <= 32'h116e5111;
                10'd449: dout0 <= 32'he1a3dd66;
                10'd450: dout0 <= 32'he3eb95a1;
                10'd451: dout0 <= 32'h93399e45;
                10'd452: dout0 <= 32'h135999e2;
                10'd453: dout0 <= 32'he96ad515;
                10'd454: dout0 <= 32'h61e25915;
                10'd455: dout0 <= 32'h6d56de1d;
                10'd456: dout0 <= 32'ha11ee3d5;
                10'd457: dout0 <= 32'he95e3d1b;
                10'd458: dout0 <= 32'h315ed3eb;
                10'd459: dout0 <= 32'h16be539e;
                10'd460: dout0 <= 32'hde3da7a5;
                10'd461: dout0 <= 32'h9d5e6d69;
                10'd462: dout0 <= 32'h591695a5;
                10'd463: dout0 <= 32'h5d1a51e1;
                10'd464: dout0 <= 32'hdd395665;
                10'd465: dout0 <= 32'h5d1e5eee;
                10'd466: dout0 <= 32'h311919a1;
                10'd467: dout0 <= 32'h9ee1ad66;
                10'd468: dout0 <= 32'he5d569e6;
                10'd469: dout0 <= 32'hedde5a6d;
                10'd470: dout0 <= 32'h1e15e2ed;
                10'd471: dout0 <= 32'h5ee1e9ee;
                10'd472: dout0 <= 32'h65615f9a;
                10'd473: dout0 <= 32'h79f09da3;
                10'd474: dout0 <= 32'h1b70756f;
                10'd475: dout0 <= 32'hb9d6d663;
                10'd476: dout0 <= 32'h1961115e;
                10'd477: dout0 <= 32'hcdc5595a;
                10'd478: dout0 <= 32'hefd6c32d;
                10'd479: dout0 <= 32'h1e3331a1;
                10'd480: dout0 <= 32'h635993ee;
                10'd481: dout0 <= 32'h6691155e;
                10'd482: dout0 <= 32'hea1e2151;
                10'd483: dout0 <= 32'hed5e1d6e;
                10'd484: dout0 <= 32'h5e9a5b51;
                10'd485: dout0 <= 32'h9a51935d;
                10'd486: dout0 <= 32'h9e5a5797;
                10'd487: dout0 <= 32'h9ab115eb;
                10'd488: dout0 <= 32'hd555ad11;
                10'd489: dout0 <= 32'h5d196566;
                10'd490: dout0 <= 32'h9519c15e;
                10'd491: dout0 <= 32'h111e6191;
                10'd492: dout0 <= 32'h951e996e;
                10'd493: dout0 <= 32'h551e395e;
                10'd494: dout0 <= 32'h151d59ae;
                10'd495: dout0 <= 32'h1eee156e;
                10'd496: dout0 <= 32'h9e9ee696;
                10'd497: dout0 <= 32'h95e561e3;
                10'd498: dout0 <= 32'h6991ee9d;
                10'd499: dout0 <= 32'h6a162e65;
                10'd500: dout0 <= 32'h6a6e2bde;
                10'd501: dout0 <= 32'hbb92e31b;
                10'd502: dout0 <= 32'h33e56b13;
                10'd503: dout0 <= 32'h1a797a57;
                10'd504: dout0 <= 32'h9c6931f1;
                10'd505: dout0 <= 32'h6665119a;
                10'd506: dout0 <= 32'hadededa1;
                10'd507: dout0 <= 32'h5b3deb25;
                10'd508: dout0 <= 32'h6d9a99c5;
                10'd509: dout0 <= 32'h935ee591;
                10'd510: dout0 <= 32'h99551e19;
                10'd511: dout0 <= 32'h9ee2e1dd;
                10'd512: dout0 <= 32'h1ad1d6d5;
                10'd513: dout0 <= 32'h163e9595;
                10'd514: dout0 <= 32'h9ed91d19;
                10'd515: dout0 <= 32'h65dda5ed;
                10'd516: dout0 <= 32'hd69e69a9;
                10'd517: dout0 <= 32'h5d9a6ec6;
                10'd518: dout0 <= 32'hd1522a95;
                10'd519: dout0 <= 32'he119ea1e;
                10'd520: dout0 <= 32'h1d95de11;
                10'd521: dout0 <= 32'hde15511a;
                10'd522: dout0 <= 32'h169e6d96;
                10'd523: dout0 <= 32'h916e91e5;
                10'd524: dout0 <= 32'he511e199;
                10'd525: dout0 <= 32'h91956129;
                10'd526: dout0 <= 32'hee5ae959;
                10'd527: dout0 <= 32'hea9ee115;
                10'd528: dout0 <= 32'h625cebed;
                10'd529: dout0 <= 32'h555e5bab;
                10'd530: dout0 <= 32'he165a7ec;
                10'd531: dout0 <= 32'hd6b4152f;
                10'd532: dout0 <= 32'ha9e119a1;
                10'd533: dout0 <= 32'hca9e9e9d;
                10'd534: dout0 <= 32'h9ad6e21e;
                10'd535: dout0 <= 32'h2f9ba68e;
                10'd536: dout0 <= 32'h6ddee16d;
                10'd537: dout0 <= 32'ha99ed992;
                10'd538: dout0 <= 32'h9159ee95;
                10'd539: dout0 <= 32'h569195d1;
                10'd540: dout0 <= 32'hda5a91dd;
                10'd541: dout0 <= 32'h12e69b15;
                10'd542: dout0 <= 32'hd2de95e5;
                10'd543: dout0 <= 32'hde9615ae;
                10'd544: dout0 <= 32'h919e1e11;
                10'd545: dout0 <= 32'h9d1e1e26;
                10'd546: dout0 <= 32'h95ee559a;
                10'd547: dout0 <= 32'he19e19ee;
                10'd548: dout0 <= 32'h19199e96;
                10'd549: dout0 <= 32'h9961ee1a;
                10'd550: dout0 <= 32'hee6de1e1;
                10'd551: dout0 <= 32'h62131a66;
                10'd552: dout0 <= 32'he1151595;
                10'd553: dout0 <= 32'h5e516155;
                10'd554: dout0 <= 32'h341e55e3;
                10'd555: dout0 <= 32'h56915555;
                10'd556: dout0 <= 32'h449617e1;
                10'd557: dout0 <= 32'h9210a727;
                10'd558: dout0 <= 32'h733d554d;
                10'd559: dout0 <= 32'h5ade9e93;
                10'd560: dout0 <= 32'h6e91111e;
                10'd561: dout0 <= 32'hae393135;
                10'd562: dout0 <= 32'h167635ae;
                10'd563: dout0 <= 32'h13559341;
                10'd564: dout0 <= 32'h6b3559ed;
                10'd565: dout0 <= 32'h1119ee1e;
                10'd566: dout0 <= 32'h91195e91;
                10'd567: dout0 <= 32'h525ed515;
                10'd568: dout0 <= 32'h129e1955;
                10'd569: dout0 <= 32'h915e115d;
                10'd570: dout0 <= 32'hd63661ae;
                10'd571: dout0 <= 32'h51589929;
                10'd572: dout0 <= 32'he9e699e6;
                10'd573: dout0 <= 32'h911ae19c;
                10'd574: dout0 <= 32'h59e1662c;
                10'd575: dout0 <= 32'h9aee9996;
                10'd576: dout0 <= 32'h9e959629;
                10'd577: dout0 <= 32'haed9ad16;
                10'd578: dout0 <= 32'hae55e12d;
                10'd579: dout0 <= 32'haaa59623;
                10'd580: dout0 <= 32'hee99e9e9;
                10'd581: dout0 <= 32'h1de6e19e;
                10'd582: dout0 <= 32'hde9eee95;
                10'd583: dout0 <= 32'h91aea115;
                10'd584: dout0 <= 32'he2ee6e95;
                10'd585: dout0 <= 32'hb256e13e;
                10'd586: dout0 <= 32'he191656b;
                10'd587: dout0 <= 32'h95e969ee;
                10'd588: dout0 <= 32'hee9a6111;
                10'd589: dout0 <= 32'he519d519;
                10'd590: dout0 <= 32'hd95e77ce;
                10'd591: dout0 <= 32'h1d59bfa5;
                10'd592: dout0 <= 32'hed9111a3;
                10'd593: dout0 <= 32'he6d16d55;
                10'd594: dout0 <= 32'h92596956;
                10'd595: dout0 <= 32'he6959159;
                10'd596: dout0 <= 32'he919e961;
                10'd597: dout0 <= 32'hddd69615;
                10'd598: dout0 <= 32'h199e1699;
                10'd599: dout0 <= 32'h911eee6a;
                10'd600: dout0 <= 32'h511e99ee;
                10'd601: dout0 <= 32'h9a1e59c2;
                10'd602: dout0 <= 32'h9a66632e;
                10'd603: dout0 <= 32'he19deeee;
                10'd604: dout0 <= 32'h11692566;
                10'd605: dout0 <= 32'h1ee956ea;
                10'd606: dout0 <= 32'h1aae96e2;
                10'd607: dout0 <= 32'h51916611;
                10'd608: dout0 <= 32'haee9a9a1;
                10'd609: dout0 <= 32'h6e9e2665;
                10'd610: dout0 <= 32'h1e366661;
                10'd611: dout0 <= 32'hd93a6611;
                10'd612: dout0 <= 32'h61a88915;
                10'd613: dout0 <= 32'h6d46ddde;
                10'd614: dout0 <= 32'h2675b334;
                10'd615: dout0 <= 32'he5e1ee11;
                10'd616: dout0 <= 32'hd6d99595;
                10'd617: dout0 <= 32'h9995959e;
                10'd618: dout0 <= 32'h31eebf49;
                10'd619: dout0 <= 32'h3679de55;
                10'd620: dout0 <= 32'h3ae9ed11;
                10'd621: dout0 <= 32'h1a15ede9;
                10'd622: dout0 <= 32'h123e1e59;
                10'd623: dout0 <= 32'h9ae55631;
                10'd624: dout0 <= 32'h1e5e95d5;
                10'd625: dout0 <= 32'h9196de11;
                10'd626: dout0 <= 32'h5111d159;
                10'd627: dout0 <= 32'h593e991a;
                10'd628: dout0 <= 32'h1e115e5a;
                10'd629: dout0 <= 32'hde51d6e1;
                10'd630: dout0 <= 32'h1a655ee2;
                10'd631: dout0 <= 32'hee9999aa;
                10'd632: dout0 <= 32'he61e1ea6;
                10'd633: dout0 <= 32'he2ee5ea4;
                10'd634: dout0 <= 32'h1126a669;
                10'd635: dout0 <= 32'h659e191d;
                10'd636: dout0 <= 32'heed1eea1;
                10'd637: dout0 <= 32'he6d1a1e5;
                10'd638: dout0 <= 32'h19719941;
                10'd639: dout0 <= 32'h2e51aa16;
                10'd640: dout0 <= 32'h1e9ae299;
                10'd641: dout0 <= 32'h6ee21a5e;
                10'd642: dout0 <= 32'h8cd4a69a;
                10'd643: dout0 <= 32'he6691d51;
                10'd644: dout0 <= 32'h91561ed9;
                10'd645: dout0 <= 32'he51e6119;
                10'd646: dout0 <= 32'h1377b14e;
                10'd647: dout0 <= 32'h11139a12;
                10'd648: dout0 <= 32'h9126a39a;
                10'd649: dout0 <= 32'h5ea51591;
                10'd650: dout0 <= 32'h1fe596e6;
                10'd651: dout0 <= 32'h6d2139e9;
                10'd652: dout0 <= 32'h51993e9e;
                10'd653: dout0 <= 32'he6d93e19;
                10'd654: dout0 <= 32'he9bd9199;
                10'd655: dout0 <= 32'h199d7119;
                10'd656: dout0 <= 32'h9e593559;
                10'd657: dout0 <= 32'h6e3d9e11;
                10'd658: dout0 <= 32'hee91ee61;
                10'd659: dout0 <= 32'ha9e91e6e;
                10'd660: dout0 <= 32'hea91191a;
                10'd661: dout0 <= 32'ha5ee56e6;
                10'd662: dout0 <= 32'h9a1e3e16;
                10'd663: dout0 <= 32'h5921ea69;
                10'd664: dout0 <= 32'h5ee1e6ae;
                10'd665: dout0 <= 32'h5a5e1a86;
                10'd666: dout0 <= 32'h9a95ba61;
                10'd667: dout0 <= 32'h969d149a;
                10'd668: dout0 <= 32'h5eaeead6;
                10'd669: dout0 <= 32'h6e109ae6;
                10'd670: dout0 <= 32'h06a2c9a1;
                10'd671: dout0 <= 32'he5e19911;
                10'd672: dout0 <= 32'h55e1e919;
                10'd673: dout0 <= 32'hed569519;
                10'd674: dout0 <= 32'ha611a3aa;
                10'd675: dout0 <= 32'h83cbdb94;
                10'd676: dout0 <= 32'he31d1da1;
                10'd677: dout0 <= 32'h63cbd9da;
                10'd678: dout0 <= 32'h97619626;
                10'd679: dout0 <= 32'hd5c5eee6;
                10'd680: dout0 <= 32'h99691ee5;
                10'd681: dout0 <= 32'he11d535e;
                10'd682: dout0 <= 32'h29699e69;
                10'd683: dout0 <= 32'h1911ed9d;
                10'd684: dout0 <= 32'h16551e31;
                10'd685: dout0 <= 32'h6d695e79;
                10'd686: dout0 <= 32'hed19de36;
                10'd687: dout0 <= 32'hee911a1a;
                10'd688: dout0 <= 32'h1e599912;
                10'd689: dout0 <= 32'hee1ed114;
                10'd690: dout0 <= 32'h96569a2c;
                10'd691: dout0 <= 32'h16692aac;
                10'd692: dout0 <= 32'h6669e562;
                10'd693: dout0 <= 32'hae661626;
                10'd694: dout0 <= 32'h556d1cea;
                10'd695: dout0 <= 32'h611f68a6;
                10'd696: dout0 <= 32'h9eeab655;
                10'd697: dout0 <= 32'h17dc532e;
                10'd698: dout0 <= 32'h695e6dad;
                10'd699: dout0 <= 32'h1111d995;
                10'd700: dout0 <= 32'h9559ee66;
                10'd701: dout0 <= 32'h19eee959;
                10'd702: dout0 <= 32'hd66d9c6e;
                10'd703: dout0 <= 32'heee6ef32;
                10'd704: dout0 <= 32'h2b0361ba;
                10'd705: dout0 <= 32'hedcf6152;
                10'd706: dout0 <= 32'h3b43e9ae;
                10'd707: dout0 <= 32'h5d8b9d1e;
                10'd708: dout0 <= 32'h652b95e3;
                10'd709: dout0 <= 32'h650d5991;
                10'd710: dout0 <= 32'h55c3d91c;
                10'd711: dout0 <= 32'h55a51116;
                10'd712: dout0 <= 32'he509e992;
                10'd713: dout0 <= 32'h99c19666;
                10'd714: dout0 <= 32'hde11a215;
                10'd715: dout0 <= 32'h51e5215a;
                10'd716: dout0 <= 32'h19ed16da;
                10'd717: dout0 <= 32'h512de658;
                10'd718: dout0 <= 32'h912de81a;
                10'd719: dout0 <= 32'hee8b1e36;
                10'd720: dout0 <= 32'h5a2311d1;
                10'd721: dout0 <= 32'he8c5c67e;
                10'd722: dout0 <= 32'h6226cc91;
                10'd723: dout0 <= 32'h6c694c7c;
                10'd724: dout0 <= 32'h18af61f2;
                10'd725: dout0 <= 32'h3691e9ad;
                10'd726: dout0 <= 32'h593eee6d;
                10'd727: dout0 <= 32'h1e11ed95;
                10'd728: dout0 <= 32'h9ee5195e;
                10'd729: dout0 <= 32'h1e991e95;
                10'd730: dout0 <= 32'h6593659e;
                10'd731: dout0 <= 32'h9a916665;
                10'd732: dout0 <= 32'hf869c69f;
                10'd733: dout0 <= 32'h7e1f44c3;
                10'd734: dout0 <= 32'hd1e7061e;
                10'd735: dout0 <= 32'hbec7061d;
                10'd736: dout0 <= 32'hb517ce5e;
                10'd737: dout0 <= 32'h3e1fc556;
                10'd738: dout0 <= 32'h318fe53a;
                10'd739: dout0 <= 32'hda9f9151;
                10'd740: dout0 <= 32'hb29fa4d9;
                10'd741: dout0 <= 32'h763f1675;
                10'd742: dout0 <= 32'h766f1e33;
                10'd743: dout0 <= 32'h9623e91d;
                10'd744: dout0 <= 32'he1a31619;
                10'd745: dout0 <= 32'hd6efa156;
                10'd746: dout0 <= 32'h5a63a291;
                10'd747: dout0 <= 32'h9a4b98f6;
                10'd748: dout0 <= 32'h9c8f6035;
                10'd749: dout0 <= 32'h504f9631;
                10'd750: dout0 <= 32'h382feebe;
                10'd751: dout0 <= 32'hbead2213;
                10'd752: dout0 <= 32'hb629a69d;
                10'd753: dout0 <= 32'hea9ea61a;
                10'd754: dout0 <= 32'h1569ee91;
                10'd755: dout0 <= 32'h1a1999ee;
                10'd756: dout0 <= 32'hd191991e;
                10'd757: dout0 <= 32'h9999e995;
                10'd758: dout0 <= 32'h11669d99;
                10'd759: dout0 <= 32'h65e991e1;
                10'd760: dout0 <= 32'he5695ede;
                10'd761: dout0 <= 32'he116e556;
                10'd762: dout0 <= 32'h1e6156d5;
                10'd763: dout0 <= 32'h56e5d6b9;
                10'd764: dout0 <= 32'h31ed1151;
                10'd765: dout0 <= 32'haaceeb3e;
                10'd766: dout0 <= 32'h1a6a13f3;
                10'd767: dout0 <= 32'h10916b7d;
                10'd768: dout0 <= 32'h92d9ca59;
                10'd769: dout0 <= 32'h18eec6fb;
                10'd770: dout0 <= 32'h50cf91b3;
                10'd771: dout0 <= 32'hde2ba955;
                10'd772: dout0 <= 32'hea656d35;
                10'd773: dout0 <= 32'h3c56ded5;
                10'd774: dout0 <= 32'h56559155;
                10'd775: dout0 <= 32'h30ede559;
                10'd776: dout0 <= 32'hb699193e;
                10'd777: dout0 <= 32'hda476eba;
                10'd778: dout0 <= 32'hd6cd127a;
                10'd779: dout0 <= 32'h1516153a;
                10'd780: dout0 <= 32'h5511699e;
                10'd781: dout0 <= 32'h5e916e11;
                10'd782: dout0 <= 32'h621911e6;
                10'd783: dout0 <= 32'h96619911;
                default: dout0 <= {32{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_phys_weights_l1_b3
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "weights_l1_b3" (784 words x 32 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/weights_l1_b3/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "weights_l1"
// (784 x 128):
//   bank 3 of 4, logical bits [127:96]
//   physical_row = (logical_row >> 96) & 0xffffffff; all 4 banks share one address and are read in parallel
// Physical image sha256 8c38b42b18a653797f39ea846fc8a6fd91ff8e175e4fd5e657a39c6d7b773a2e
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_weights_l1_b3 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [9:0]          addr0,
    output reg  [31:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                10'd0: dout0 <= 32'h11911e19;
                10'd1: dout0 <= 32'h11915e51;
                10'd2: dout0 <= 32'he5e156e5;
                10'd3: dout0 <= 32'hdd1e1e51;
                10'd4: dout0 <= 32'he991eee9;
                10'd5: dout0 <= 32'he9a1eeed;
                10'd6: dout0 <= 32'h9e996919;
                10'd7: dout0 <= 32'h1e11e1e1;
                10'd8: dout0 <= 32'h15991e59;
                10'd9: dout0 <= 32'ha69e611e;
                10'd10: dout0 <= 32'hee115ed9;
                10'd11: dout0 <= 32'h9e5e6995;
                10'd12: dout0 <= 32'h196d5e9d;
                10'd13: dout0 <= 32'he9a19925;
                10'd14: dout0 <= 32'hd51ee112;
                10'd15: dout0 <= 32'h91e96516;
                10'd16: dout0 <= 32'hee9616ea;
                10'd17: dout0 <= 32'h11ee9ede;
                10'd18: dout0 <= 32'ha591e111;
                10'd19: dout0 <= 32'h11111696;
                10'd20: dout0 <= 32'h9151ceee;
                10'd21: dout0 <= 32'h65d9a9ee;
                10'd22: dout0 <= 32'h16e569d1;
                10'd23: dout0 <= 32'h51691e61;
                10'd24: dout0 <= 32'h1996ee11;
                10'd25: dout0 <= 32'h51151dce;
                10'd26: dout0 <= 32'he199e1e1;
                10'd27: dout0 <= 32'he11e6169;
                10'd28: dout0 <= 32'ha215a291;
                10'd29: dout0 <= 32'h1a95e1e9;
                10'd30: dout0 <= 32'h9a1e9151;
                10'd31: dout0 <= 32'hce19315e;
                10'd32: dout0 <= 32'h626ee969;
                10'd33: dout0 <= 32'he9593965;
                10'd34: dout0 <= 32'hab6e133b;
                10'd35: dout0 <= 32'h69ced5eb;
                10'd36: dout0 <= 32'h2d1151e5;
                10'd37: dout0 <= 32'h4311752b;
                10'd38: dout0 <= 32'hcd9ddded;
                10'd39: dout0 <= 32'ha5e219eb;
                10'd40: dout0 <= 32'h4d1ed5c3;
                10'd41: dout0 <= 32'h23e95daf;
                10'd42: dout0 <= 32'h96c65da5;
                10'd43: dout0 <= 32'hd1a2e569;
                10'd44: dout0 <= 32'hdb5c23d3;
                10'd45: dout0 <= 32'h9bbc615b;
                10'd46: dout0 <= 32'h6b6db5af;
                10'd47: dout0 <= 32'he72ed92d;
                10'd48: dout0 <= 32'ha566d56b;
                10'd49: dout0 <= 32'ha5119de3;
                10'd50: dout0 <= 32'hebae5995;
                10'd51: dout0 <= 32'h5969e1e9;
                10'd52: dout0 <= 32'h9661e1a9;
                10'd53: dout0 <= 32'h1e111699;
                10'd54: dout0 <= 32'heeee1119;
                10'd55: dout0 <= 32'ha9161666;
                10'd56: dout0 <= 32'h96e1565e;
                10'd57: dout0 <= 32'h1951511a;
                10'd58: dout0 <= 32'h59a5ee9d;
                10'd59: dout0 <= 32'h1e3ea91b;
                10'd60: dout0 <= 32'heef2edab;
                10'd61: dout0 <= 32'h6519d567;
                10'd62: dout0 <= 32'h23c555eb;
                10'd63: dout0 <= 32'h2be29d53;
                10'd64: dout0 <= 32'h8f211317;
                10'd65: dout0 <= 32'h2f0e2fbe;
                10'd66: dout0 <= 32'h6f829d39;
                10'd67: dout0 <= 32'haf2a736f;
                10'd68: dout0 <= 32'hedae55e9;
                10'd69: dout0 <= 32'h19897ee6;
                10'd70: dout0 <= 32'h9b0975a3;
                10'd71: dout0 <= 32'hdf8ebde3;
                10'd72: dout0 <= 32'h59aab11d;
                10'd73: dout0 <= 32'ha5e919d5;
                10'd74: dout0 <= 32'h41e56e93;
                10'd75: dout0 <= 32'h218e9561;
                10'd76: dout0 <= 32'h1a4ee591;
                10'd77: dout0 <= 32'h1316db55;
                10'd78: dout0 <= 32'he9acdb9b;
                10'd79: dout0 <= 32'h6dec5be9;
                10'd80: dout0 <= 32'h13ca5bd6;
                10'd81: dout0 <= 32'he36e1316;
                10'd82: dout0 <= 32'h699e5e91;
                10'd83: dout0 <= 32'heee516e5;
                10'd84: dout0 <= 32'h9aea1991;
                10'd85: dout0 <= 32'he9666e91;
                10'd86: dout0 <= 32'h13619991;
                10'd87: dout0 <= 32'h23541923;
                10'd88: dout0 <= 32'h56a935e5;
                10'd89: dout0 <= 32'h13d13c65;
                10'd90: dout0 <= 32'heb267e1d;
                10'd91: dout0 <= 32'hdbd2b9e7;
                10'd92: dout0 <= 32'h559c5353;
                10'd93: dout0 <= 32'hc51e17bd;
                10'd94: dout0 <= 32'h91ee63dd;
                10'd95: dout0 <= 32'h51199593;
                10'd96: dout0 <= 32'h9191e591;
                10'd97: dout0 <= 32'h15256999;
                10'd98: dout0 <= 32'h2911e119;
                10'd99: dout0 <= 32'h21911651;
                10'd100: dout0 <= 32'ha99e12dd;
                10'd101: dout0 <= 32'ha9e66add;
                10'd102: dout0 <= 32'hca911d19;
                10'd103: dout0 <= 32'h41a9171d;
                10'd104: dout0 <= 32'hc1de9669;
                10'd105: dout0 <= 32'ha163e995;
                10'd106: dout0 <= 32'h8d1991eb;
                10'd107: dout0 <= 32'h15ed9a6d;
                10'd108: dout0 <= 32'ha316d359;
                10'd109: dout0 <= 32'hedb5a1de;
                10'd110: dout0 <= 32'h69336539;
                10'd111: dout0 <= 32'he1ee19ae;
                10'd112: dout0 <= 32'he91593de;
                10'd113: dout0 <= 32'h521999a6;
                10'd114: dout0 <= 32'hea199aea;
                10'd115: dout0 <= 32'h959cba43;
                10'd116: dout0 <= 32'h76a1f161;
                10'd117: dout0 <= 32'hb5a2b212;
                10'd118: dout0 <= 32'h1d66d13c;
                10'd119: dout0 <= 32'h1e9ed27e;
                10'd120: dout0 <= 32'hd91e31d9;
                10'd121: dout0 <= 32'heda9adf1;
                10'd122: dout0 <= 32'h5991de79;
                10'd123: dout0 <= 32'h96116133;
                10'd124: dout0 <= 32'h19ed599a;
                10'd125: dout0 <= 32'h911aba1a;
                10'd126: dout0 <= 32'h5d161ad9;
                10'd127: dout0 <= 32'h5e1ea1de;
                10'd128: dout0 <= 32'he9eea111;
                10'd129: dout0 <= 32'ha6e6a155;
                10'd130: dout0 <= 32'h629a6559;
                10'd131: dout0 <= 32'hca6e199e;
                10'd132: dout0 <= 32'h0a6e919d;
                10'd133: dout0 <= 32'h095d61a6;
                10'd134: dout0 <= 32'h8e1de116;
                10'd135: dout0 <= 32'h6eef91a5;
                10'd136: dout0 <= 32'h16ffa196;
                10'd137: dout0 <= 32'ha3ffee92;
                10'd138: dout0 <= 32'h155366dd;
                10'd139: dout0 <= 32'h11be9b2d;
                10'd140: dout0 <= 32'h6d9e9e15;
                10'd141: dout0 <= 32'he1191e16;
                10'd142: dout0 <= 32'hdda2d1d9;
                10'd143: dout0 <= 32'hd1d8199c;
                10'd144: dout0 <= 32'h7e527c63;
                10'd145: dout0 <= 32'h1e2e9864;
                10'd146: dout0 <= 32'h951eb49e;
                10'd147: dout0 <= 32'h59d1da95;
                10'd148: dout0 <= 32'h15551d69;
                10'd149: dout0 <= 32'h131eed16;
                10'd150: dout0 <= 32'h9d115199;
                10'd151: dout0 <= 32'h99156cb9;
                10'd152: dout0 <= 32'hd3d3315a;
                10'd153: dout0 <= 32'h15dea951;
                10'd154: dout0 <= 32'h95161655;
                10'd155: dout0 <= 32'h51ea1a91;
                10'd156: dout0 <= 32'hae9a6991;
                10'd157: dout0 <= 32'h49519139;
                10'd158: dout0 <= 32'h1c115516;
                10'd159: dout0 <= 32'h229eade9;
                10'd160: dout0 <= 32'hca1e1959;
                10'd161: dout0 <= 32'h02a11556;
                10'd162: dout0 <= 32'h41a1a952;
                10'd163: dout0 <= 32'h6eaad66c;
                10'd164: dout0 <= 32'h16a596ae;
                10'd165: dout0 <= 32'h96bf6117;
                10'd166: dout0 <= 32'h9535d393;
                10'd167: dout0 <= 32'h19e5ddad;
                10'd168: dout0 <= 32'hd9e1e616;
                10'd169: dout0 <= 32'h5e1a9191;
                10'd170: dout0 <= 32'h96b1a1e6;
                10'd171: dout0 <= 32'hd25e3eec;
                10'd172: dout0 <= 32'h91d9d469;
                10'd173: dout0 <= 32'h1159e621;
                10'd174: dout0 <= 32'h59b96625;
                10'd175: dout0 <= 32'h55511961;
                10'd176: dout0 <= 32'h5dd3e5e9;
                10'd177: dout0 <= 32'h53d11e6a;
                10'd178: dout0 <= 32'h6969a553;
                10'd179: dout0 <= 32'h559565b1;
                10'd180: dout0 <= 32'he515e591;
                10'd181: dout0 <= 32'h9d151559;
                10'd182: dout0 <= 32'h9359695e;
                10'd183: dout0 <= 32'he916aade;
                10'd184: dout0 <= 32'h5d91e69e;
                10'd185: dout0 <= 32'h6a962a31;
                10'd186: dout0 <= 32'he6e9e992;
                10'd187: dout0 <= 32'hce96c6da;
                10'd188: dout0 <= 32'h2269ae5a;
                10'd189: dout0 <= 32'h62b66ee2;
                10'd190: dout0 <= 32'h0a95919e;
                10'd191: dout0 <= 32'h12dd363a;
                10'd192: dout0 <= 32'h5693d1ec;
                10'd193: dout0 <= 32'h5a1f2651;
                10'd194: dout0 <= 32'h96d7551e;
                10'd195: dout0 <= 32'h596ed1ad;
                10'd196: dout0 <= 32'h61e5d5ae;
                10'd197: dout0 <= 32'h567ea5ea;
                10'd198: dout0 <= 32'h5db1692a;
                10'd199: dout0 <= 32'hde5a3e6e;
                10'd200: dout0 <= 32'h3ae2b66d;
                10'd201: dout0 <= 32'he155d69d;
                10'd202: dout0 <= 32'h995e26ae;
                10'd203: dout0 <= 32'he9a9e9ae;
                10'd204: dout0 <= 32'h15e9e596;
                10'd205: dout0 <= 32'h99d563ae;
                10'd206: dout0 <= 32'h9de1a619;
                10'd207: dout0 <= 32'h9d65e31d;
                10'd208: dout0 <= 32'h5deea991;
                10'd209: dout0 <= 32'hb31ea516;
                10'd210: dout0 <= 32'h1566ee15;
                10'd211: dout0 <= 32'h5dd9a19e;
                10'd212: dout0 <= 32'hd51da5de;
                10'd213: dout0 <= 32'h1e51a5e6;
                10'd214: dout0 <= 32'h66116d1a;
                10'd215: dout0 <= 32'ha65ea19e;
                10'd216: dout0 <= 32'h2e1529e2;
                10'd217: dout0 <= 32'hc2ad2516;
                10'd218: dout0 <= 32'h6615ad1e;
                10'd219: dout0 <= 32'h22991ee9;
                10'd220: dout0 <= 32'h60d57eae;
                10'd221: dout0 <= 32'he83d1eb1;
                10'd222: dout0 <= 32'h2937999a;
                10'd223: dout0 <= 32'h5ea6756d;
                10'd224: dout0 <= 32'h66166e65;
                10'd225: dout0 <= 32'h8911c1ae;
                10'd226: dout0 <= 32'h92315e4a;
                10'd227: dout0 <= 32'h5ed1d15e;
                10'd228: dout0 <= 32'h9dee7a69;
                10'd229: dout0 <= 32'h661e59e5;
                10'd230: dout0 <= 32'h19911a19;
                10'd231: dout0 <= 32'hee19919d;
                10'd232: dout0 <= 32'h15132d15;
                10'd233: dout0 <= 32'h11a165e3;
                10'd234: dout0 <= 32'h15e1a569;
                10'd235: dout0 <= 32'h6115a9ae;
                10'd236: dout0 <= 32'h16116b95;
                10'd237: dout0 <= 32'h591ec91d;
                10'd238: dout0 <= 32'h9be1ed9e;
                10'd239: dout0 <= 32'h3c3e6e1a;
                10'd240: dout0 <= 32'hda5e6156;
                10'd241: dout0 <= 32'h91911ee6;
                10'd242: dout0 <= 32'h621d2596;
                10'd243: dout0 <= 32'h611e2391;
                10'd244: dout0 <= 32'h865e69e5;
                10'd245: dout0 <= 32'h4a19a551;
                10'd246: dout0 <= 32'haad16be2;
                10'd247: dout0 <= 32'h86e3e9ee;
                10'd248: dout0 <= 32'h807761d4;
                10'd249: dout0 <= 32'h607feedc;
                10'd250: dout0 <= 32'h14d7193a;
                10'd251: dout0 <= 32'h6a39c139;
                10'd252: dout0 <= 32'he15e11e5;
                10'd253: dout0 <= 32'h41b5c912;
                10'd254: dout0 <= 32'he2d29d91;
                10'd255: dout0 <= 32'he269235b;
                10'd256: dout0 <= 32'h1e32da61;
                10'd257: dout0 <= 32'h6999e6ee;
                10'd258: dout0 <= 32'h9ad9689d;
                10'd259: dout0 <= 32'h9165a993;
                10'd260: dout0 <= 32'he6692515;
                10'd261: dout0 <= 32'h95e1e999;
                10'd262: dout0 <= 32'h9e9ac9ed;
                10'd263: dout0 <= 32'hee9ee969;
                10'd264: dout0 <= 32'h199aa3a9;
                10'd265: dout0 <= 32'h3195959e;
                10'd266: dout0 <= 32'hbe16ada2;
                10'd267: dout0 <= 32'hb69151e2;
                10'd268: dout0 <= 32'hb619e5e6;
                10'd269: dout0 <= 32'h66562916;
                10'd270: dout0 <= 32'ha9d61ed9;
                10'd271: dout0 <= 32'h2261ed9e;
                10'd272: dout0 <= 32'ha6de6996;
                10'd273: dout0 <= 32'h4ade5e19;
                10'd274: dout0 <= 32'h251e91e2;
                10'd275: dout0 <= 32'h4e39951e;
                10'd276: dout0 <= 32'h22b71d1e;
                10'd277: dout0 <= 32'h9cf72dd4;
                10'd278: dout0 <= 32'h91e3ca50;
                10'd279: dout0 <= 32'hd5e82524;
                10'd280: dout0 <= 32'h6611e166;
                10'd281: dout0 <= 32'h2193956e;
                10'd282: dout0 <= 32'hac1ae741;
                10'd283: dout0 <= 32'h3ad2a3ea;
                10'd284: dout0 <= 32'hea911611;
                10'd285: dout0 <= 32'h9911e131;
                10'd286: dout0 <= 32'h11d129d1;
                10'd287: dout0 <= 32'h1ae1391d;
                10'd288: dout0 <= 32'h61196695;
                10'd289: dout0 <= 32'h6299a165;
                10'd290: dout0 <= 32'h92ed2de9;
                10'd291: dout0 <= 32'he661e5e6;
                10'd292: dout0 <= 32'h90191319;
                10'd293: dout0 <= 32'h5cd697a1;
                10'd294: dout0 <= 32'hd4955111;
                10'd295: dout0 <= 32'h329e5956;
                10'd296: dout0 <= 32'h91e991e1;
                10'd297: dout0 <= 32'h1e969de9;
                10'd298: dout0 <= 32'ha9a6e5e1;
                10'd299: dout0 <= 32'ha259e51e;
                10'd300: dout0 <= 32'hac995119;
                10'd301: dout0 <= 32'ha19ea999;
                10'd302: dout0 <= 32'ha6d59d5a;
                10'd303: dout0 <= 32'hab39a196;
                10'd304: dout0 <= 32'h2e736d35;
                10'd305: dout0 <= 32'h625ec118;
                10'd306: dout0 <= 32'h9152a5d0;
                10'd307: dout0 <= 32'hd36219e4;
                10'd308: dout0 <= 32'ha99199e6;
                10'd309: dout0 <= 32'h29ca1966;
                10'd310: dout0 <= 32'h1861e8ca;
                10'd311: dout0 <= 32'hf2fa666a;
                10'd312: dout0 <= 32'h9a556d9e;
                10'd313: dout0 <= 32'h9965e99a;
                10'd314: dout0 <= 32'h6a13ede9;
                10'd315: dout0 <= 32'h1c1b6aad;
                10'd316: dout0 <= 32'h969361c5;
                10'd317: dout0 <= 32'hec131619;
                10'd318: dout0 <= 32'h1c991929;
                10'd319: dout0 <= 32'h14d19661;
                10'd320: dout0 <= 32'h94553e11;
                10'd321: dout0 <= 32'hb45dba11;
                10'd322: dout0 <= 32'h32edd651;
                10'd323: dout0 <= 32'h56955c14;
                10'd324: dout0 <= 32'he51951ea;
                10'd325: dout0 <= 32'ha9196999;
                10'd326: dout0 <= 32'h69911d1e;
                10'd327: dout0 <= 32'h69961915;
                10'd328: dout0 <= 32'h9e526e59;
                10'd329: dout0 <= 32'h9521e111;
                10'd330: dout0 <= 32'he511dee1;
                10'd331: dout0 <= 32'h855baab5;
                10'd332: dout0 <= 32'h053722dd;
                10'd333: dout0 <= 32'h213126f1;
                10'd334: dout0 <= 32'ha0f383f9;
                10'd335: dout0 <= 32'h9a9a9da6;
                10'd336: dout0 <= 32'h9ee51e2e;
                10'd337: dout0 <= 32'h99ae11ce;
                10'd338: dout0 <= 32'he66ba6cc;
                10'd339: dout0 <= 32'hd673a1e5;
                10'd340: dout0 <= 32'hd6ae4196;
                10'd341: dout0 <= 32'h169daed1;
                10'd342: dout0 <= 32'hee159e6d;
                10'd343: dout0 <= 32'hea9b99e1;
                10'd344: dout0 <= 32'h62e3de11;
                10'd345: dout0 <= 32'h9ce59de5;
                10'd346: dout0 <= 32'h6cdd7e69;
                10'd347: dout0 <= 32'h1a15b69d;
                10'd348: dout0 <= 32'h9c917e96;
                10'd349: dout0 <= 32'h54993231;
                10'd350: dout0 <= 32'hd1e6d031;
                10'd351: dout0 <= 32'h15951c16;
                10'd352: dout0 <= 32'h1111d21e;
                10'd353: dout0 <= 32'h5b99aa19;
                10'd354: dout0 <= 32'h591a5ee1;
                10'd355: dout0 <= 32'h19319199;
                10'd356: dout0 <= 32'hee9d9691;
                10'd357: dout0 <= 32'h66afde5d;
                10'd358: dout0 <= 32'h59a136ce;
                10'd359: dout0 <= 32'h65ad5463;
                10'd360: dout0 <= 32'h0e63daab;
                10'd361: dout0 <= 32'h21162d1a;
                10'd362: dout0 <= 32'hced54d32;
                10'd363: dout0 <= 32'h59ea6526;
                10'd364: dout0 <= 32'h9ee16eed;
                10'd365: dout0 <= 32'h611199ee;
                10'd366: dout0 <= 32'hc191d94c;
                10'd367: dout0 <= 32'h99316196;
                10'd368: dout0 <= 32'h166148e9;
                10'd369: dout0 <= 32'he297dae9;
                10'd370: dout0 <= 32'h9655d52f;
                10'd371: dout0 <= 32'h541bd191;
                10'd372: dout0 <= 32'hdc5db995;
                10'd373: dout0 <= 32'h161bb95d;
                10'd374: dout0 <= 32'h1253d666;
                10'd375: dout0 <= 32'h6c95be19;
                10'd376: dout0 <= 32'h5e61de71;
                10'd377: dout0 <= 32'h599e52b6;
                10'd378: dout0 <= 32'hdd5666d6;
                10'd379: dout0 <= 32'hd16352e1;
                10'd380: dout0 <= 32'h9551d861;
                10'd381: dout0 <= 32'hfee59295;
                10'd382: dout0 <= 32'h51599a15;
                10'd383: dout0 <= 32'h599a9491;
                10'd384: dout0 <= 32'he1b919d1;
                10'd385: dout0 <= 32'h61d9d125;
                10'd386: dout0 <= 32'he6635eab;
                10'd387: dout0 <= 32'ha9193cc7;
                10'd388: dout0 <= 32'ha56e92a9;
                10'd389: dout0 <= 32'h291ae129;
                10'd390: dout0 <= 32'hae24c35c;
                10'd391: dout0 <= 32'h65292156;
                10'd392: dout0 <= 32'ha656d3dd;
                10'd393: dout0 <= 32'he2711ace;
                10'd394: dout0 <= 32'hceacdd8c;
                10'd395: dout0 <= 32'hda9a5914;
                10'd396: dout0 <= 32'ha692ea16;
                10'd397: dout0 <= 32'h4215d19e;
                10'd398: dout0 <= 32'h6963dae9;
                10'd399: dout0 <= 32'h1e9b5165;
                10'd400: dout0 <= 32'he9195e61;
                10'd401: dout0 <= 32'h919951e9;
                10'd402: dout0 <= 32'had19bd1e;
                10'd403: dout0 <= 32'hede99a69;
                10'd404: dout0 <= 32'h96e11259;
                10'd405: dout0 <= 32'h5513aa9e;
                10'd406: dout0 <= 32'h531ed251;
                10'd407: dout0 <= 32'h95a59a55;
                10'd408: dout0 <= 32'h55191669;
                10'd409: dout0 <= 32'h565b16e9;
                10'd410: dout0 <= 32'h51b11ae9;
                10'd411: dout0 <= 32'h15591615;
                10'd412: dout0 <= 32'h6adaa661;
                10'd413: dout0 <= 32'hea9156e9;
                10'd414: dout0 <= 32'h696d96c9;
                10'd415: dout0 <= 32'h19aa1c23;
                10'd416: dout0 <= 32'h6956eaad;
                10'd417: dout0 <= 32'h19a1ea65;
                10'd418: dout0 <= 32'h2504c93c;
                10'd419: dout0 <= 32'h9d4ac596;
                10'd420: dout0 <= 32'h45e155b9;
                10'd421: dout0 <= 32'h91d91a69;
                10'd422: dout0 <= 32'h96e4b126;
                10'd423: dout0 <= 32'h35a93d94;
                10'd424: dout0 <= 32'h66e12eea;
                10'd425: dout0 <= 32'h2959396e;
                10'd426: dout0 <= 32'h2b559e65;
                10'd427: dout0 <= 32'h19b156e9;
                10'd428: dout0 <= 32'h115151e5;
                10'd429: dout0 <= 32'he5ed5ea1;
                10'd430: dout0 <= 32'h15e9e11e;
                10'd431: dout0 <= 32'h1e969119;
                10'd432: dout0 <= 32'h51995199;
                10'd433: dout0 <= 32'h91699631;
                10'd434: dout0 <= 32'h5ded9c91;
                10'd435: dout0 <= 32'h51155caa;
                10'd436: dout0 <= 32'hd9195a11;
                10'd437: dout0 <= 32'h3e5d5ce5;
                10'd438: dout0 <= 32'hc93696ee;
                10'd439: dout0 <= 32'h19315499;
                10'd440: dout0 <= 32'h965696a9;
                10'd441: dout0 <= 32'h619e91a9;
                10'd442: dout0 <= 32'h5e5992ed;
                10'd443: dout0 <= 32'h55d99cad;
                10'd444: dout0 <= 32'he79a6a95;
                10'd445: dout0 <= 32'h4989e69b;
                10'd446: dout0 <= 32'h55e82d64;
                10'd447: dout0 <= 32'hc51a6539;
                10'd448: dout0 <= 32'h395396ea;
                10'd449: dout0 <= 32'h5e5959e6;
                10'd450: dout0 <= 32'h999e3e59;
                10'd451: dout0 <= 32'heae15a32;
                10'd452: dout0 <= 32'h1c14a296;
                10'd453: dout0 <= 32'h41d216e1;
                10'd454: dout0 <= 32'hc332a6d6;
                10'd455: dout0 <= 32'h213a51c5;
                10'd456: dout0 <= 32'h6e5ada19;
                10'd457: dout0 <= 32'he1e6e9ee;
                10'd458: dout0 <= 32'h5a111d99;
                10'd459: dout0 <= 32'h5de5e1ad;
                10'd460: dout0 <= 32'he9d99e9d;
                10'd461: dout0 <= 32'h599d9151;
                10'd462: dout0 <= 32'hd915de69;
                10'd463: dout0 <= 32'h111d96ee;
                10'd464: dout0 <= 32'h59635119;
                10'd465: dout0 <= 32'h6e551a9a;
                10'd466: dout0 <= 32'h1eb696e1;
                10'd467: dout0 <= 32'he99a9ae1;
                10'd468: dout0 <= 32'h66511219;
                10'd469: dout0 <= 32'h1d1239ee;
                10'd470: dout0 <= 32'hdd9a5e55;
                10'd471: dout0 <= 32'hde5eee99;
                10'd472: dout0 <= 32'h95e8e5d9;
                10'd473: dout0 <= 32'h07c61513;
                10'd474: dout0 <= 32'h6308a39c;
                10'd475: dout0 <= 32'hefe46d75;
                10'd476: dout0 <= 32'he19191e9;
                10'd477: dout0 <= 32'h915e926a;
                10'd478: dout0 <= 32'h11eddcae;
                10'd479: dout0 <= 32'h1ed29634;
                10'd480: dout0 <= 32'h15526ad1;
                10'd481: dout0 <= 32'he9dc61d1;
                10'd482: dout0 <= 32'h63595cda;
                10'd483: dout0 <= 32'h6eb25616;
                10'd484: dout0 <= 32'h6e16ee11;
                10'd485: dout0 <= 32'h6a191d61;
                10'd486: dout0 <= 32'h1119dee5;
                10'd487: dout0 <= 32'h919355e5;
                10'd488: dout0 <= 32'h9365e96b;
                10'd489: dout0 <= 32'h1e61d1a9;
                10'd490: dout0 <= 32'h992ebe66;
                10'd491: dout0 <= 32'h591d5295;
                10'd492: dout0 <= 32'h1e551655;
                10'd493: dout0 <= 32'h9e5e9151;
                10'd494: dout0 <= 32'ha1193656;
                10'd495: dout0 <= 32'h129a9651;
                10'd496: dout0 <= 32'haa115a69;
                10'd497: dout0 <= 32'he69efe51;
                10'd498: dout0 <= 32'h66963e69;
                10'd499: dout0 <= 32'h9e96599d;
                10'd500: dout0 <= 32'he11159a3;
                10'd501: dout0 <= 32'h0581539e;
                10'd502: dout0 <= 32'h2e224fa4;
                10'd503: dout0 <= 32'h97940df3;
                10'd504: dout0 <= 32'hee2ead6d;
                10'd505: dout0 <= 32'hb9661516;
                10'd506: dout0 <= 32'hbe35e66e;
                10'd507: dout0 <= 32'h19321e9a;
                10'd508: dout0 <= 32'ha91c6e92;
                10'd509: dout0 <= 32'h31362a96;
                10'd510: dout0 <= 32'h6d3eea5c;
                10'd511: dout0 <= 32'h65d2eee6;
                10'd512: dout0 <= 32'he13a169e;
                10'd513: dout0 <= 32'h6e9e9e51;
                10'd514: dout0 <= 32'h1551e65d;
                10'd515: dout0 <= 32'he935a115;
                10'd516: dout0 <= 32'h6b6159a5;
                10'd517: dout0 <= 32'he9955169;
                10'd518: dout0 <= 32'h5519d616;
                10'd519: dout0 <= 32'h5999da53;
                10'd520: dout0 <= 32'he13ed659;
                10'd521: dout0 <= 32'h9d919951;
                10'd522: dout0 <= 32'h6916599e;
                10'd523: dout0 <= 32'he61aee1e;
                10'd524: dout0 <= 32'h9ee19e1a;
                10'd525: dout0 <= 32'h9e1e75e1;
                10'd526: dout0 <= 32'h11e665e9;
                10'd527: dout0 <= 32'h26169ad5;
                10'd528: dout0 <= 32'h89c19136;
                10'd529: dout0 <= 32'hcd06e19e;
                10'd530: dout0 <= 32'h539a63e8;
                10'd531: dout0 <= 32'h9faad3da;
                10'd532: dout0 <= 32'h159e9ae6;
                10'd533: dout0 <= 32'h5ad16ed3;
                10'd534: dout0 <= 32'h9e94eb51;
                10'd535: dout0 <= 32'he3be2662;
                10'd536: dout0 <= 32'h61901dea;
                10'd537: dout0 <= 32'h1e521662;
                10'd538: dout0 <= 32'hea5e99ae;
                10'd539: dout0 <= 32'h96aaede6;
                10'd540: dout0 <= 32'hae5e966e;
                10'd541: dout0 <= 32'he6e916a9;
                10'd542: dout0 <= 32'hed15e99d;
                10'd543: dout0 <= 32'hebe559e5;
                10'd544: dout0 <= 32'he315e965;
                10'd545: dout0 <= 32'h1b159db5;
                10'd546: dout0 <= 32'h159191e6;
                10'd547: dout0 <= 32'h65115e11;
                10'd548: dout0 <= 32'h91a65e96;
                10'd549: dout0 <= 32'ha95e95d9;
                10'd550: dout0 <= 32'h59163951;
                10'd551: dout0 <= 32'hee11191a;
                10'd552: dout0 <= 32'h5eae6991;
                10'd553: dout0 <= 32'h9151e193;
                10'd554: dout0 <= 32'h9e11ad5f;
                10'd555: dout0 <= 32'heee652b5;
                10'd556: dout0 <= 32'h2aa6e65e;
                10'd557: dout0 <= 32'h1d88e3fc;
                10'd558: dout0 <= 32'hebca1d36;
                10'd559: dout0 <= 32'h9b4a9734;
                10'd560: dout0 <= 32'he5161e9d;
                10'd561: dout0 <= 32'h3eba919d;
                10'd562: dout0 <= 32'h1b62e7b1;
                10'd563: dout0 <= 32'hb39a5e94;
                10'd564: dout0 <= 32'h3a90e756;
                10'd565: dout0 <= 32'hea9ce91a;
                10'd566: dout0 <= 32'h9a9c1e5c;
                10'd567: dout0 <= 32'h961219ae;
                10'd568: dout0 <= 32'h1a91e516;
                10'd569: dout0 <= 32'h695e19e1;
                10'd570: dout0 <= 32'h6ee55ea1;
                10'd571: dout0 <= 32'hcde9e115;
                10'd572: dout0 <= 32'h65ed9959;
                10'd573: dout0 <= 32'h5b991539;
                10'd574: dout0 <= 32'h5e11d961;
                10'd575: dout0 <= 32'h65699d1e;
                10'd576: dout0 <= 32'h1112999e;
                10'd577: dout0 <= 32'he19db6de;
                10'd578: dout0 <= 32'h99aa5959;
                10'd579: dout0 <= 32'hee6c1599;
                10'd580: dout0 <= 32'h5e9ee5e5;
                10'd581: dout0 <= 32'h916ad55d;
                10'd582: dout0 <= 32'h1a6ae5d5;
                10'd583: dout0 <= 32'h969ee1b9;
                10'd584: dout0 <= 32'he56e919a;
                10'd585: dout0 <= 32'ha36ec3f9;
                10'd586: dout0 <= 32'h1922dde9;
                10'd587: dout0 <= 32'hde1e6e1e;
                10'd588: dout0 <= 32'hd16a9151;
                10'd589: dout0 <= 32'h39e1933a;
                10'd590: dout0 <= 32'hf9e2d576;
                10'd591: dout0 <= 32'h75e8ee5c;
                10'd592: dout0 <= 32'h96184bd1;
                10'd593: dout0 <= 32'h149ce9d8;
                10'd594: dout0 <= 32'ha6ec6eda;
                10'd595: dout0 <= 32'he61e11b5;
                10'd596: dout0 <= 32'h1e111599;
                10'd597: dout0 <= 32'h29e915ee;
                10'd598: dout0 <= 32'he16195e9;
                10'd599: dout0 <= 32'heee3e995;
                10'd600: dout0 <= 32'h6311ed69;
                10'd601: dout0 <= 32'h6196ed91;
                10'd602: dout0 <= 32'h9de66b97;
                10'd603: dout0 <= 32'h11111de5;
                10'd604: dout0 <= 32'h1d126516;
                10'd605: dout0 <= 32'he5951961;
                10'd606: dout0 <= 32'h6e6e9511;
                10'd607: dout0 <= 32'hd9961919;
                10'd608: dout0 <= 32'h16651bea;
                10'd609: dout0 <= 32'h9d6eae56;
                10'd610: dout0 <= 32'he95eef11;
                10'd611: dout0 <= 32'ha96653f6;
                10'd612: dout0 <= 32'hcb412f54;
                10'd613: dout0 <= 32'h63dd6779;
                10'd614: dout0 <= 32'ha994bda3;
                10'd615: dout0 <= 32'h9e11e1ad;
                10'd616: dout0 <= 32'h15161e99;
                10'd617: dout0 <= 32'h19195e95;
                10'd618: dout0 <= 32'h56e66535;
                10'd619: dout0 <= 32'hb51ee9f1;
                10'd620: dout0 <= 32'hd66a659e;
                10'd621: dout0 <= 32'h96a0edda;
                10'd622: dout0 <= 32'heae2e936;
                10'd623: dout0 <= 32'he6e6e156;
                10'd624: dout0 <= 32'he1e1199e;
                10'd625: dout0 <= 32'hab915dde;
                10'd626: dout0 <= 32'he6e15d15;
                10'd627: dout0 <= 32'he1eda391;
                10'd628: dout0 <= 32'h66596913;
                10'd629: dout0 <= 32'h551ea519;
                10'd630: dout0 <= 32'h19d9e9dd;
                10'd631: dout0 <= 32'h1ed99b6d;
                10'd632: dout0 <= 32'h119e611d;
                10'd633: dout0 <= 32'h6e19ad9e;
                10'd634: dout0 <= 32'h5515ed1a;
                10'd635: dout0 <= 32'h119e95ee;
                10'd636: dout0 <= 32'hd1a1699a;
                10'd637: dout0 <= 32'h1915621a;
                10'd638: dout0 <= 32'h5ddaa51e;
                10'd639: dout0 <= 32'h59d12d7a;
                10'd640: dout0 <= 32'h41e61d74;
                10'd641: dout0 <= 32'h15ee1132;
                10'd642: dout0 <= 32'h76597733;
                10'd643: dout0 <= 32'h11116199;
                10'd644: dout0 <= 32'h191256ed;
                10'd645: dout0 <= 32'h95ee6ade;
                10'd646: dout0 <= 32'hdcf06339;
                10'd647: dout0 <= 32'hbcda3df9;
                10'd648: dout0 <= 32'h52d18339;
                10'd649: dout0 <= 32'h1216abd9;
                10'd650: dout0 <= 32'h26166752;
                10'd651: dout0 <= 32'h9eee599c;
                10'd652: dout0 <= 32'h65e511be;
                10'd653: dout0 <= 32'h91e65556;
                10'd654: dout0 <= 32'h669111de;
                10'd655: dout0 <= 32'h11e5991e;
                10'd656: dout0 <= 32'h95e99db1;
                10'd657: dout0 <= 32'h95911d9d;
                10'd658: dout0 <= 32'h1e5e6169;
                10'd659: dout0 <= 32'h1de96d1d;
                10'd660: dout0 <= 32'h6119e955;
                10'd661: dout0 <= 32'h5e11c159;
                10'd662: dout0 <= 32'he21129e1;
                10'd663: dout0 <= 32'h1d1969e9;
                10'd664: dout0 <= 32'h3519199a;
                10'd665: dout0 <= 32'hed336e92;
                10'd666: dout0 <= 32'h55e12371;
                10'd667: dout0 <= 32'h9979cb3e;
                10'd668: dout0 <= 32'h9a5a69fa;
                10'd669: dout0 <= 32'hd55e67b9;
                10'd670: dout0 <= 32'h3ee23ba6;
                10'd671: dout0 <= 32'h1199e61e;
                10'd672: dout0 <= 32'h55aeeada;
                10'd673: dout0 <= 32'h1e19e61a;
                10'd674: dout0 <= 32'hadad92e1;
                10'd675: dout0 <= 32'h90bdd049;
                10'd676: dout0 <= 32'hf5f589e6;
                10'd677: dout0 <= 32'hd93e8bae;
                10'd678: dout0 <= 32'hee39ab1a;
                10'd679: dout0 <= 32'hea59e56a;
                10'd680: dout0 <= 32'h9d112362;
                10'd681: dout0 <= 32'h66611996;
                10'd682: dout0 <= 32'h96e3599e;
                10'd683: dout0 <= 32'heed1e9de;
                10'd684: dout0 <= 32'hee5de939;
                10'd685: dout0 <= 32'hee9e9335;
                10'd686: dout0 <= 32'h15591391;
                10'd687: dout0 <= 32'h6d361d56;
                10'd688: dout0 <= 32'h993ee59a;
                10'd689: dout0 <= 32'h91926392;
                10'd690: dout0 <= 32'h5de56535;
                10'd691: dout0 <= 32'h91eb9596;
                10'd692: dout0 <= 32'h9ed56d1c;
                10'd693: dout0 <= 32'hd5ee9596;
                10'd694: dout0 <= 32'h96e115d2;
                10'd695: dout0 <= 32'h3b11c936;
                10'd696: dout0 <= 32'heb204ffa;
                10'd697: dout0 <= 32'hab24dd24;
                10'd698: dout0 <= 32'heda636ea;
                10'd699: dout0 <= 32'hd3eed596;
                10'd700: dout0 <= 32'h55656191;
                10'd701: dout0 <= 32'h15e5e95e;
                10'd702: dout0 <= 32'h61de9ed5;
                10'd703: dout0 <= 32'hc55b9ec5;
                10'd704: dout0 <= 32'hdf11434e;
                10'd705: dout0 <= 32'hfdbe09e9;
                10'd706: dout0 <= 32'h3b7e6969;
                10'd707: dout0 <= 32'hdf51c9ee;
                10'd708: dout0 <= 32'hfe51c56a;
                10'd709: dout0 <= 32'hbe966b11;
                10'd710: dout0 <= 32'h397d5ec9;
                10'd711: dout0 <= 32'h1d3de522;
                10'd712: dout0 <= 32'h5136e3e6;
                10'd713: dout0 <= 32'h5cbe29ec;
                10'd714: dout0 <= 32'hd959e962;
                10'd715: dout0 <= 32'h29192e16;
                10'd716: dout0 <= 32'h16be235a;
                10'd717: dout0 <= 32'heddd2595;
                10'd718: dout0 <= 32'ha9dd2d92;
                10'd719: dout0 <= 32'h1cfe63e1;
                10'd720: dout0 <= 32'h12131d56;
                10'd721: dout0 <= 32'h91b32318;
                10'd722: dout0 <= 32'ha9331d26;
                10'd723: dout0 <= 32'h23b16556;
                10'd724: dout0 <= 32'h45322ff1;
                10'd725: dout0 <= 32'h35156961;
                10'd726: dout0 <= 32'h199ad512;
                10'd727: dout0 <= 32'h1b1919e9;
                10'd728: dout0 <= 32'h1e165ad6;
                10'd729: dout0 <= 32'h9ee699ee;
                10'd730: dout0 <= 32'h611161ed;
                10'd731: dout0 <= 32'h99e16612;
                10'd732: dout0 <= 32'hf36b4156;
                10'd733: dout0 <= 32'h7d394c33;
                10'd734: dout0 <= 32'hb796c2d9;
                10'd735: dout0 <= 32'hbbee0169;
                10'd736: dout0 <= 32'h31516129;
                10'd737: dout0 <= 32'hfdd5262a;
                10'd738: dout0 <= 32'hfdfe1192;
                10'd739: dout0 <= 32'h39b6a1ed;
                10'd740: dout0 <= 32'h197ec165;
                10'd741: dout0 <= 32'h5efe0919;
                10'd742: dout0 <= 32'h75590a95;
                10'd743: dout0 <= 32'h54a6039e;
                10'd744: dout0 <= 32'h923e0d91;
                10'd745: dout0 <= 32'hb67a8e13;
                10'd746: dout0 <= 32'h9a7e0615;
                10'd747: dout0 <= 32'h9c51ad51;
                10'd748: dout0 <= 32'h2c3a0d5e;
                10'd749: dout0 <= 32'h12dd25d8;
                10'd750: dout0 <= 32'h5a96a592;
                10'd751: dout0 <= 32'hb65da5b5;
                10'd752: dout0 <= 32'hb191a6f3;
                10'd753: dout0 <= 32'hed659d11;
                10'd754: dout0 <= 32'h61ed959a;
                10'd755: dout0 <= 32'heea511d1;
                10'd756: dout0 <= 32'he911ee91;
                10'd757: dout0 <= 32'h21651e9e;
                10'd758: dout0 <= 32'h1e95e1e5;
                10'd759: dout0 <= 32'heee119d5;
                10'd760: dout0 <= 32'h19e1e9e2;
                10'd761: dout0 <= 32'h6e5eed61;
                10'd762: dout0 <= 32'hb9112de9;
                10'd763: dout0 <= 32'hd1e1611e;
                10'd764: dout0 <= 32'h5191a599;
                10'd765: dout0 <= 32'h61ce1b22;
                10'd766: dout0 <= 32'he19d5966;
                10'd767: dout0 <= 32'h13eba211;
                10'd768: dout0 <= 32'h97a3aae1;
                10'd769: dout0 <= 32'hed2dafa4;
                10'd770: dout0 <= 32'hfd430918;
                10'd771: dout0 <= 32'h3d450615;
                10'd772: dout0 <= 32'h964dc92e;
                10'd773: dout0 <= 32'h996b2622;
                10'd774: dout0 <= 32'hbee72ee5;
                10'd775: dout0 <= 32'hb54fea99;
                10'd776: dout0 <= 32'h5595529a;
                10'd777: dout0 <= 32'h592a3eec;
                10'd778: dout0 <= 32'hde245518;
                10'd779: dout0 <= 32'h65aaf5ee;
                10'd780: dout0 <= 32'h9611591e;
                10'd781: dout0 <= 32'h61e69e91;
                10'd782: dout0 <= 32'he9969969;
                10'd783: dout0 <= 32'h9919e9ee;
                default: dout0 <= {32{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_phys_weights_l2
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "weights_l2" (32 words x 40 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/weights_l2/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "weights_l2"
// (32 x 40):
//   bank 0 of 1, logical bits [39:0]
//   identity: the logical word is already byte granular
// Physical image sha256 0f475f7ea7b7dff0fd6f14cf958f157e1239adebeecbb98f7e0357dc2d314a0c
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_weights_l2 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [4:0]          addr0,
    output reg  [39:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                5'd0: dout0 <= 40'h9f82cb9d0a;
                5'd1: dout0 <= 40'h895bb0ce15;
                5'd2: dout0 <= 40'h0bc7df0e03;
                5'd3: dout0 <= 40'hd56f85ea4e;
                5'd4: dout0 <= 40'hc6e11730be;
                5'd5: dout0 <= 40'hc12ed60023;
                5'd6: dout0 <= 40'hd3683ae90b;
                5'd7: dout0 <= 40'h95a16ac3d5;
                5'd8: dout0 <= 40'h6499e5630b;
                5'd9: dout0 <= 40'he1307ad33e;
                5'd10: dout0 <= 40'h2b75ae0ba6;
                5'd11: dout0 <= 40'h53ccbfd1c3;
                5'd12: dout0 <= 40'hcbdb692bd4;
                5'd13: dout0 <= 40'h4f39c2e291;
                5'd14: dout0 <= 40'h3e0a52515d;
                5'd15: dout0 <= 40'hcd8a0f76ea;
                5'd16: dout0 <= 40'hc8562c9259;
                5'd17: dout0 <= 40'he253bac9a1;
                5'd18: dout0 <= 40'h3256d11092;
                5'd19: dout0 <= 40'h58e7858193;
                5'd20: dout0 <= 40'hdcdd06de9a;
                5'd21: dout0 <= 40'h173591dfa0;
                5'd22: dout0 <= 40'hba66038d59;
                5'd23: dout0 <= 40'hedd89c245d;
                5'd24: dout0 <= 40'h73935029e3;
                5'd25: dout0 <= 40'h19760ef3ae;
                5'd26: dout0 <= 40'h90a3951159;
                5'd27: dout0 <= 40'h2ca451aed9;
                5'd28: dout0 <= 40'h15d99e7940;
                5'd29: dout0 <= 40'h9edec5dea0;
                5'd30: dout0 <= 40'h19d9a5cc3e;
                5'd31: dout0 <= 40'h32ae21b4da;
                default: dout0 <= {40{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_phys_bias_l1
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "bias_l1" (32 words x 24 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/bias_l1/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "bias_l1"
// (32 x 22):
//   bank 0 of 1, logical bits [21:0]
//   physical_row = sign_extend_24(logical_row_22); the wrapper truncates back to 22 bits and re-extends to the 22-bit bus
// Physical image sha256 bd8e7f6a00b5e5530cf80dd08f5cee1fb1803b956a3412e7f896f39826ada9a3
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_bias_l1 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [4:0]          addr0,
    output reg  [23:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                5'd0: dout0 <= 24'hf70000;
                5'd1: dout0 <= 24'hadffff;
                5'd2: dout0 <= 24'h388000;
                5'd3: dout0 <= 24'hc0ffff;
                5'd4: dout0 <= 24'h290000;
                5'd5: dout0 <= 24'h240000;
                5'd6: dout0 <= 24'h03ffff;
                5'd7: dout0 <= 24'h920000;
                5'd8: dout0 <= 24'h4d8000;
                5'd9: dout0 <= 24'hf88000;
                5'd10: dout0 <= 24'he50000;
                5'd11: dout0 <= 24'h0c0000;
                5'd12: dout0 <= 24'h48ffff;
                5'd13: dout0 <= 24'hfbffff;
                5'd14: dout0 <= 24'h35ffff;
                5'd15: dout0 <= 24'haa0000;
                5'd16: dout0 <= 24'h29ffff;
                5'd17: dout0 <= 24'h218000;
                5'd18: dout0 <= 24'hb30000;
                5'd19: dout0 <= 24'h9d7fff;
                5'd20: dout0 <= 24'h59ffff;
                5'd21: dout0 <= 24'h5effff;
                5'd22: dout0 <= 24'h948000;
                5'd23: dout0 <= 24'h360000;
                5'd24: dout0 <= 24'hec0000;
                5'd25: dout0 <= 24'h4d0000;
                5'd26: dout0 <= 24'hc80000;
                5'd27: dout0 <= 24'h870000;
                5'd28: dout0 <= 24'h450000;
                5'd29: dout0 <= 24'hb88000;
                5'd30: dout0 <= 24'h59ffff;
                5'd31: dout0 <= 24'he77fff;
                default: dout0 <= {24{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_phys_bias_l2
//
// model2rtl behavioural model of the contents of the PHYSICAL OpenROM macro
// "bias_l2" (10 words x 24 bits), which exists on disk as
// GDS/SPICE/LEF under build/stage5/bias_l2/out/.
//
// It is NOT OpenROM-generated Verilog.  OpenROM's own .v output is a
// byte-oriented, delay-based, non-synthesizable stub that does not implement
// this project's read contract, so it is not used as a backend.
//
// Derivation from the canonical logical image "bias_l2"
// (10 x 17):
//   bank 0 of 1, logical bits [16:0]
//   physical_row = sign_extend_24(logical_row_17); the wrapper truncates back to 17 bits and re-extends to the 22-bit bus
// Physical image sha256 86d4111b7cb6b5d8291d0f99da06f7901c7f0cf66889ed2dbcf28efbfe8ea8b2
// Bit order on dout0: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_phys_bias_l2 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [3:0]          addr0,
    output reg  [23:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                4'd0: dout0 <= 24'h69ffff;
                4'd1: dout0 <= 24'h500000;
                4'd2: dout0 <= 24'h400000;
                4'd3: dout0 <= 24'hcbffff;
                4'd4: dout0 <= 24'h940000;
                4'd5: dout0 <= 24'h0a0000;
                4'd6: dout0 <= 24'h6bffff;
                4'd7: dout0 <= 24'h9c0000;
                4'd8: dout0 <= 24'hc80000;
                4'd9: dout0 <= 24'h6dffff;
                default: dout0 <= {24{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Stage-5 physical backend wrapper. ASIC / SKY130 only.
//
// Presents byte-for-byte the frozen logical interface and hides the fact that
// layer-1 weights now live in 4 macros and the biases are stored 24 bits wide.
// ---------------------------------------------------------------------------
module mnist_mlp_params_openrom_phys (
    input  wire          clk,                       // single clock, shared with the fabric
    input  wire          wmem_en,                   // read strobe
    input  wire          wmem_layer,                // 0 = layer 1, 1 = layer 2
    input  wire [9:0]    wmem_addr,                 // input-feature index
    output wire [127:0]  wmem_data,                 // packed weight indices
    input  wire          bmem_en,                   // read strobe
    input  wire          bmem_layer,                // 0 = layer 1, 1 = layer 2
    input  wire [5:0]    bmem_addr,                 // output-neuron index
    output wire [21:0]   bmem_data                  // sign-extended bias
);

    genvar gi;

    // ---- macro strobes and range qualification -------------------------
    wire wsel_l1 = wmem_en && (wmem_layer == 1'b0) && (wmem_addr < 10'd784);
    wire wsel_l2 = wmem_en && (wmem_layer == 1'b1) && (wmem_addr < 10'd32);
    wire bsel_l1 = bmem_en && (bmem_layer == 1'b0) && (bmem_addr < 6'd32);
    wire bsel_l2 = bmem_en && (bmem_layer == 1'b1) && (bmem_addr < 6'd10);

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

    // ---- layer-1 weight banks: ONE address, 4 macros, read in parallel ----
    wire [31:0] wl1b0_dout;
    wire [31:0] wl1b0_word;
    wire [31:0] wl1b1_dout;
    wire [31:0] wl1b1_word;
    wire [31:0] wl1b2_dout;
    wire [31:0] wl1b2_word;
    wire [31:0] wl1b3_dout;
    wire [31:0] wl1b3_word;
    rom_phys_weights_l1_b0 u_wl1_b0 (.clk0(clk), .cs0(wsel_l1),
                                .addr0(wmem_addr[9:0]), .dout0(wl1b0_dout));
    rom_phys_weights_l1_b1 u_wl1_b1 (.clk0(clk), .cs0(wsel_l1),
                                .addr0(wmem_addr[9:0]), .dout0(wl1b1_dout));
    rom_phys_weights_l1_b2 u_wl1_b2 (.clk0(clk), .cs0(wsel_l1),
                                .addr0(wmem_addr[9:0]), .dout0(wl1b2_dout));
    rom_phys_weights_l1_b3 u_wl1_b3 (.clk0(clk), .cs0(wsel_l1),
                                .addr0(wmem_addr[9:0]), .dout0(wl1b3_dout));
    generate
        for (gi = 0; gi < 32; gi = gi + 1) begin : WL1B0_WORD_REV
            assign wl1b0_word[gi] = wl1b0_dout[31 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 32; gi = gi + 1) begin : WL1B1_WORD_REV
            assign wl1b1_word[gi] = wl1b1_dout[31 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 32; gi = gi + 1) begin : WL1B2_WORD_REV
            assign wl1b2_word[gi] = wl1b2_dout[31 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 32; gi = gi + 1) begin : WL1B3_WORD_REV
            assign wl1b3_word[gi] = wl1b3_dout[31 - gi];
        end
    endgenerate
    // logical word = {bank3, bank2, bank1, bank0}
    wire [127:0] wl1_word = {wl1b3_word, wl1b2_word, wl1b1_word, wl1b0_word};

    // ---- the byte-granular macros ---------------------------------------
    wire [39:0]  wl2_dout;
    wire [39:0]  wl2_word;
    wire [23:0]  bl1_dout;
    wire [23:0]  bl1_word;
    wire [23:0]  bl2_dout;
    wire [23:0]  bl2_word;

    rom_phys_weights_l2 u_wl2 (.clk0(clk), .cs0(wsel_l2),
                                .addr0(wmem_addr[4:0]), .dout0(wl2_dout));
    rom_phys_bias_l1    u_bl1 (.clk0(clk), .cs0(bsel_l1),
                                .addr0(bmem_addr[4:0]), .dout0(bl1_dout));
    rom_phys_bias_l2    u_bl2 (.clk0(clk), .cs0(bsel_l2),
                                .addr0(bmem_addr[3:0]), .dout0(bl2_dout));

    generate
        for (gi = 0; gi < 40; gi = gi + 1) begin : WL2_WORD_REV
            assign wl2_word[gi] = wl2_dout[39 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 24; gi = gi + 1) begin : BL1_WORD_REV
            assign bl1_word[gi] = bl1_dout[23 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 24; gi = gi + 1) begin : BL2_WORD_REV
            assign bl2_word[gi] = bl2_dout[23 - gi];
        end
    endgenerate

    // ---- undo the physical bias padding ---------------------------------
    // The physical word is sign extended to 24 bits.  Take the logical
    // low bits back and SIGN extend them onto the 22-bit bus. Never zero extend.
    wire [21:0] bl1_logical = bl1_word[21:0];
    wire [16:0] bl2_logical = bl2_word[16:0];

    // ---- present the fixed interface ------------------------------------
    assign wmem_data = (wvalid_d == 1'b0) ? {128{1'b0}}
                     : (wlayer_d == 1'b0) ? wl1_word
                                          : {88'd0, wl2_word};

    assign bmem_data = (bvalid_d == 1'b0) ? {22{1'b0}}
                     : (blayer_d == 1'b0)
                       ? {{0{bl1_logical[21]}}, bl1_logical}
                       : {{5{bl2_logical[16]}}, bl2_logical};

endmodule

`default_nettype wire
