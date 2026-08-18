// ===========================================================================
// mnist_mlp_params_openram.v -- OpenRAM/OpenROM ASIC backend
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
// OpenROM DATA CONVENTION (proven empirically, see the Stage-2 report)
//   OpenROM stores the input file as a big-endian bit stream, first bit
//   first. Word A of the file lands at addr0 = A. Within a word, the macro
//   drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value,
//   i.e. dout0 is BIT REVERSED with respect to a Verilog [word_bits-1:0]
//   literal. This was proven empirically against a generated SPICE netlist,
//   not assumed.
//
// PHYSICAL MACRO STATUS AT GENERATION TIME
//   weights_l1  physical macro NOT generated: not attempted
//   weights_l2  physical macro generated (gds, lef, log, lvs.sp, py, sp, v)
//   bias_l1     physical macro NOT generated: not attempted
//   bias_l2     physical macro NOT generated: not attempted
//
// The behavioural macro models below are OURS. OpenROM's own .v output
// is a byte-oriented, delay-based, non-synthesizable stub and is not used.
//
// SOURCE IMAGES (canonical, model2rtl-param-image-v1)
//   weights_l1  depth  784  width 128  sha256 e7fd9a1668b71ff64616466a0ed0f77a3dae098836fde86d5906f53416216d14
//   weights_l2  depth   32  width  40  sha256 b3866b5dcbd1e60e75300794786c9c75fa8e08361dbb31144182748bee934cec
//   bias_l1     depth   32  width  22  sha256 ac8563c111b41dd72a09b55ee3136ab71e4f538a567b84a50c9de949f520364d
//   bias_l2     depth   10  width  17  sha256 efb63bb9cc7b26d721b4fc53f19aaed428916dae6dc1ed29074f8e0dac942482
// ===========================================================================

