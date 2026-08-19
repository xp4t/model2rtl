// ===========================================================================
// mnist_mlp_top.v -- GENERATED FILE, do not edit by hand.
//
// mnist_mlp_fabric (Stage 1, UNCHANGED) + one Stage-2 parameter backend.
//
// BACKEND SELECTION IS BUILD TIME. Compile exactly one of:
//     rtl/mnist_mlp_top.v rtl/mnist_mlp_fabric.v rtl/mnist_mlp_params_portable.v \
//         rtl/mnist_mlp_params_sel_portable.v
//     rtl/mnist_mlp_top.v rtl/mnist_mlp_fabric.v rtl/mnist_mlp_params_openram.v \
//         rtl/mnist_mlp_params_sel_openram.v
// Each selector file defines the module `mnist_mlp_params` and binds it to one
// backend.  The two selectors are mutually exclusive by construction, so there
// is never an unresolved or duplicated module.
// ===========================================================================

`default_nettype none

module mnist_mlp_top (
    input  wire         clk,
    input  wire         rst,
    input  wire         start,
    output wire         in_ready,
    input  wire         in_valid,
    input  wire [7:0]   in_data,
    output wire         busy,
    output wire         done,
    output wire         prediction_valid,
    output wire [3:0]   prediction,
    output wire [179:0] logits
);

    wire         wmem_en, wmem_layer;
    wire [9:0]  wmem_addr;
    wire [127:0] wmem_data;
    wire         bmem_en, bmem_layer;
    wire [5:0]   bmem_addr;
    wire [21:0]  bmem_data;

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
