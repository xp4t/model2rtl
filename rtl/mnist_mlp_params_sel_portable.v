// ===========================================================================
// Build-time backend selector: `mnist_mlp_params` -> mnist_mlp_params_portable
// GENERATED FILE. Compile exactly ONE selector file per build.
// ===========================================================================

`default_nettype none

module mnist_mlp_params (
    input  wire          clk,
    input  wire          wmem_en,
    input  wire          wmem_layer,
    input  wire [9:0]    wmem_addr,
    output wire [127:0]   wmem_data,
    input  wire          bmem_en,
    input  wire          bmem_layer,
    input  wire [5:0]     bmem_addr,
    output wire [21:0]    bmem_data
);

    mnist_mlp_params_portable u_backend (
        .clk(clk),
        .wmem_en(wmem_en), .wmem_layer(wmem_layer),
        .wmem_addr(wmem_addr), .wmem_data(wmem_data),
        .bmem_en(bmem_en), .bmem_layer(bmem_layer),
        .bmem_addr(bmem_addr), .bmem_data(bmem_data)
    );

endmodule

`default_nettype wire
