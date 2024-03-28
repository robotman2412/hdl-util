
// Copyright © 2024, Julian Scheffers, see LICENSE for more information

`timescale 1ns/1ps

module hu_selector#(
    // Number of select bits.
    parameter width     = 2,
    // Type of the selected value.
    type      seltype   = bit[7:0]
)(
    // Selector.
    input  wire [width-1:0] sel,
    // Input data.
    input  seltype          d[width],
    // Output data.
    output seltype          q
);
    genvar x;
    integer i;
    seltype mask[width];
    generate
        for (x = 0; x < width; x = x + 1) begin
            assign mask[x] = sel[x] ? d[x] : 0;
        end
    endgenerate
    always @(*) begin
        q = 0;
        for (i = 0; i < width; i = i + 1) begin
            q |= mask[i];
        end
    end
endmodule