`default_nettype none

// ---------------------------------------------------------------------------
// rom_macro_weights_l1
//
// model2rtl behavioural model for the generated OpenROM contents of the
// "weights_l1" macro.  It is NOT OpenROM-generated Verilog: the OpenROM
// compiler's own .v output is a byte-oriented, delay-based, non-synthesizable
// stub that does not implement this project's read contract, so it is not used.
//
// Pin names follow the OpenROM macro convention (clk0 / cs0 / addr0 / dout0) so
// that dropping in the physical macro changes only this module body.
//
// Contents: 784 words x 128 bits, canonical image sha256
//   e7fd9a1668b71ff64616466a0ed0f77a3dae098836fde86d5906f53416216d14
// Bit order: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_macro_weights_l1 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [9:0]           addr0,
    output reg  [127:0]        dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                10'd0: dout0 <= 128'h19a9511511e669511ee1e19111911e19;
                10'd1: dout0 <= 128'h159ea1165a1195e5e691116511915e51;
                10'd2: dout0 <= 128'hd11d9d55119e656e6d19a11ee5e156e5;
                10'd3: dout0 <= 128'h6eaaeae15e5196e151de115edd1e1e51;
                10'd4: dout0 <= 128'h1612991e116925e15915e61ae991eee9;
                10'd5: dout0 <= 128'h69ae95e6eee59e96d1a95911e9a1eeed;
                10'd6: dout0 <= 128'he655eee99e6d6e1d696c611e9e996919;
                10'd7: dout0 <= 128'h965e161ee659195995619e161e11e1e1;
                10'd8: dout0 <= 128'h9e999dde91ad6156e199156215991e59;
                10'd9: dout0 <= 128'h91d9561961e611669edeee99a69e611e;
                10'd10: dout0 <= 128'he9599e9a696ed919119e6956ee115ed9;
                10'd11: dout0 <= 128'he559e19119169e61569951959e5e6995;
                10'd12: dout0 <= 128'he66695ee5a619e9de16e91e1196d5e9d;
                10'd13: dout0 <= 128'h9e61ee151e961e691e551ed6e9a19925;
                10'd14: dout0 <= 128'h612ee1951911e91961e91169d51ee112;
                10'd15: dout0 <= 128'hd19ae3e111659191e1ee991991e96516;
                10'd16: dout0 <= 128'h661196515ae56e1969191921ee9616ea;
                10'd17: dout0 <= 128'h19e6969991da919596a1e19511ee9ede;
                10'd18: dout0 <= 128'h9de159111995e21a691ea659a591e111;
                10'd19: dout0 <= 128'h9e519e191156e1195ed62d5911111696;
                10'd20: dout0 <= 128'h1ad5e5e91e159221116e16969151ceee;
                10'd21: dout0 <= 128'h1e9ee51915a9e591e11916a165d9a9ee;
                10'd22: dout0 <= 128'h959ce55599199e1eae11e31116e569d1;
                10'd23: dout0 <= 128'he9e19e51695ae91ee9e96e9e51691e61;
                10'd24: dout0 <= 128'h1eae951115519eeee15d29a11996ee11;
                10'd25: dout0 <= 128'h3319a95119919e91991ee16151151dce;
                10'd26: dout0 <= 128'he616ee5e991ea5999115a561e199e1e1;
                10'd27: dout0 <= 128'h11e919956ee11e5eea611eeee11e6169;
                10'd28: dout0 <= 128'h1991d669e15ee9e515ee9196a215a291;
                10'd29: dout0 <= 128'h6651e1eee63a119e1115611e1a95e1e9;
                10'd30: dout0 <= 128'h5eece19e59119911519163aa9a1e9151;
                10'd31: dout0 <= 128'h6e1e165999e9e15519ee5199ce19315e;
                10'd32: dout0 <= 128'hee1ea599ee19659d599d9e69626ee969;
                10'd33: dout0 <= 128'h1e151199161961911e59e395e9593965;
                10'd34: dout0 <= 128'h9e6a5ea22669d59ddaa2311eab6e133b;
                10'd35: dout0 <= 128'h1e699ee6a1e695a53a6ad9a269ced5eb;
                10'd36: dout0 <= 128'h9e11dea65926e9975eae39192d1151e5;
                10'd37: dout0 <= 128'hee65791a1421a2dbdc12d1644311752b;
                10'd38: dout0 <= 128'hd29e7e16a225a2df9c9c99d6cd9ddded;
                10'd39: dout0 <= 128'ha69b9651a4caa65716b0b979a5e219eb;
                10'd40: dout0 <= 128'ha22be9dca6ae8efb1c92d9b14d1ed5c3;
                10'd41: dout0 <= 128'hcca3d9d62c6ec2ff94d431b123e95daf;
                10'd42: dout0 <= 128'h66e1a123a2cbd3efcaa2639196c65da5;
                10'd43: dout0 <= 128'h9ce72dab294257ef2a669d36d1a2e569;
                10'd44: dout0 <= 128'h14ebada3ce401ec396b9fd56db5c23d3;
                10'd45: dout0 <= 128'h9a176e952aace19d1cde5e729bbc615b;
                10'd46: dout0 <= 128'hea93791e2269e637bc6edeea6b6db5af;
                10'd47: dout0 <= 128'h1ee3d1a6caa6aed9faacb11ae72ed92d;
                10'd48: dout0 <= 128'h5e1d5ee662aea613dca4be12a566d56b;
                10'd49: dout0 <= 128'h1615d1e6161615dd565ab962a5119de3;
                10'd50: dout0 <= 128'h11e9dee629eea6511a61559aebae5995;
                10'd51: dout0 <= 128'h3961151e1115919e96e995ae5969e1e9;
                10'd52: dout0 <= 128'h1e1e1599d16959999661e1199661e1a9;
                10'd53: dout0 <= 128'h115d6a1e1991965e115959e61e111699;
                10'd54: dout0 <= 128'h1596d51e1a5e11991e515551eeee1119;
                10'd55: dout0 <= 128'h916ae1e16a61999e6a651566a9161666;
                10'd56: dout0 <= 128'h19e9691593e161919199ee1996e1565e;
                10'd57: dout0 <= 128'heee16e131aed5169111966ee1951511a;
                10'd58: dout0 <= 128'h56e9ee919ee9919916551ae559a5ee9d;
                10'd59: dout0 <= 128'h61d3a51bc8e1e666c2beb97c1e3ea91b;
                10'd60: dout0 <= 128'h965f56b5a69daee3ecd1d6baeef2edab;
                10'd61: dout0 <= 128'h6eee5ee15e1ee1e9eeaa15166519d567;
                10'd62: dout0 <= 128'h5e113e66646e61e5526c99d923c555eb;
                10'd63: dout0 <= 128'h1ce52ed9cce6e5f632ea79912be29d53;
                10'd64: dout0 <= 128'h161de166ac119939b4ee7b558f211317;
                10'd65: dout0 <= 128'hf26e4d68b6ec3b64fe5affc72f0e2fbe;
                10'd66: dout0 <= 128'hfc236ea0d8405f2af5e8ffc96f829d39;
                10'd67: dout0 <= 128'h36a336a0d108e3e9f8ecff9eaf2a736f;
                10'd68: dout0 <= 128'hd12191e81d0c53563e5ab515edae55e9;
                10'd69: dout0 <= 128'h16a6c295692157e919503f1119897ee6;
                10'd70: dout0 <= 128'h81269212cdcae5637a90dfc19b0975a3;
                10'd71: dout0 <= 128'h03695ed6550a5bcdec605faddf8ebde3;
                10'd72: dout0 <= 128'h039d5166ed025d67aac0171a59aab11d;
                10'd73: dout0 <= 128'h8d1d3e20170d99a7eaa469aaa5e919d5;
                10'd74: dout0 <= 128'h4efe5ae467ca9d3f126a19c141e56e93;
                10'd75: dout0 <= 128'h40f3dee0ea1b59df12461301218e9561;
                10'd76: dout0 <= 128'he8b5ee14e59ad5799626532a1a4ee591;
                10'd77: dout0 <= 128'hde99e5e41522d1f9bee4fdce1316db55;
                10'd78: dout0 <= 128'h1a911a10191aa5f31cd1f5ace9acdb9b;
                10'd79: dout0 <= 128'h661d51a219e091b3d4eef19c6dec5be9;
                10'd80: dout0 <= 128'h6ee92556d5e699697936b31513ca5bd6;
                10'd81: dout0 <= 128'h99964e51d9e655ee5a157da3e36e1316;
                10'd82: dout0 <= 128'h99e61e1599169119ae9e193e699e5e91;
                10'd83: dout0 <= 128'h99eee6edee96591e1561ee15eee516e5;
                10'd84: dout0 <= 128'he1199e1d9d56e6195e5e915a9aea1991;
                10'd85: dout0 <= 128'h6661596a55a96ebdee111999e9666e91;
                10'd86: dout0 <= 128'h1ed1293169ee1ea1e695d99913619991;
                10'd87: dout0 <= 128'h961f91916c91e9a99c52517223541923;
                10'd88: dout0 <= 128'he2ed11d641166e391a1add5a56a935e5;
                10'd89: dout0 <= 128'h599d992e3161ea9c66edb36513d13c65;
                10'd90: dout0 <= 128'h1ad139cc296e5e1ed8c37762eb267e1d;
                10'd91: dout0 <= 128'h1469d32c26216565e49973e8dbd2b9e7;
                10'd92: dout0 <= 128'h7c69d3682e82991ebe2b716e559c5353;
                10'd93: dout0 <= 128'h76cd59ca29ac53a99edd3153c51e17bd;
                10'd94: dout0 <= 128'hb9a56160a124392116edda1991ee63dd;
                10'd95: dout0 <= 128'h519dee1ca508ae5a9e9375ee51199593;
                10'd96: dout0 <= 128'h1a3dd66e210cbece9619d5259191e591;
                10'd97: dout0 <= 128'h0ead5e661c0a7dadd4e1915115256999;
                10'd98: dout0 <= 128'h0d1bda56be0a5e1e115a39552911e119;
                10'd99: dout0 <= 128'h0d63da115ea213e111dee5a221911651;
                10'd100: dout0 <= 128'h0d131eb1d14a59a1119add2aa99e12dd;
                10'd101: dout0 <= 128'h8fd5a65ee1a1511919911366a9e66add;
                10'd102: dout0 <= 128'h0dd9d15dee66de1d5a6e5b21ca911d19;
                10'd103: dout0 <= 128'h615d395cee1e919b92a15d2a41a9171d;
                10'd104: dout0 <= 128'h921556ea1d51dad529155514c1de9669;
                10'd105: dout0 <= 128'hac5e3664ddda99ebd65955aca163e995;
                10'd106: dout0 <= 128'h12ecfb94395515933c6719ea8d1991eb;
                10'd107: dout0 <= 128'hca16534631199eb3306d5ee615ed9a6d;
                10'd108: dout0 <= 128'h2a5711aaf9112e9358175366a316d359;
                10'd109: dout0 <= 128'hca671913111b5813a6156215edb5a1de;
                10'd110: dout0 <= 128'h225151cee1a5e21bacae529c69336539;
                10'd111: dout0 <= 128'h912e5e661e9119e951e151e1e1ee19ae;
                10'd112: dout0 <= 128'h1551d111ae9191115eae1e95e91593de;
                10'd113: dout0 <= 128'heee199296569513915911511521999a6;
                10'd114: dout0 <= 128'hed1511aea959e69aada5d916ea199aea;
                10'd115: dout0 <= 128'hd57fd1aeeae6661ad527351a959cba43;
                10'd116: dout0 <= 128'h3a3c9d68616a865611e9922476a1f161;
                10'd117: dout0 <= 128'h59e7c142615c77e69e253386b5a2b212;
                10'd118: dout0 <= 128'ha96e69e0cd5e5fa6d59e3dc11d66d13c;
                10'd119: dout0 <= 128'hd56991e843a6e3ce5dd53eae1e9ed27e;
                10'd120: dout0 <= 128'hdae755428dc49f8996659126d91e31d9;
                10'd121: dout0 <= 128'h9667194a81a69da19c15e1d9eda9adf1;
                10'd122: dout0 <= 128'h291dd1aa09c033ae191511855991de79;
                10'd123: dout0 <= 128'h5155ee5e26c83191ee15d18996116133;
                10'd124: dout0 <= 128'h29d111eaa56cd5aee1911ec919ed599a;
                10'd125: dout0 <= 128'h01ade11169e9951e6de55169911aba1a;
                10'd126: dout0 <= 128'h09a9736e25aee11165611ee55d161ad9;
                10'd127: dout0 <= 128'h45d1d55ee1e63e692e5191e15e1ea1de;
                10'd128: dout0 <= 128'hc99196a5e1a1bd559131b1a1e9eea111;
                10'd129: dout0 <= 128'h6d919a3e612519d69ee65111a6e6a155;
                10'd130: dout0 <= 128'h95153e3e9e6eb96de5dedaee629a6559;
                10'd131: dout0 <= 128'hd115de6aae66ed5ea9561961ca6e199e;
                10'd132: dout0 <= 128'h5d669a11a5a11993959369a10a6e919d;
                10'd133: dout0 <= 128'h66b219995d5aeadba9d1c12c095d61a6;
                10'd134: dout0 <= 128'h2e51179d516e6131617561cc8e1de116;
                10'd135: dout0 <= 128'h64fc39e8d359293b1a1d662a6eef91a5;
                10'd136: dout0 <= 128'ha498b52adfe9601dae9fe0e616ffa196;
                10'd137: dout0 <= 128'h827a7111ed3698e315b96c15a3ffee92;
                10'd138: dout0 <= 128'h463e91cee9ec3a9f95936a1a155366dd;
                10'd139: dout0 <= 128'h2e5e9161695261317c9ed52211be9b2d;
                10'd140: dout0 <= 128'h1d9e9e9991e9a9e6151ea69e6d9e9e15;
                10'd141: dout0 <= 128'he115611e6ded9d119e599511e1191e16;
                10'd142: dout0 <= 128'h9d599e2e26e3596916ad5316dda2d1d9;
                10'd143: dout0 <= 128'hed9b1dd22cd63da4279fdd91d1d8199c;
                10'd144: dout0 <= 128'h31e513640ea6e3c0d961d9127e527c63;
                10'd145: dout0 <= 128'hb15ac1ad61b6f95561a965161e2e9864;
                10'd146: dout0 <= 128'hd596cde615567152611d5d11951eb49e;
                10'd147: dout0 <= 128'hd11655111169b51a55e5e6ae59d1da95;
                10'd148: dout0 <= 128'hea562a66356cd616959ea6c615551d69;
                10'd149: dout0 <= 128'h563669191b225116e1916dee131eed16;
                10'd150: dout0 <= 128'h1195155aa5241a15e19d158a9d115199;
                10'd151: dout0 <= 128'h5a95e91e61eaeae13199eeee99156cb9;
                10'd152: dout0 <= 128'h269159d92ee65996199d5661d3d3315a;
                10'd153: dout0 <= 128'h2111119de1e95a1ee6616e6515dea951;
                10'd154: dout0 <= 128'ha9699d95696551119199e92e95161655;
                10'd155: dout0 <= 128'h1ae5e11d6111e696ee1119ee51ea1a91;
                10'd156: dout0 <= 128'ha99a1e59a919d5a59995d32eae9a6991;
                10'd157: dout0 <= 128'h65995a1169ee669511e1166549519139;
                10'd158: dout0 <= 128'h1919ea51e9e69115d195d9a11c115516;
                10'd159: dout0 <= 128'h2d99e656e1a69d51169e56c6229eade9;
                10'd160: dout0 <= 128'h691e3a9e9961192151d3562eca1e1959;
                10'd161: dout0 <= 128'he91e553969ea15131635ee2902a11556;
                10'd162: dout0 <= 128'h913e1e9926e2dd29a95ee6a141a1a952;
                10'd163: dout0 <= 128'hd296931c696d13ebee36e9826eaad66c;
                10'd164: dout0 <= 128'h11ee3542996a65f96e95a92e16a596ae;
                10'd165: dout0 <= 128'h8ab935066eb9326b52bdda5696bf6117;
                10'd166: dout0 <= 128'h2ea1b1aeac522e9552d1d16a9535d393;
                10'd167: dout0 <= 128'ha22ed166665eee593091db4619e5ddad;
                10'd168: dout0 <= 128'h9e19e11a9e9919161611d15ad9e1e616;
                10'd169: dout0 <= 128'h6699e5969652e365ede355a65e1a9191;
                10'd170: dout0 <= 128'h16de65d559e1d41a1559a21196b1a1e6;
                10'd171: dout0 <= 128'h5fa3295e517a9da86fede9d6d25e3eec;
                10'd172: dout0 <= 128'h3959e9eec9ad616e155569da91d9d469;
                10'd173: dout0 <= 128'hda61191ee513ba5e295199321159e621;
                10'd174: dout0 <= 128'h9d5569a5659553915e9e913959b96625;
                10'd175: dout0 <= 128'hee1e16969192565e66e9119a55511961;
                10'd176: dout0 <= 128'h611115ea55d0165199631e295dd3e5e9;
                10'd177: dout0 <= 128'hd91e31ea3154d29911a5e5ae53d11e6a;
                10'd178: dout0 <= 128'h35de19d55e16d696e52b19e16969a553;
                10'd179: dout0 <= 128'h1e5e11e53e316e19e6e1e911559565b1;
                10'd180: dout0 <= 128'h6291159591e95691999d9ea1e515e591;
                10'd181: dout0 <= 128'ha59e119366ae996e19e759e69d151559;
                10'd182: dout0 <= 128'h1199e9d591931e15999be99e9359695e;
                10'd183: dout0 <= 128'heeaa11156611a6edd1631de9e916aade;
                10'd184: dout0 <= 128'he9e1e611da66e955de13d5c15d91e69e;
                10'd185: dout0 <= 128'h1e19acd391916115d96dd5956a962a31;
                10'd186: dout0 <= 128'he515a6e95999a5e596ed3195e6e9e992;
                10'd187: dout0 <= 128'h5ee11e91691e151d151152e6ce96c6da;
                10'd188: dout0 <= 128'h9d1e9ad9ee6911e9a9a9dae12269ae5a;
                10'd189: dout0 <= 128'h69a5aa931c59e955ee9555e162b66ee2;
                10'd190: dout0 <= 128'h1e516166aa19915ba5dad9de0a95919e;
                10'd191: dout0 <= 128'h12ee17c9e561965315d9162612dd363a;
                10'd192: dout0 <= 128'h9ce67ec4a495eeaf6566e1885693d1ec;
                10'd193: dout0 <= 128'hcdd6f1812e3e5e2f5cc46eae5a1f2651;
                10'd194: dout0 <= 128'hae59b66262da661f519a169e96d7551e;
                10'd195: dout0 <= 128'h6d96dee6e13215edd21dd56e596ed1ad;
                10'd196: dout0 <= 128'h16e91191199e199936e9999161e5d5ae;
                10'd197: dout0 <= 128'hce5d11c536b0fe6a97933d58567ea5ea;
                10'd198: dout0 <= 128'h3e91ae5d3df6541c9599c95d5db1692a;
                10'd199: dout0 <= 128'h6da32dd1535a55aca36969b8de5a3e6e;
                10'd200: dout0 <= 128'h9d199961e1e6f36ad156db513ae2b66d;
                10'd201: dout0 <= 128'hc9d556e2a35bd2aeed163152e155d69d;
                10'd202: dout0 <= 128'h41e19e9955d1e9aae3edaad6995e26ae;
                10'd203: dout0 <= 128'h1e695921d6e0e6e1adea5dd1e9a9e9ae;
                10'd204: dout0 <= 128'h211156169ddca11eeb659e1615e9e596;
                10'd205: dout0 <= 128'he15e51e99dba9a59195e769999d563ae;
                10'd206: dout0 <= 128'h915e16911d52e1152595ed5e9de1a619;
                10'd207: dout0 <= 128'he9191191e2916659699d159e9d65e31d;
                10'd208: dout0 <= 128'he65665995995dee9911bc9d65deea991;
                10'd209: dout0 <= 128'h61ea9311dee916115193195eb31ea516;
                10'd210: dout0 <= 128'he2a1e99eaaed1be3952f991e1566ee15;
                10'd211: dout0 <= 128'h16e1e91159e9655956ab915e5dd9a19e;
                10'd212: dout0 <= 128'hd95d6e111de51597191d99d5d51da5de;
                10'd213: dout0 <= 128'h55691e1de99961e511151dd51e51a5e6;
                10'd214: dout0 <= 128'h1dedcee319e69937e6d5de9966116d1a;
                10'd215: dout0 <= 128'h5d15695d6559115f516ede19a65ea19e;
                10'd216: dout0 <= 128'hd555ae65e2ed5e5b99169d112e1529e2;
                10'd217: dout0 <= 128'hee19a996e5591d539e9a9d99c2ad2516;
                10'd218: dout0 <= 128'h1ae96e93e3e5d99d9d5891916615ad1e;
                10'd219: dout0 <= 128'h98e1e12d22e59e952310e9de22991ee9;
                10'd220: dout0 <= 128'h801116111a111ae31d5016ea60d57eae;
                10'd221: dout0 <= 128'h2c5ad612611ae62355b894e5e83d1eb1;
                10'd222: dout0 <= 128'h5656de60e1393eef6d36699c2937999a;
                10'd223: dout0 <= 128'h6511de6191fccdd5d41ddb165ea6756d;
                10'd224: dout0 <= 128'h16e5e916e961165e5ee5511966166e65;
                10'd225: dout0 <= 128'h5c1e4113be78786193495d328911c1ae;
                10'd226: dout0 <= 128'ha1d9191559e63c322fed211992315e4a;
                10'd227: dout0 <= 128'ha599e96bad91b16aa1a6b1525ed1d15e;
                10'd228: dout0 <= 128'h259a23ae5596592c9556ddaa9dee7a69;
                10'd229: dout0 <= 128'haed6e451ed9e6ae115261998661e59e5;
                10'd230: dout0 <= 128'h2ee2e2eb99d1daeee5169a9e19911a19;
                10'd231: dout0 <= 128'h2e16eda91dd63ee1abe93d1eee19919d;
                10'd232: dout0 <= 128'ha6e515e999de6ad191211e9a15132d15;
                10'd233: dout0 <= 128'h6e9ee99e139a14596399111911a165e3;
                10'd234: dout0 <= 128'he6ee11e999da5e6e5ee9911115e1a569;
                10'd235: dout0 <= 128'hae12111e911e16e5199115e66115a9ae;
                10'd236: dout0 <= 128'h161515199639de9e9919a93116116b95;
                10'd237: dout0 <= 128'h49a655a9129d51d5e91ded3d591ec91d;
                10'd238: dout0 <= 128'h8699a9196e931e91ee6be59a9be1ed9e;
                10'd239: dout0 <= 128'hec6de5d1199955e91519e5793c3e6e1a;
                10'd240: dout0 <= 128'h16e19699e15eae115119ed76da5e6156;
                10'd241: dout0 <= 128'h5d59e895619191e5195e353591911ee6;
                10'd242: dout0 <= 128'hebd61e1b1e659e1ea5e1517e621d2596;
                10'd243: dout0 <= 128'h93e6125a5e995d1199e6bed9611e2391;
                10'd244: dout0 <= 128'h1d1196d961511e1e1616d15e865e69e5;
                10'd245: dout0 <= 128'h6169565e5663e199e3eee1164a19a551;
                10'd246: dout0 <= 128'h9a3ea96dee55bd5e1d92b199aad16be2;
                10'd247: dout0 <= 128'ha0ea1eadc66199a613a01a9e86e3e9ee;
                10'd248: dout0 <= 128'ha01a1eea1e6b506ca990c0b1807761d4;
                10'd249: dout0 <= 128'h605a7e6ae5edd26a2d70209e607feedc;
                10'd250: dout0 <= 128'h591abd6aa1d9fbe195e2a25d14d7193a;
                10'd251: dout0 <= 128'heeeab9c9aee1b1699ca1e6516a39c139;
                10'd252: dout0 <= 128'h96e559e19d165e9515155511e15e11e5;
                10'd253: dout0 <= 128'h149e095fb3fa3c1933ee5bb241b5c912;
                10'd254: dout0 <= 128'ha5d6ee69ed1abe5e2ba6d991e2d29d91;
                10'd255: dout0 <= 128'h69b1ae1d6954f641de957793e269235b;
                10'd256: dout0 <= 128'haed1a965e9ee515c99915e121e32da61;
                10'd257: dout0 <= 128'h1e6eee115954eac4159962dc6999e6ee;
                10'd258: dout0 <= 128'h2e96e55de6509ade9963e1169ad9689d;
                10'd259: dout0 <= 128'h66d9e99119325eeeeea5695a9165a993;
                10'd260: dout0 <= 128'he966555199bed691e32365e2e6692515;
                10'd261: dout0 <= 128'h615e5999993ee69e9195a91e95e1e999;
                10'd262: dout0 <= 128'hee115eda3956ae51eee5e1d69e9ac9ed;
                10'd263: dout0 <= 128'h66e216de513195e59161aedeee9ee969;
                10'd264: dout0 <= 128'h419e1ae1523d511111519a1e199aa3a9;
                10'd265: dout0 <= 128'h0a19e5111c333e5a9666a1333195959e;
                10'd266: dout0 <= 128'hc421eea9603d395ceaeeee5ebe16ada2;
                10'd267: dout0 <= 128'h56e596999e995d9291111159b69151e2;
                10'd268: dout0 <= 128'hb55992916e161918611eded5b619e5e6;
                10'd269: dout0 <= 128'hbbae9ae9115ed1e0e9e92ed966562916;
                10'd270: dout0 <= 128'h339ea6b2113192e0e11e9a31a9d61ed9;
                10'd271: dout0 <= 128'h9315e99de599199091553a5e2261ed9e;
                10'd272: dout0 <= 128'h11961e5ee99e9a101de63691a6de6996;
                10'd273: dout0 <= 128'h59e61515e9ee1690116ed6954ade5e19;
                10'd274: dout0 <= 128'hace55ea9ea11516093ae96ee251e91e2;
                10'd275: dout0 <= 128'h04a9e6591a999d2019ecbc194e39951e;
                10'd276: dout0 <= 128'he0e196e5961392c0e0b220b522b71d1e;
                10'd277: dout0 <= 128'hc496b6156415ba16121220fa9cf72dd4;
                10'd278: dout0 <= 128'h9e165689e9c6fe15eaecc9de91e3ca50;
                10'd279: dout0 <= 128'hbadd2123dadb5a454ca9a970d5e82524;
                10'd280: dout0 <= 128'hd959e111599115eb215619996611e166;
                10'd281: dout0 <= 128'he222c51bfdde9ce599911d362193956e;
                10'd282: dout0 <= 128'hdc55cd35139ad2ee456a53b2ac1ae741;
                10'd283: dout0 <= 128'hab7d2151619c99269331fc193ad2a3ea;
                10'd284: dout0 <= 128'h629a11a92936de5161a18ad9ea911611;
                10'd285: dout0 <= 128'he266a31a55d6ec461595e4e69911e131;
                10'd286: dout0 <= 128'haaae5596d630d1161e1de5ea11d129d1;
                10'd287: dout0 <= 128'heeee555d5e9ae6a5e2ee939a1ae1391d;
                10'd288: dout0 <= 128'h915aee96edda16a5de551eea61196695;
                10'd289: dout0 <= 128'h62116a9955dc9691ea66691a6299a165;
                10'd290: dout0 <= 128'haa5692a2dd3a1e6ea451629692ed2de9;
                10'd291: dout0 <= 128'h899614e99d3955615c1aec56e661e5e6;
                10'd292: dout0 <= 128'h0e111a99dadd6eeeae9a6a1d90191319;
                10'd293: dout0 <= 128'h82ee1161587dd99e1eac6a3e5cd697a1;
                10'd294: dout0 <= 128'hae61e5c5983dee9199a21efdd4955111;
                10'd295: dout0 <= 128'hf9a65d19d995a96c61a2e9de329e5956;
                10'd296: dout0 <= 128'hb7659e95939aaee0a69d15b991e991e1;
                10'd297: dout0 <= 128'h936eecde659a51e025156dd11e969de9;
                10'd298: dout0 <= 128'hb3a69151e16ad6b0699b6e3ea9a6e5e1;
                10'd299: dout0 <= 128'h7d2e911e59e6916013ad9a55a259e51e;
                10'd300: dout0 <= 128'h7965199d911619105b1116d9ac995119;
                10'd301: dout0 <= 128'h989a6165951e596069e6da19a19ea999;
                10'd302: dout0 <= 128'h906521ed11e91390edadde9ea6d59d5a;
                10'd303: dout0 <= 128'h60ae16e56a616a90d6d5fae5ab39a196;
                10'd304: dout0 <= 128'h30e5521ce9e5a240aa58ec562e736d35;
                10'd305: dout0 <= 128'h7e5a53eeba6f36aacbab0a1a625ec118;
                10'd306: dout0 <= 128'hbedd3ec6e4357e8324c98df89152a5d0;
                10'd307: dout0 <= 128'hf15e251bd515b6230eaeeb3cd36219e4;
                10'd308: dout0 <= 128'h1ee9999519d69cada9a61915a99199e6;
                10'd309: dout0 <= 128'h9666aaa51bf1da11c99ae95129ca1966;
                10'd310: dout0 <= 128'h3c610a27b6bd3e1ea6edea3e1861e8ca;
                10'd311: dout0 <= 128'h95cec94512a612ee6f994a95f2fa666a;
                10'd312: dout0 <= 128'hba6aee81e9be51231ae562e69a556d9e;
                10'd313: dout0 <= 128'h5e111e11693a5921da664c2e9965e99a;
                10'd314: dout0 <= 128'h661e56799eb06e191e5da66a6a13ede9;
                10'd315: dout0 <= 128'h1115e91d59915e1a1ed912961c1b6aad;
                10'd316: dout0 <= 128'ha1d11ae9d19e9616e211129e969361c5;
                10'd317: dout0 <= 128'ha61e12519d1aeea1921ea226ec131619;
                10'd318: dout0 <= 128'hc919ee995d91ee516661a2e11c991929;
                10'd319: dout0 <= 128'ha21de11d1d31a56a969ea45914d19661;
                10'd320: dout0 <= 128'h66119625555d66961eece86594553e11;
                10'd321: dout0 <= 128'h1a1db92554db91d5e64ed1edb45dba11;
                10'd322: dout0 <= 128'h19eedecfd2e5ee39d61e9d5132edd651;
                10'd323: dout0 <= 128'hb551d32996e91e51e1a6e59956955c14;
                10'd324: dout0 <= 128'hdbe6de1551e6a5dea169211ee51951ea;
                10'd325: dout0 <= 128'h5b93e65dd99666d1eedd6aeea9196999;
                10'd326: dout0 <= 128'hdde99215de52a3566d99a26669911d1e;
                10'd327: dout0 <= 128'hd3a151915d1e69e05d95969569961915;
                10'd328: dout0 <= 128'h369e169d1eece95099c999199e526e59;
                10'd329: dout0 <= 128'h706dae5519eee5d0d6a631e19521e111;
                10'd330: dout0 <= 128'h90ae21e76e625e509615963ae511dee1;
                10'd331: dout0 <= 128'hdc996e55e11962005a995a31855baab5;
                10'd332: dout0 <= 128'h119252936d1aa00014965479053722dd;
                10'd333: dout0 <= 128'hb59233e6399d9e081e352851213126f1;
                10'd334: dout0 <= 128'h5358f9e306fa169d1c1b04fda0f383f9;
                10'd335: dout0 <= 128'hba5d99631c9c11494aa2ed949a9a9da6;
                10'd336: dout0 <= 128'he9d111e159e16aeae169d6699ee51e2e;
                10'd337: dout0 <= 128'h3c2621a3b7f15a116d11663699ae11ce;
                10'd338: dout0 <= 128'h3aee09257e9991969265c4d9e66ba6cc;
                10'd339: dout0 <= 128'hf58a296d6b92e2ee61318e67d673a1e5;
                10'd340: dout0 <= 128'h3016111d5296eb8d5a154c15d6ae4196;
                10'd341: dout0 <= 128'h1aa11113955c9e29566ea21e169daed1;
                10'd342: dout0 <= 128'hce9d915959ec1aee5ee12016ee159e6d;
                10'd343: dout0 <= 128'h1e9eee69de1999e16c5120e1ea9b99e1;
                10'd344: dout0 <= 128'h5a15eed69999611119eaa81e62e3de11;
                10'd345: dout0 <= 128'hd1991519dd9e6e9eee1620919ce59de5;
                10'd346: dout0 <= 128'h619991e695dd2d1ae56ee49a6cdd7e69;
                10'd347: dout0 <= 128'ha5d51ae693d5495969ee94da1a15b69d;
                10'd348: dout0 <= 128'h5559dae96bd3e131e99a56d99c917e96;
                10'd349: dout0 <= 128'h955139a91e6d6e5111e65e1954993231;
                10'd350: dout0 <= 128'hd19956c35c6de9596aa99be5d1e6d031;
                10'd351: dout0 <= 128'hdd6191a5d191a9b16e611e1e15951c16;
                10'd352: dout0 <= 128'hdd5916c9d1ee16959621aa251111d21e;
                10'd353: dout0 <= 128'h1be111e11e9ea135e6ee521e5b99aa19;
                10'd354: dout0 <= 128'h9ee51695519a1e5de1a9aeee591a5ee1;
                10'd355: dout0 <= 128'h5e6199595de6eba6d5e5c69519319199;
                10'd356: dout0 <= 128'hdcbeaa999eae11965d1de961ee9d9691;
                10'd357: dout0 <= 128'hd0519ee395aca912915e916b66afde5d;
                10'd358: dout0 <= 128'he03dae1915622238da1e15de59a136ce;
                10'd359: dout0 <= 128'h1e76e45d26a4ac90d059925d65ad5463;
                10'd360: dout0 <= 128'he5ece1958f821c80a1d4d69a0e63daab;
                10'd361: dout0 <= 128'h359c262695d6e10cee92659a21162d1a;
                10'd362: dout0 <= 128'hf362eec7923c318d26292aeaced54d32;
                10'd363: dout0 <= 128'hfce529633c663aad12a11f5a59ea6526;
                10'd364: dout0 <= 128'h9e59166e6569ed1eeae219659ee16eed;
                10'd365: dout0 <= 128'h9e99a19d65e19a51615a165e611199ee;
                10'd366: dout0 <= 128'hf2ac0a2fbdd5922e2e2dce31c191d94c;
                10'd367: dout0 <= 128'h792e23a3e66cc14566dbe51e99316196;
                10'd368: dout0 <= 128'hba556edd5e2c0125aa15e06d166148e9;
                10'd369: dout0 <= 128'hd6d961ed11a242a19e92a06ee297dae9;
                10'd370: dout0 <= 128'h1a9369ed11ea2de1eee250ed9655d52f;
                10'd371: dout0 <= 128'h5115119e39e92e959156e099541bd191;
                10'd372: dout0 <= 128'h59db92e9d9e11531ee59a09ddc5db995;
                10'd373: dout0 <= 128'h1195911161ae211ae196d8ee161bb95d;
                10'd374: dout0 <= 128'ha91dd6963e11461ea9de5a5e1253d666;
                10'd375: dout0 <= 128'h1e595615e3e5e5d1ed919e116c95be19;
                10'd376: dout0 <= 128'hd99d3ee69123663e153e99e55e61de71;
                10'd377: dout0 <= 128'h139976a19ecd915e9ee933ed599e52b6;
                10'd378: dout0 <= 128'h3d9659c5526196915961ed19dd5666d6;
                10'd379: dout0 <= 128'h1316d9c991e56655912ea529d16352e1;
                10'd380: dout0 <= 128'h9556e66156ee1976e96e29199551d861;
                10'd381: dout0 <= 128'h9e91aaae59955b911599a165fee59295;
                10'd382: dout0 <= 128'h99e51e5d151e19d51d59e6e951599a15;
                10'd383: dout0 <= 128'h661119e5ed26c9d7931e11a5599a9491;
                10'd384: dout0 <= 128'h6e115de99d596a5599e961ade1b919d1;
                10'd385: dout0 <= 128'he4d9651d93666cd1d619a51961d9d125;
                10'd386: dout0 <= 128'hea5919d9a568a696d4591e19e6635eab;
                10'd387: dout0 <= 128'h6639199921c0e4cad89c516aa9193cc7;
                10'd388: dout0 <= 128'ha136eae1ae601482d1ea1b14a56e92a9;
                10'd389: dout0 <= 128'h5564aa9da9e09548159c9dde291ae129;
                10'd390: dout0 <= 128'h9d04a9a16d14bda9ebde1dc5ae24c35c;
                10'd391: dout0 <= 128'h9b65e963ae96e9e1be3dd9e365292156;
                10'd392: dout0 <= 128'h9c55d9eea613142d621ee3d1a656d3dd;
                10'd393: dout0 <= 128'hb169e1e59259d13dcb259511e2711ace;
                10'd394: dout0 <= 128'h32424d8fd9be5e150aee1e7eceacdd8c;
                10'd395: dout0 <= 128'hf1a1ede95edaad2ae9911163da9a5914;
                10'd396: dout0 <= 128'h3df126d536a8cec1e191a441a692ea16;
                10'd397: dout0 <= 128'hddb569e5672a8aaa6152d0114215d19e;
                10'd398: dout0 <= 128'hae33155119ac8589519a5a556963dae9;
                10'd399: dout0 <= 128'h1159a9dd13a98149e55e5a1d1e9b5165;
                10'd400: dout0 <= 128'h999561e59dad45e165965615e9195e61;
                10'd401: dout0 <= 128'h1dd16699e9e9c191659a3e11919951e9;
                10'd402: dout0 <= 128'hea9e91ed1569aa559111551ead19bd1e;
                10'd403: dout0 <= 128'h9e9915211de16ede55399515ede99a69;
                10'd404: dout0 <= 128'h5ed119eca621e63995995fea96e11259;
                10'd405: dout0 <= 128'h11e13a6e9eade1de95995bed5513aa9e;
                10'd406: dout0 <= 128'h551e56a9eeee39e9516e91a9531ed251;
                10'd407: dout0 <= 128'ha159dea99ee1999193ce615e95a59a55;
                10'd408: dout0 <= 128'h695e9e6e9e55131999a12e6d55191669;
                10'd409: dout0 <= 128'h15ee5ae939d19e511b1a61e9565b16e9;
                10'd410: dout0 <= 128'ha15e6e11dd51a1e5955d191151b11ae9;
                10'd411: dout0 <= 128'hdee16e19ed91e1951bea653515591615;
                10'd412: dout0 <= 128'he1e12359b5d31aa3ded5e9696adaa661;
                10'd413: dout0 <= 128'hc5ed65151d1a9a959e5de361ea9156e9;
                10'd414: dout0 <= 128'he559e5d6571ca267d159e111696d96c9;
                10'd415: dout0 <= 128'h61392e53651660c566bd959a19aa1c23;
                10'd416: dout0 <= 128'h1ed36e912191628ea55ae9d16956eaad;
                10'd417: dout0 <= 128'hef212ae9adbc118ed3fc116f19a1ea65;
                10'd418: dout0 <= 128'heb4dce559d727b0af33a331f2504c93c;
                10'd419: dout0 <= 128'h9391a19599395522db5e9b1d9d4ac596;
                10'd420: dout0 <= 128'h511ed6a165d91e6d61ea53de45e155b9;
                10'd421: dout0 <= 128'h5d3669a56a1eda55ada9591e91d91a69;
                10'd422: dout0 <= 128'h9912550221d973ec455a161996e4b126;
                10'd423: dout0 <= 128'h132ce1ee511e61e4a9311daf35a93d94;
                10'd424: dout0 <= 128'hebd36a5e596d26acab5e161166e12eea;
                10'd425: dout0 <= 128'h699d2ee111612e46631cded52959396e;
                10'd426: dout0 <= 128'heddd61e1d925c98e5e6619112b559e65;
                10'd427: dout0 <= 128'hb1e9135d5742aeaeae52195919b156e9;
                10'd428: dout0 <= 128'h9956919d11ce496e1651dd93115151e5;
                10'd429: dout0 <= 128'hde7a951d1d2ead39e95c5b15e5ed5ea1;
                10'd430: dout0 <= 128'hd6be11153dc91c56d936e35115e9e11e;
                10'd431: dout0 <= 128'he191d165de2129ded33a5b691e969119;
                10'd432: dout0 <= 128'h16de3a1a1aa91ad93551179551995199;
                10'd433: dout0 <= 128'h11119969e6e1715eb11e1b6591699631;
                10'd434: dout0 <= 128'h1d1e3ec161953dde1995196e5ded9c91;
                10'd435: dout0 <= 128'h955aeaae5e1596191d5edea151155caa;
                10'd436: dout0 <= 128'h55ee92a19d139591dd111165d9195a11;
                10'd437: dout0 <= 128'h1e9ece1299e59ed9556695653e5d5ce5;
                10'd438: dout0 <= 128'h1a11e6d911d5e6e95995a116c93696ee;
                10'd439: dout0 <= 128'h911395d3b791d45935d195e919315499;
                10'd440: dout0 <= 128'hdd1369dd56e11a11d65e6ee9965696a9;
                10'd441: dout0 <= 128'h111d155553e9ece9511d95ec619e91a9;
                10'd442: dout0 <= 128'hade1a155bd51e42ee9555e6a5e5992ed;
                10'd443: dout0 <= 128'h8596e69161e3982ea157599a55d99cad;
                10'd444: dout0 <= 128'h21d39ee5c6de1e09a1de5b75e79a6a95;
                10'd445: dout0 <= 128'h6d6e929ea95a2e259978e9674989e69b;
                10'd446: dout0 <= 128'h5f5b66729dbaddc86b7c592b55e82d64;
                10'd447: dout0 <= 128'h2fa16619d3d2d5e6d3595d35c51a6539;
                10'd448: dout0 <= 128'h1daa6a15de39e1de116e5111395396ea;
                10'd449: dout0 <= 128'h1395ee2311115951e1a3dd665e5959e6;
                10'd450: dout0 <= 128'h97ba11a9e632f129e3eb95a1999e3e59;
                10'd451: dout0 <= 128'h6d12d92aa995b92993399e45eae15a32;
                10'd452: dout0 <= 128'h95ad6ee635c3ae28135999e21c14a296;
                10'd453: dout0 <= 128'hd9239adad5c94a4ce96ad51541d216e1;
                10'd454: dout0 <= 128'h662aed115986a96661e25915c332a6d6;
                10'd455: dout0 <= 128'h616cc959d94a4bae6d56de1d213a51c5;
                10'd456: dout0 <= 128'h95ee659135c56155a11ee3d56e5ada19;
                10'd457: dout0 <= 128'hedd2e999e5a669dee95e3d1be1e6e9ee;
                10'd458: dout0 <= 128'h6936a9211621611e315ed3eb5a111d99;
                10'd459: dout0 <= 128'h91d616e55ccda55516be539e5de5e1ad;
                10'd460: dout0 <= 128'h513c16eee6e59916de3da7a5e9d99e9d;
                10'd461: dout0 <= 128'hedda196166e6d99d9d5e6d69599d9151;
                10'd462: dout0 <= 128'he11a9eceea51dd95591695a5d915de69;
                10'd463: dout0 <= 128'hd13116295b599ed15d1a51e1111d96ee;
                10'd464: dout0 <= 128'h9e1e66ed9d999991dd39566559635119;
                10'd465: dout0 <= 128'h9256e6e6db51e4195d1e5eee6e551a9a;
                10'd466: dout0 <= 128'hea1d51d99919161e311919a11eb696e1;
                10'd467: dout0 <= 128'h166591a2539e1ce99ee1ad66e99a9ae1;
                10'd468: dout0 <= 128'h9e59ebd1553e18e1e5d569e666511219;
                10'd469: dout0 <= 128'h9eade1e69bdedeadedde5a6d1d1239ee;
                10'd470: dout0 <= 128'h4e196e1d39d652c51e15e2eddd9a5e55;
                10'd471: dout0 <= 128'hab1a1a6e29d7e2ce5ee1e9eede5eee99;
                10'd472: dout0 <= 128'h2b9511212e34a54565615f9a95e8e5d9;
                10'd473: dout0 <= 128'heb025c300d30632d79f09da307c61513;
                10'd474: dout0 <= 128'h1f8625ba9bf85b8e1b70756f6308a39c;
                10'd475: dout0 <= 128'h76ebe6524ae41522b9d6d663efe46d75;
                10'd476: dout0 <= 128'ha1965d9e191199e11961115ee19191e9;
                10'd477: dout0 <= 128'h15115e656a19de9dcdc5595a915e926a;
                10'd478: dout0 <= 128'h6f729a1ca359f6e6efd6c32d11eddcae;
                10'd479: dout0 <= 128'he56339aa2e21b9c31e3331a11ed29634;
                10'd480: dout0 <= 128'h9e091a62e3cd51e6635993ee15526ad1;
                10'd481: dout0 <= 128'h1c039e51d989e5ca6691155ee9dc61d1;
                10'd482: dout0 <= 128'h692e969a61091e22ea1e215163595cda;
                10'd483: dout0 <= 128'ha14691151e6de2a6ed5e1d6e6eb25616;
                10'd484: dout0 <= 128'h1d069dded92a166e5e9a5b516e16ee11;
                10'd485: dout0 <= 128'h1182ee5e31c91e969a51935d6a191d61;
                10'd486: dout0 <= 128'h1922e696d46911659e5a57971119dee5;
                10'd487: dout0 <= 128'h5e6e169e54ae15119ab115eb919355e5;
                10'd488: dout0 <= 128'h1192111e96a6559ed555ad119365e96b;
                10'd489: dout0 <= 128'hdda4d59355c9dde15d1965661e61d1a9;
                10'd490: dout0 <= 128'haee2a1259965d11d9519c15e992ebe66;
                10'd491: dout0 <= 128'h6e5a619e9d955e91111e6191591d5295;
                10'd492: dout0 <= 128'h9e61e111131d561e951e996e1e551655;
                10'd493: dout0 <= 128'he9e35dd1d55d9c99551e395e9e5e9151;
                10'd494: dout0 <= 128'h15969d5ee9d162e5151d59aea1193656;
                10'd495: dout0 <= 128'h5ee39d96951a92111eee156e129a9651;
                10'd496: dout0 <= 128'hd62115ea9996d2a99e9ee696aa115a69;
                10'd497: dout0 <= 128'h95e19559556c162995e561e3e69efe51;
                10'd498: dout0 <= 128'h69e19966a5d9996d6991ee9d66963e69;
                10'd499: dout0 <= 128'ha996156d6a152eed6a162e659e96599d;
                10'd500: dout0 <= 128'h39666e11c5b191216a6e2bdee11159a3;
                10'd501: dout0 <= 128'hb126cad63edc1d0abb92e31b0581539e;
                10'd502: dout0 <= 128'hfd2e2539bbba356a33e56b132e224fa4;
                10'd503: dout0 <= 128'hd66529b142bc25281a797a5797940df3;
                10'd504: dout0 <= 128'hbae529eb7c565aee9c6931f1ee2ead6d;
                10'd505: dout0 <= 128'h31959ee11156519e6665119ab9661516;
                10'd506: dout0 <= 128'h177665a76c31fce5adededa1be35e66e;
                10'd507: dout0 <= 128'h6ba17198a1963e4f5b3deb2519321e9a;
                10'd508: dout0 <= 128'h650e11e115a599256d9a99c5a91c6e92;
                10'd509: dout0 <= 128'h410eda21d3e5ddae935ee59131362a96;
                10'd510: dout0 <= 128'h2905319c1526114699551e196d3eea5c;
                10'd511: dout0 <= 128'h6989359659213e6e9ee2e1dd65d2eee6;
                10'd512: dout0 <= 128'h3d0ed536119195a11ad1d6d5e13a169e;
                10'd513: dout0 <= 128'h5e0e1d9e9a613196163e95956e9e9e51;
                10'd514: dout0 <= 128'hd102a55690e291119ed91d191551e65d;
                10'd515: dout0 <= 128'hde0215da50a991e165dda5ede935a115;
                10'd516: dout0 <= 128'h7982e6e192c61e1ed69e69a96b6159a5;
                10'd517: dout0 <= 128'h358691c955aeb3e65d9a6ec6e9955169;
                10'd518: dout0 <= 128'he1a15561dd155155d1522a955519d616;
                10'd519: dout0 <= 128'h11e1d5d23d319191e119ea1e5999da53;
                10'd520: dout0 <= 128'hee951d3e1d915e991d95de11e13ed659;
                10'd521: dout0 <= 128'he511d131d3de16d6de15511a9d919951;
                10'd522: dout0 <= 128'h59e1e9b111eaee95169e6d966916599e;
                10'd523: dout0 <= 128'h95da1e3e5a16515e916e91e5e61aee1e;
                10'd524: dout0 <= 128'h411195e661a99a5be511e1999ee19e1a;
                10'd525: dout0 <= 128'h85d1655e56511ea1919561299e1e75e1;
                10'd526: dout0 <= 128'h651519195a9626ceee5ae95911e665e9;
                10'd527: dout0 <= 128'h293a67e6ca59e98eea9ee11526169ad5;
                10'd528: dout0 <= 128'h15e26d9aad56a981625cebed89c19136;
                10'd529: dout0 <= 128'h39642c5e3199e365555e5babcd06e19e;
                10'd530: dout0 <= 128'h7e6a86c3fbfd76fce165a7ec539a63e8;
                10'd531: dout0 <= 128'h9de1c6cceef91ec2d6b4152f9faad3da;
                10'd532: dout0 <= 128'h915eed9ee59e55e1a9e119a1159e9ae6;
                10'd533: dout0 <= 128'he193155a653136d5ca9e9e9d5ad16ed3;
                10'd534: dout0 <= 128'h3ad1a1919eb5de6b9ad6e21e9e94eb51;
                10'd535: dout0 <= 128'hbb1dd99039daeeed2f9ba68ee3be2662;
                10'd536: dout0 <= 128'hc36e91e63e9551ad6ddee16d61901dea;
                10'd537: dout0 <= 128'hce253e9a55e9d669a99ed9921e521662;
                10'd538: dout0 <= 128'h25835a1e662659699159ee95ea5e99ae;
                10'd539: dout0 <= 128'h1589991295699662569195d196aaede6;
                10'd540: dout0 <= 128'hd10e659e6a953aeeda5a91ddae5e966e;
                10'd541: dout0 <= 128'h5909ed96a4dcdec112e69b15e6e916a9;
                10'd542: dout0 <= 128'hde0de93e60ec9eead2de95e5ed15e99d;
                10'd543: dout0 <= 128'hf601115262e6ee61de9615aeebe559e5;
                10'd544: dout0 <= 128'hb60be59e11a9691e919e1e11e315e965;
                10'd545: dout0 <= 128'h5e451eee655391de9d1e1e261b159db5;
                10'd546: dout0 <= 128'hcd63199513dd111d95ee559a159191e6;
                10'd547: dout0 <= 128'haa199e9619591111e19e19ee65115e11;
                10'd548: dout0 <= 128'h69e65ed1a999156919199e9691a65e96;
                10'd549: dout0 <= 128'he119925119d255919961ee1aa95e95d9;
                10'd550: dout0 <= 128'h1121d29ae116695eee6de1e159163951;
                10'd551: dout0 <= 128'h11191a559e1e99e562131a66ee11191a;
                10'd552: dout0 <= 128'hc6ea15d6ee52e165e11515955eae6991;
                10'd553: dout0 <= 128'h05ea596192912e695e5161559151e193;
                10'd554: dout0 <= 128'h29e965de2a1eee63341e55e39e11ad5f;
                10'd555: dout0 <= 128'h691d535e6dba214556915555eee652b5;
                10'd556: dout0 <= 128'h5e166d1522d9518d449617e12aa6e65e;
                10'd557: dout0 <= 128'h95d212e56e35eb659210a7271d88e3fc;
                10'd558: dout0 <= 128'h17e26e863df599ea733d554debca1d36;
                10'd559: dout0 <= 128'h95116961597355a65ade9e939b4a9734;
                10'd560: dout0 <= 128'hdea1516e5599591a6e91111ee5161e9d;
                10'd561: dout0 <= 128'h22599e362156d1d9ae3931353eba919d;
                10'd562: dout0 <= 128'h165611d8bd31e699167635ae1b62e7b1;
                10'd563: dout0 <= 128'habd59994353895ed13559341b39a5e94;
                10'd564: dout0 <= 128'h25e5d69a1c9e6dd56b3559ed3a90e756;
                10'd565: dout0 <= 128'he9c17ab169e359e11119ee1eea9ce91a;
                10'd566: dout0 <= 128'ha68e9ed64e19f16991195e919a9c1e5c;
                10'd567: dout0 <= 128'h66e9d19ec99ed11e525ed515961219ae;
                10'd568: dout0 <= 128'h2ea55b912419d921129e19551a91e516;
                10'd569: dout0 <= 128'he12d599e629e116d915e115d695e19e1;
                10'd570: dout0 <= 128'h16cb191aa4ea59add63661ae6ee55ea1;
                10'd571: dout0 <= 128'hdacb96516a1a61ae51589929cde9e115;
                10'd572: dout0 <= 128'h9cafe9da63319559e9e699e665ed9959;
                10'd573: dout0 <= 128'h16e79e15e9116116911ae19c5b991539;
                10'd574: dout0 <= 128'haed711d9e55d59ee59e1662c5e11d961;
                10'd575: dout0 <= 128'hae95de152d55e5519aee999665699d1e;
                10'd576: dout0 <= 128'he5d51a362de51b169e9596291112999e;
                10'd577: dout0 <= 128'h2639d29eaa111599aed9ad16e19db6de;
                10'd578: dout0 <= 128'he9999a51266eeb21ae55e12d99aa5959;
                10'd579: dout0 <= 128'h21129e59c1eeeb5daaa59623ee6c1599;
                10'd580: dout0 <= 128'h29115111ca9a97a5ee99e9e95e9ee5e5;
                10'd581: dout0 <= 128'h8de655162d92e7611de6e19e916ad55d;
                10'd582: dout0 <= 128'h6939dde6aae55123de9eee951a6ae5d5;
                10'd583: dout0 <= 128'h69939b592c365d2591aea115969ee1b9;
                10'd584: dout0 <= 128'h55e565dd3e516b25e2ee6e95e56e919a;
                10'd585: dout0 <= 128'h3132a11e5c5d2d4db256e13ea36ec3f9;
                10'd586: dout0 <= 128'h9391ca617db3dd5ee191656b1922dde9;
                10'd587: dout0 <= 128'h9199e9191e1e951595e969eede1e6e1e;
                10'd588: dout0 <= 128'h99ee19699e93d9e9ee9a6111d16a9151;
                10'd589: dout0 <= 128'h15111e1e4ee6e591e519d51939e1933a;
                10'd590: dout0 <= 128'ha7b161da63bc9918d95e77cef9e2d576;
                10'd591: dout0 <= 128'h8d3919d61e9c9d991d59bfa575e8ee5c;
                10'd592: dout0 <= 128'ha1f696162e665113ed9111a396184bd1;
                10'd593: dout0 <= 128'h695e913da1e16a13e6d16d55149ce9d8;
                10'd594: dout0 <= 128'h15965e5e4611319192596956a6ec6eda;
                10'd595: dout0 <= 128'h26599a15caee5eaae6959159e61e11b5;
                10'd596: dout0 <= 128'he19d9c96226a2e65e919e9611e111599;
                10'd597: dout0 <= 128'h1ae95e15aa191e11ddd6961529e915ee;
                10'd598: dout0 <= 128'h5e5d6111255ae111199e1699e16195e9;
                10'd599: dout0 <= 128'head39a9a2116e1e9911eee6aeee3e995;
                10'd600: dout0 <= 128'h96d3929d19d1d96e511e99ee6311ed69;
                10'd601: dout0 <= 128'h6659541ead1169e59a1e59c26196ed91;
                10'd602: dout0 <= 128'h69955c95a19151e19a66632e9de66b97;
                10'd603: dout0 <= 128'h2911d65121511915e19deeee11111de5;
                10'd604: dout0 <= 128'hae29525991111111116925661d126516;
                10'd605: dout0 <= 128'ha156d41e23e61d1e1ee956eae5951961;
                10'd606: dout0 <= 128'h2d96149c4e5135951aae96e26e6e9511;
                10'd607: dout0 <= 128'h6991e25e2e66e52151916611d9961919;
                10'd608: dout0 <= 128'h851a56164211536daee9a9a116651bea;
                10'd609: dout0 <= 128'he9195556c116156d6e9e26659d6eae56;
                10'd610: dout0 <= 128'he5a9535c2e1a55251e366661e95eef11;
                10'd611: dout0 <= 128'hd5e1b79a6e5ed941d93a6611a96653f6;
                10'd612: dout0 <= 128'h5ee6a3d561de2dc361a88915cb412f54;
                10'd613: dout0 <= 128'h1190e119a231252d6d46ddde63dd6779;
                10'd614: dout0 <= 128'hfcefe1a682112ae12675b334a994bda3;
                10'd615: dout0 <= 128'h969aa6919ee91ee6e5e1ee119e11e1ad;
                10'd616: dout0 <= 128'h9195eee3e61d119ed6d9959515161e99;
                10'd617: dout0 <= 128'h959e99a55569551e9995959e19195e95;
                10'd618: dout0 <= 128'h13b55e9c6991519031eebf4956e66535;
                10'd619: dout0 <= 128'h4b9e5e92aa251dea3679de55b51ee9f1;
                10'd620: dout0 <= 128'h1ab21ea96a1259653ae9ed11d66a659e;
                10'd621: dout0 <= 128'h5152a1d1ce1271111a15ede996a0edda;
                10'd622: dout0 <= 128'h955e14536196d936123e1e59eae2e936;
                10'd623: dout0 <= 128'h5e9a1cee6cde516e9ae55631e6e6e156;
                10'd624: dout0 <= 128'h9e512ee1615aa1951e5e95d5e1e1199e;
                10'd625: dout0 <= 128'he19966d1e9d5ee919196de11ab915dde;
                10'd626: dout0 <= 128'h9639961ee19159515111d159e6e15d15;
                10'd627: dout0 <= 128'ha159149e6e9eeede593e991ae1eda391;
                10'd628: dout0 <= 128'h6e51969519e919ee1e115e5a66596913;
                10'd629: dout0 <= 128'h9e59ecd6c19e95d1de51d6e1551ea519;
                10'd630: dout0 <= 128'h665ee55961e19d1d1a655ee219d9e9dd;
                10'd631: dout0 <= 128'hc91911596e969de9ee9999aa1ed99b6d;
                10'd632: dout0 <= 128'haee6ee1ee6915e15e61e1ea6119e611d;
                10'd633: dout0 <= 128'hede59cde6a59e5a5e2ee5ea46e19ad9e;
                10'd634: dout0 <= 128'h2eeae2ee4ee95d6e1126a6695515ed1a;
                10'd635: dout0 <= 128'ha9169e5e4e9e5169659e191d119e95ee;
                10'd636: dout0 <= 128'h2111d216a663ddc3eed1eea1d1a1699a;
                10'd637: dout0 <= 128'h1999e95121c999c5e6d1a1e51915621a;
                10'd638: dout0 <= 128'h91119d56ee6615c9197199415ddaa51e;
                10'd639: dout0 <= 128'h61e953566e95ee152e51aa1659d12d7a;
                10'd640: dout0 <= 128'ha96cd7d991d51b9e1e9ae29941e61d74;
                10'd641: dout0 <= 128'h9662e599961a3b256ee21a5e15ee1132;
                10'd642: dout0 <= 128'hb29f592a0665e6938cd4a69a76597733;
                10'd643: dout0 <= 128'h15e119a1de9a1636e6691d5111116199;
                10'd644: dout0 <= 128'h511161955de11d1191561ed9191256ed;
                10'd645: dout0 <= 128'h5955e1131e115959e51e611995ee6ade;
                10'd646: dout0 <= 128'h27337aa2a49453421377b14edcf06339;
                10'd647: dout0 <= 128'hcb39b698e9cead2911139a12bcda3df9;
                10'd648: dout0 <= 128'he2fab52261991e699126a39a52d18339;
                10'd649: dout0 <= 128'h961159e96e1196a15ea515911216abd9;
                10'd650: dout0 <= 128'h31d619e15a66e1a61fe596e626166752;
                10'd651: dout0 <= 128'hde9961d95112ea566d2139e99eee599c;
                10'd652: dout0 <= 128'h55519e9121e1e69e51993e9e65e511be;
                10'd653: dout0 <= 128'h9611ee916a396e15e6d93e1991e65556;
                10'd654: dout0 <= 128'h91d5ea69e1e11e1ee9bd9199669111de;
                10'd655: dout0 <= 128'h515d9ee69a155e6e199d711911e5991e;
                10'd656: dout0 <= 128'h565512d5291555919e59355995e99db1;
                10'd657: dout0 <= 128'hd15e6ce1a96115156e3d9e1195911d9d;
                10'd658: dout0 <= 128'ha69191d9a5e51165ee91ee611e5e6169;
                10'd659: dout0 <= 128'h2e1d1195ae519595a9e91e6e1de96d1d;
                10'd660: dout0 <= 128'h4191565e6966dd96ea91191a6119e955;
                10'd661: dout0 <= 128'h0619ee19a6199d16a5ee56e65e11c159;
                10'd662: dout0 <= 128'h292d9916ae6163e19a1e3e16e21129e1;
                10'd663: dout0 <= 128'h2161126629616d1e5921ea691d1969e9;
                10'd664: dout0 <= 128'hcd629e9a6969ab6d5ee1e6ae3519199a;
                10'd665: dout0 <= 128'h63261692512aee6a5a5e1a86ed336e92;
                10'd666: dout0 <= 128'h39ea5199e9621fa69a95ba6155e12371;
                10'd667: dout0 <= 128'h191ed3aa95e91b91969d149a9979cb3e;
                10'd668: dout0 <= 128'h76a9ed169cda6f695eaeead69a5a69fa;
                10'd669: dout0 <= 128'hdee29d661196de956e109ae6d55e67b9;
                10'd670: dout0 <= 128'h5b1dd5c68a1f9da506a2c9a13ee23ba6;
                10'd671: dout0 <= 128'he99e16151a66ee19e5e199111199e61e;
                10'd672: dout0 <= 128'he61995ee169eee1a55e1e91955aeeada;
                10'd673: dout0 <= 128'h6115155d515d9e1eed5695191e19e61a;
                10'd674: dout0 <= 128'h731a65d3595a95d4a611a3aaadad92e1;
                10'd675: dout0 <= 128'h51dd55a9e51a3e9d83cbdb9490bdd049;
                10'd676: dout0 <= 128'h65d33e51d1734e1ae31d1da1f5f589e6;
                10'd677: dout0 <= 128'h393e6e5332dd9c5363cbd9dad93e8bae;
                10'd678: dout0 <= 128'h913e19a1bc9c5c5d97619626ee39ab1a;
                10'd679: dout0 <= 128'he13e3ae1dc59a493d5c5eee6ea59e56a;
                10'd680: dout0 <= 128'h51e9d599d2196eee99691ee59d112362;
                10'd681: dout0 <= 128'h19565611991155e9e11d535e66611996;
                10'd682: dout0 <= 128'h69593a11121ea19929699e6996e3599e;
                10'd683: dout0 <= 128'h1192e6ee11ead1961911ed9deed1e9de;
                10'd684: dout0 <= 128'h91565ad121e695ee16551e31ee5de939;
                10'd685: dout0 <= 128'h5196996da51e5a1e6d695e79ee9e9335;
                10'd686: dout0 <= 128'h56d1de1ae591996eed19de3615591391;
                10'd687: dout0 <= 128'h6e559a99a91e1995ee911a1a6d361d56;
                10'd688: dout0 <= 128'h066939e15dce9d511e599912993ee59a;
                10'd689: dout0 <= 128'h091b925619d96529ee1ed11491926392;
                10'd690: dout0 <= 128'h855a5a1a1e596ea996569a2c5de56535;
                10'd691: dout0 <= 128'h81e4169ee91539ed16692aac91eb9596;
                10'd692: dout0 <= 128'h899c11e95ea9d1996669e5629ed56d1c;
                10'd693: dout0 <= 128'h539456ae95eedbceae661626d5ee9596;
                10'd694: dout0 <= 128'h593ade32d6e96369556d1cea96e115d2;
                10'd695: dout0 <= 128'h61d61e7136ab493a611f68a63b11c936;
                10'd696: dout0 <= 128'h3c5e39149ad3a3229eeab655eb204ffa;
                10'd697: dout0 <= 128'he9a159582be399ae17dc532eab24dd24;
                10'd698: dout0 <= 128'he391651531d9dbe9695e6dadeda636ea;
                10'd699: dout0 <= 128'h51596e69e96e92e11111d995d3eed596;
                10'd700: dout0 <= 128'h1155191ee95516519559ee6655656191;
                10'd701: dout0 <= 128'he6a51116691e119919eee95915e5e95e;
                10'd702: dout0 <= 128'h1d5dded45cc9e399d66d9c6e61de9ed5;
                10'd703: dout0 <= 128'hb2715a31d91152bdeee6ef32c55b9ec5;
                10'd704: dout0 <= 128'hb67d6e5d3bb9ac152b0361badf11434e;
                10'd705: dout0 <= 128'hbdf99e5974d9e25dedcf6152fdbe09e9;
                10'd706: dout0 <= 128'hc1f6d96e5a5c19a93b43e9ae3b7e6969;
                10'd707: dout0 <= 128'h6ef699299896ee515d8b9d1edf51c9ee;
                10'd708: dout0 <= 128'h1ede1265ea5a5171652b95e3fe51c56a;
                10'd709: dout0 <= 128'haed556ae16155953650d5991be966b11;
                10'd710: dout0 <= 128'ha53c5e216ce65edd55c3d91c397d5ec9;
                10'd711: dout0 <= 128'heed299e951eee2d155a511161d3de522;
                10'd712: dout0 <= 128'h115256ae9a36e525e509e9925136e3e6;
                10'd713: dout0 <= 128'h91d49ae16ea1ad6399c196665cbe29ec;
                10'd714: dout0 <= 128'h29586aa5599cebe9de11a215d959e962;
                10'd715: dout0 <= 128'ha150d5c99d9a116551e5215a29192e16;
                10'd716: dout0 <= 128'h89d0e1a19d9a231d19ed16da16be235a;
                10'd717: dout0 <= 128'hc918e4ee1b119511512de658eddd2595;
                10'd718: dout0 <= 128'h81e0991e551c96dd912de81aa9dd2d92;
                10'd719: dout0 <= 128'h66145113ee52912dee8b1e361cfe63e1;
                10'd720: dout0 <= 128'hae5c91319e49a1665a2311d112131d56;
                10'd721: dout0 <= 128'h1a5c1cd9d16722ede8c5c67e91b32318;
                10'd722: dout0 <= 128'h1afeeaea364b2e356226cc91a9331d26;
                10'd723: dout0 <= 128'hd8fdba1ae8efa95d6c694c7c23b16556;
                10'd724: dout0 <= 128'h147e7c99927b125318af61f245322ff1;
                10'd725: dout0 <= 128'h1e5e611ed26ae1e93691e9ad35156961;
                10'd726: dout0 <= 128'h5d1e61e6a5399ee6593eee6d199ad512;
                10'd727: dout0 <= 128'h991e9911e19e12ae1e11ed951b1919e9;
                10'd728: dout0 <= 128'he11ee5e5e1e1d11e9ee5195e1e165ad6;
                10'd729: dout0 <= 128'he16d11156995561e1e991e959ee699ee;
                10'd730: dout0 <= 128'ha6e151e6e12e51196593659e611161ed;
                10'd731: dout0 <= 128'h6e9eee1eb9aee1d99a91666599e16612;
                10'd732: dout0 <= 128'ha59656e17e6f49f1f869c69ff36b4156;
                10'd733: dout0 <= 128'h16f29e1e14e324b57e1f44c37d394c33;
                10'd734: dout0 <= 128'hdcfea95e9895a455d1e7061eb796c2d9;
                10'd735: dout0 <= 128'h16a4aee35cdd9afdbec7061dbbee0169;
                10'd736: dout0 <= 128'h22e0a96d9431b63fb517ce5e31516129;
                10'd737: dout0 <= 128'h2e166917dc5e92353e1fc556fdd5262a;
                10'd738: dout0 <= 128'he1d6eaa3b4e6e953318fe53afdfe1192;
                10'd739: dout0 <= 128'h31d4954de86155a2da9f915139b6a1ed;
                10'd740: dout0 <= 128'hb1dc9e1d1e55c16eb29fa4d9197ec165;
                10'd741: dout0 <= 128'h3a2eae33723e966b763f16755efe0919;
                10'd742: dout0 <= 128'h16e9a6e7fc53e19f766f1e3375590a95;
                10'd743: dout0 <= 128'h1e91ee297ed7691f9623e91d54a6039e;
                10'd744: dout0 <= 128'hde6219edda57c9e5e1a31619923e0d91;
                10'd745: dout0 <= 128'h91169e13d61d1d1dd6efa156b67a8e13;
                10'd746: dout0 <= 128'h295a1ee75ade11db5a63a2919a7e0615;
                10'd747: dout0 <= 128'hcad64115d1be92ef9a4b98f69c51ad51;
                10'd748: dout0 <= 128'hce726d533816a1e39c8f60352c3a0d5e;
                10'd749: dout0 <= 128'h611aecedb2932eab504f963112dd25d8;
                10'd750: dout0 <= 128'hee5566ebb6e3c527382feebe5a96a592;
                10'd751: dout0 <= 128'he11594dd522a935fbead2213b65da5b5;
                10'd752: dout0 <= 128'h36e126fdb461e9d9b629a69db191a6f3;
                10'd753: dout0 <= 128'h1665515d661e5ee9ea9ea61aed659d11;
                10'd754: dout0 <= 128'h11919e6a595e2a511569ee9161ed959a;
                10'd755: dout0 <= 128'h99911951e569e19b1a1999eeeea511d1;
                10'd756: dout0 <= 128'h915e959119ee159dd191991ee911ee91;
                10'd757: dout0 <= 128'he99ee1e1696e19ee9999e99521651e9e;
                10'd758: dout0 <= 128'h91596e651e93e66911669d991e95e1e5;
                10'd759: dout0 <= 128'h99116a1e6e1e52ee65e991e1eee119d5;
                10'd760: dout0 <= 128'hd915a1e165111561e5695ede19e1e9e2;
                10'd761: dout0 <= 128'he159e9e965b61e19e116e5566e5eed61;
                10'd762: dout0 <= 128'h3a62a9e9bad9da911e6156d5b9112de9;
                10'd763: dout0 <= 128'h3c9161e95a995e5956e5d6b9d1e1611e;
                10'd764: dout0 <= 128'h5c19a91bb196b61931ed11515191a599;
                10'd765: dout0 <= 128'he6c666e3599e516baaceeb3e61ce1b22;
                10'd766: dout0 <= 128'hd42ded1f397355611a6a13f3e19d5966;
                10'd767: dout0 <= 128'h99e165adb29d239510916b7d13eba211;
                10'd768: dout0 <= 128'h6d961e9ddc1bebd192d9ca5997a3aae1;
                10'd769: dout0 <= 128'hd613212f79b5b33d18eec6fbed2dafa4;
                10'd770: dout0 <= 128'hd9e92ec7f29b9fb650cf91b3fd430918;
                10'd771: dout0 <= 128'h93deee25321b3331de2ba9553d450615;
                10'd772: dout0 <= 128'h3299aaa3f557b65dea656d35964dc92e;
                10'd773: dout0 <= 128'h1a614627f9f511353c56ded5996b2622;
                10'd774: dout0 <= 128'hc596e1553155ed3956559155bee72ee5;
                10'd775: dout0 <= 128'h21656e9ff659215930ede559b54fea99;
                10'd776: dout0 <= 128'h1dee2995f1eee9e5b699193e5595529a;
                10'd777: dout0 <= 128'hd145ca6773de62e6da476eba592a3eec;
                10'd778: dout0 <= 128'h52292e27f765cea3d6cd127ade245518;
                10'd779: dout0 <= 128'h9ce9ae47535e5e191516153a65aaf5ee;
                10'd780: dout0 <= 128'ha96e11d966e6a1e15511699e9611591e;
                10'd781: dout0 <= 128'h1165e16151e6eee95e916e1161e69e91;
                10'd782: dout0 <= 128'h5e11e66eed1969e9621911e6e9969969;
                10'd783: dout0 <= 128'he5e199eee165955e966199119919e9ee;
                default: dout0 <= {128{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_macro_weights_l2
//
// model2rtl behavioural model for the generated OpenROM contents of the
// "weights_l2" macro.  It is NOT OpenROM-generated Verilog: the OpenROM
// compiler's own .v output is a byte-oriented, delay-based, non-synthesizable
// stub that does not implement this project's read contract, so it is not used.
//
// Pin names follow the OpenROM macro convention (clk0 / cs0 / addr0 / dout0) so
// that dropping in the physical macro changes only this module body.
//
// Contents: 32 words x 40 bits, canonical image sha256
//   b3866b5dcbd1e60e75300794786c9c75fa8e08361dbb31144182748bee934cec
// Bit order: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_macro_weights_l2 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [4:0]           addr0,
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
// rom_macro_bias_l1
//
// model2rtl behavioural model for the generated OpenROM contents of the
// "bias_l1" macro.  It is NOT OpenROM-generated Verilog: the OpenROM
// compiler's own .v output is a byte-oriented, delay-based, non-synthesizable
// stub that does not implement this project's read contract, so it is not used.
//
// Pin names follow the OpenROM macro convention (clk0 / cs0 / addr0 / dout0) so
// that dropping in the physical macro changes only this module body.
//
// Contents: 32 words x 22 bits, canonical image sha256
//   ac8563c111b41dd72a09b55ee3136ab71e4f538a567b84a50c9de949f520364d
// Bit order: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_macro_bias_l1 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [4:0]           addr0,
    output reg  [21:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                5'd0: dout0 <= 22'h3dc000;
                5'd1: dout0 <= 22'h2b7fff;
                5'd2: dout0 <= 22'h0e2000;
                5'd3: dout0 <= 22'h303fff;
                5'd4: dout0 <= 22'h0a4000;
                5'd5: dout0 <= 22'h090000;
                5'd6: dout0 <= 22'h00ffff;
                5'd7: dout0 <= 22'h248000;
                5'd8: dout0 <= 22'h136000;
                5'd9: dout0 <= 22'h3e2000;
                5'd10: dout0 <= 22'h394000;
                5'd11: dout0 <= 22'h030000;
                5'd12: dout0 <= 22'h123fff;
                5'd13: dout0 <= 22'h3effff;
                5'd14: dout0 <= 22'h0d7fff;
                5'd15: dout0 <= 22'h2a8000;
                5'd16: dout0 <= 22'h0a7fff;
                5'd17: dout0 <= 22'h086000;
                5'd18: dout0 <= 22'h2cc000;
                5'd19: dout0 <= 22'h275fff;
                5'd20: dout0 <= 22'h167fff;
                5'd21: dout0 <= 22'h17bfff;
                5'd22: dout0 <= 22'h252000;
                5'd23: dout0 <= 22'h0d8000;
                5'd24: dout0 <= 22'h3b0000;
                5'd25: dout0 <= 22'h134000;
                5'd26: dout0 <= 22'h320000;
                5'd27: dout0 <= 22'h21c000;
                5'd28: dout0 <= 22'h114000;
                5'd29: dout0 <= 22'h2e2000;
                5'd30: dout0 <= 22'h167fff;
                5'd31: dout0 <= 22'h39dfff;
                default: dout0 <= {22{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// rom_macro_bias_l2
//
// model2rtl behavioural model for the generated OpenROM contents of the
// "bias_l2" macro.  It is NOT OpenROM-generated Verilog: the OpenROM
// compiler's own .v output is a byte-oriented, delay-based, non-synthesizable
// stub that does not implement this project's read contract, so it is not used.
//
// Pin names follow the OpenROM macro convention (clk0 / cs0 / addr0 / dout0) so
// that dropping in the physical macro changes only this module body.
//
// Contents: 10 words x 17 bits, canonical image sha256
//   efb63bb9cc7b26d721b4fc53f19aaed428916dae6dc1ed29074f8e0dac942482
// Bit order: Within a word, the macro drives dout0[b] = bit (word_bits-1-b) of that word's big-endian value, i.e.
// ---------------------------------------------------------------------------
module rom_macro_bias_l2 (
    input  wire                 clk0,
    input  wire                 cs0,
    input  wire [3:0]           addr0,
    output reg  [16:0]         dout0
);
    always @(posedge clk0) begin
        if (cs0) begin
            case (addr0)
                4'd0: dout0 <= 17'h0d3ff;
                4'd1: dout0 <= 17'h0a000;
                4'd2: dout0 <= 17'h08000;
                4'd3: dout0 <= 17'h197ff;
                4'd4: dout0 <= 17'h12800;
                4'd5: dout0 <= 17'h01400;
                4'd6: dout0 <= 17'h0d7ff;
                4'd7: dout0 <= 17'h13800;
                4'd8: dout0 <= 17'h19000;
                4'd9: dout0 <= 17'h0dbff;
                default: dout0 <= {17{1'b0}};
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------
// Backend B wrapper. ASIC / SKY130 only -- no FPGA portability is claimed.
//
// It presents byte-for-byte the same logical interface as the portable backend
// and hides how many physical macros exist behind it.  Its jobs are:
//   * strobe the right macro for the requested layer,
//   * undo the OpenROM bit reversal,
//   * zero the unused high weight bits for layer 2,
//   * sign extend the layer-2 bias onto the 22-bit bus,
//   * return zeros for out-of-range addresses.
// ---------------------------------------------------------------------------
module mnist_mlp_params_openram (
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

    // ---- macro instances -----------------------------------------------
    wire [127:0] wl1_dout;
    wire [39:0]  wl2_dout;
    wire [21:0]  bl1_dout;
    wire [16:0]  bl2_dout;

    rom_macro_weights_l1 u_wl1 (.clk0(clk), .cs0(wsel_l1),
                                .addr0(wmem_addr[9:0]), .dout0(wl1_dout));
    rom_macro_weights_l2 u_wl2 (.clk0(clk), .cs0(wsel_l2),
                                .addr0(wmem_addr[4:0]), .dout0(wl2_dout));
    rom_macro_bias_l1    u_bl1 (.clk0(clk), .cs0(bsel_l1),
                                .addr0(bmem_addr[4:0]), .dout0(bl1_dout));
    rom_macro_bias_l2    u_bl2 (.clk0(clk), .cs0(bsel_l2),
                                .addr0(bmem_addr[3:0]), .dout0(bl2_dout));

    // ---- undo the OpenROM bit reversal ----------------------------------
    wire [127:0] wl1_word;
    wire [39:0]  wl2_word;
    wire [21:0]  bl1_word;
    wire [16:0]  bl2_word;
    generate
        for (gi = 0; gi < 128; gi = gi + 1) begin : WL1_WORD_REV
            assign wl1_word[gi] = wl1_dout[127 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 40; gi = gi + 1) begin : WL2_WORD_REV
            assign wl2_word[gi] = wl2_dout[39 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 22; gi = gi + 1) begin : BL1_WORD_REV
            assign bl1_word[gi] = bl1_dout[21 - gi];
        end
    endgenerate
    generate
        for (gi = 0; gi < 17; gi = gi + 1) begin : BL2_WORD_REV
            assign bl2_word[gi] = bl2_dout[16 - gi];
        end
    endgenerate

    // ---- present the fixed interface ------------------------------------
    assign wmem_data = (wvalid_d == 1'b0) ? {128{1'b0}}
                     : (wlayer_d == 1'b0) ? wl1_word
                                          : {88'd0, wl2_word};

    // layer-2 biases are SIGN extended from 17 to 22 bits, never zero extended
    assign bmem_data = (bvalid_d == 1'b0) ? {22{1'b0}}
                     : (blayer_d == 1'b0) ? bl1_word
                                          : {{5{bl2_word[16]}}, bl2_word};

endmodule

`default_nettype wire
