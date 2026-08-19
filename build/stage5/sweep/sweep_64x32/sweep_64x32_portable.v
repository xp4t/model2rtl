// GENERATED for the Stage-5 storage sweep. Portable Verilog-2001.
`default_nettype none

module sweep_64x32_portable (
    input  wire                 clk,
    input  wire                 en,
    input  wire [5:0]           addr,
    output reg  [31:0]          dout
);
    always @(posedge clk) begin
        if (en) begin
            case (addr)
            6'd0: dout <= 32'h58a2c3e5;
            6'd1: dout <= 32'heab38cab;
            6'd2: dout <= 32'h3827b889;
            6'd3: dout <= 32'h3b6649d5;
            6'd4: dout <= 32'hb2ba8778;
            6'd5: dout <= 32'hbf140281;
            6'd6: dout <= 32'ha946ac00;
            6'd7: dout <= 32'h619cfe63;
            6'd8: dout <= 32'h5b8f3653;
            6'd9: dout <= 32'h297e798d;
            6'd10: dout <= 32'hc5c66393;
            6'd11: dout <= 32'hccf40762;
            6'd12: dout <= 32'h72cefefe;
            6'd13: dout <= 32'h76efa572;
            6'd14: dout <= 32'hc71c461b;
            6'd15: dout <= 32'h577f5e69;
            6'd16: dout <= 32'h4e318edd;
            6'd17: dout <= 32'hefc58975;
            6'd18: dout <= 32'hbaf4760f;
            6'd19: dout <= 32'h0ab638cf;
            6'd20: dout <= 32'h533eb588;
            6'd21: dout <= 32'haa94da48;
            6'd22: dout <= 32'h85483cfb;
            6'd23: dout <= 32'h9736770e;
            6'd24: dout <= 32'h7e1f955c;
            6'd25: dout <= 32'h3c2bf405;
            6'd26: dout <= 32'ha9434631;
            6'd27: dout <= 32'hf7f34264;
            6'd28: dout <= 32'ha178b54c;
            6'd29: dout <= 32'h70242878;
            6'd30: dout <= 32'h8e361cbe;
            6'd31: dout <= 32'h9c553cba;
            6'd32: dout <= 32'h558887fd;
            6'd33: dout <= 32'h04e669a0;
            6'd34: dout <= 32'h4bd3a09f;
            6'd35: dout <= 32'h7370e6c9;
            6'd36: dout <= 32'h10573c11;
            6'd37: dout <= 32'hd5509478;
            6'd38: dout <= 32'hb06a6733;
            6'd39: dout <= 32'h0e7a207b;
            6'd40: dout <= 32'heae9e9c2;
            6'd41: dout <= 32'h5d74dff2;
            6'd42: dout <= 32'h5bf23af3;
            6'd43: dout <= 32'hd841e78f;
            6'd44: dout <= 32'h696471b3;
            6'd45: dout <= 32'h577d3443;
            6'd46: dout <= 32'h16e12e60;
            6'd47: dout <= 32'h8515b87f;
            6'd48: dout <= 32'h0b12a102;
            6'd49: dout <= 32'h85d06e66;
            6'd50: dout <= 32'h530af63d;
            6'd51: dout <= 32'h780635a5;
            6'd52: dout <= 32'h1cb26ea0;
            6'd53: dout <= 32'h206fd3da;
            6'd54: dout <= 32'h52907efd;
            6'd55: dout <= 32'he2acf89c;
            6'd56: dout <= 32'h004e65e4;
            6'd57: dout <= 32'hc95f3aad;
            6'd58: dout <= 32'h445cf17e;
            6'd59: dout <= 32'hf93fb1e4;
            6'd60: dout <= 32'hebc0925d;
            6'd61: dout <= 32'h2f0aa9be;
            6'd62: dout <= 32'hb2189af7;
            6'd63: dout <= 32'h3858fac9;
                default: dout <= {32{1'b0}};
            endcase
        end
    end
endmodule

`default_nettype wire
