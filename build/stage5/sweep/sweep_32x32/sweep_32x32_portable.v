// GENERATED for the Stage-5 storage sweep. Portable Verilog-2001.
`default_nettype none

module sweep_32x32_portable (
    input  wire                 clk,
    input  wire                 en,
    input  wire [4:0]           addr,
    output reg  [31:0]          dout
);
    always @(posedge clk) begin
        if (en) begin
            case (addr)
            5'd0: dout <= 32'h58a2c3e5;
            5'd1: dout <= 32'heab38cab;
            5'd2: dout <= 32'h3827b889;
            5'd3: dout <= 32'h3b6649d5;
            5'd4: dout <= 32'hb2ba8778;
            5'd5: dout <= 32'hbf140281;
            5'd6: dout <= 32'ha946ac00;
            5'd7: dout <= 32'h619cfe63;
            5'd8: dout <= 32'h5b8f3653;
            5'd9: dout <= 32'h297e798d;
            5'd10: dout <= 32'hc5c66393;
            5'd11: dout <= 32'hccf40762;
            5'd12: dout <= 32'h72cefefe;
            5'd13: dout <= 32'h76efa572;
            5'd14: dout <= 32'hc71c461b;
            5'd15: dout <= 32'h577f5e69;
            5'd16: dout <= 32'h4e318edd;
            5'd17: dout <= 32'hefc58975;
            5'd18: dout <= 32'hbaf4760f;
            5'd19: dout <= 32'h0ab638cf;
            5'd20: dout <= 32'h533eb588;
            5'd21: dout <= 32'haa94da48;
            5'd22: dout <= 32'h85483cfb;
            5'd23: dout <= 32'h9736770e;
            5'd24: dout <= 32'h7e1f955c;
            5'd25: dout <= 32'h3c2bf405;
            5'd26: dout <= 32'ha9434631;
            5'd27: dout <= 32'hf7f34264;
            5'd28: dout <= 32'ha178b54c;
            5'd29: dout <= 32'h70242878;
            5'd30: dout <= 32'h8e361cbe;
            5'd31: dout <= 32'h9c553cba;
                default: dout <= {32{1'b0}};
            endcase
        end
    end
endmodule

`default_nettype wire
