// TEST-ONLY Stage-3 testbench. Never synthesized.
// Drives mnist_mlp_top back to back under a selectable input stall pattern and
// optionally captures a cycle-by-cycle internal trace of the fabric.
`timescale 1ns/1ps

module tb;
    parameter NIMG        = 4;
    parameter STALL_MODE  = 0;   // 0 none, 1 periodic, 2 pseudo-random
    parameter STALL_N     = 7;   // period for mode 1
    parameter TRACE_IMAGES = 0;  // capture the internal trace for the first M

    localparam N_IN     = 784;
    localparam N_HID    = 32;
    localparam N_OUT    = 10;
    localparam ACT_BITS = 8;
    localparam ACC2     = 18;
    localparam PREDW    = 4;
    localparam LOGW     = 180;
    localparam TIMEOUT  = 40000;

    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg                rst, start, in_valid;
    reg [ACT_BITS-1:0] in_data;
    wire               in_ready, busy, done, prediction_valid;
    wire [PREDW-1:0]   prediction;
    wire [LOGW-1:0]    logits;

    mnist_mlp_top dut (
        .clk(clk), .rst(rst), .start(start),
        .in_ready(in_ready), .in_valid(in_valid), .in_data(in_data),
        .busy(busy), .done(done), .prediction_valid(prediction_valid),
        .prediction(prediction), .logits(logits)
    );

    reg [ACT_BITS-1:0] img [0:NIMG*N_IN-1];
    reg [31:0] cyc;
    always @(posedge clk) cyc <= cyc + 32'd1;

    integer fh_out, fh_hid, fh_tr, im, q, errors, done_pulses;
    reg [15:0] lfsr;

    // ---- cycle-by-cycle internal trace -----------------------------------
    integer trace_img;
    task capture;
        begin
            $fwrite(fh_tr, "%0d %0d %0d %0d %0d %0d %0d %0d %h %h",
                    trace_img, cyc,
                    dut.u_fabric.state, dut.u_fabric.mac_valid,
                    dut.u_fabric.layer_r, dut.u_fabric.fin_valid,
                    dut.u_fabric.fin_idx, dut.u_fabric.act_pipe,
                    dut.wmem_data, dut.bmem_data);
            $fwrite(fh_tr, " %0d", dut.u_fabric.acc1[0]); $fwrite(fh_tr, " %0d", dut.u_fabric.acc1[1]); $fwrite(fh_tr, " %0d", dut.u_fabric.acc1[31]);
            $fwrite(fh_tr, " %0d", dut.u_fabric.l1_sel_ext[0]); $fwrite(fh_tr, " %0d", dut.u_fabric.l1_sel_ext[1]); $fwrite(fh_tr, " %0d", dut.u_fabric.l1_sel_ext[31]);
            $fwrite(fh_tr, " %0d %0d", dut.u_fabric.l1_accb,
                    dut.u_fabric.hid_next);
            $fwrite(fh_tr, " %0d", dut.u_fabric.acc2[0]); $fwrite(fh_tr, " %0d", dut.u_fabric.acc2[9]);
            $fwrite(fh_tr, " %0d", dut.u_fabric.l2_sel_ext[0]); $fwrite(fh_tr, " %0d", dut.u_fabric.l2_sel_ext[9]);
            $fwrite(fh_tr, " %0d", dut.u_fabric.logit_next);
            $fwrite(fh_tr, " %0d %0d %0d", dut.u_fabric.prod_00,
                    dut.u_fabric.prod_09, dut.u_fabric.prod_15);
            $fdisplay(fh_tr, "");
        end
    endtask

    // ---- one image --------------------------------------------------------
    task run_image;
        input integer index;
        integer base, pix, t0, t1, guard, bubble;
        begin
            base = index * N_IN;
            trace_img = index;

            @(negedge clk); start = 1'b1; t0 = cyc;
            if (index < TRACE_IMAGES) capture;
            @(negedge clk); start = 1'b0;

            pix    = 0;
            bubble = 0;
            while (pix < N_IN) begin
                if (index < TRACE_IMAGES) capture;
                if (in_ready && (bubble == 0)) begin
                    in_valid = 1'b1;
                    in_data  = img[base + pix];
                    pix      = pix + 1;
                    if (STALL_MODE == 1)
                        bubble = ((pix % STALL_N) == 0) ? 1 : 0;
                    else if (STALL_MODE == 2) begin
                        lfsr   = {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
                        bubble = lfsr[0];
                    end else
                        bubble = 0;
                end else begin
                    in_valid = 1'b0;
                    bubble   = 0;
                end
                @(negedge clk);
            end
            in_valid = 1'b0;

            guard = 0;
            while (!done && (guard < TIMEOUT)) begin
                if (index < TRACE_IMAGES) capture;
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) begin
                $display("TIMEOUT on image %0d", index);
                errors = errors + 1;
            end else begin
                if (index < TRACE_IMAGES) capture;
                t1 = cyc;
                done_pulses = done_pulses + 1;
                if (prediction_valid !== 1'b1) begin
                    $display("prediction_valid low with done, image %0d", index);
                    errors = errors + 1;
                end
                if (busy !== 1'b1) begin
                    $display("busy low while done asserted, image %0d", index);
                    errors = errors + 1;
                end
                $fwrite(fh_out, "%0d %0d %0d", index, t1 - t0 + 1, prediction);
                for (q = 0; q < N_OUT; q = q + 1)
                    $fwrite(fh_out, " %0d", $signed(logits[q*ACC2 +: ACC2]));
                $fdisplay(fh_out, "");

                $fwrite(fh_hid, "%0d", index);
                for (q = 0; q < N_HID; q = q + 1)
                    $fwrite(fh_hid, " %0d", dut.u_fabric.hidden[q]);
                $fdisplay(fh_hid, "");
            end
            @(negedge clk);
            // done must be a single-cycle pulse
            if (done !== 1'b0) begin
                $display("done still high one cycle later, image %0d", index);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        cyc = 32'd0; errors = 0; done_pulses = 0; lfsr = 16'hACE1;
        rst = 1'b1; start = 1'b0; in_valid = 1'b0;
        in_data = {ACT_BITS{1'b0}};
        $readmemh("img.hex", img);
        fh_out = $fopen("out.txt", "w");
        fh_hid = $fopen("hidden.txt", "w");
        fh_tr  = $fopen("trace.txt", "w");

        repeat (4) @(negedge clk);
        rst = 1'b0;
        @(negedge clk);

        for (im = 0; im < NIMG; im = im + 1)
            run_image(im);

        if (done_pulses != NIMG) begin
            $display("expected %0d done pulses, saw %0d", NIMG, done_pulses);
            errors = errors + 1;
        end
        $fclose(fh_out); $fclose(fh_hid); $fclose(fh_tr);
        if (errors != 0) $display("TB ERRORS: %0d", errors);
        else             $display("TB OK");
        $finish;
    end
endmodule
