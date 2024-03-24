
// Copyright © 2024, Julian Scheffers, see LICENSE for more information

`timescale 1ns/1ps

module hu_pipeline_reg#(
    // Number of pipeline registers.
    parameter depth     = 1,
    // Type of the pipeline register.
    type      regtype   = bit[7:0]
)(
    // Pipeline clock.
    input  logic    clk,
    // Input data.
    input  regtype  d,
    // Output data.
    output regtype  q
);
    genvar x;
    regtype regs[depth+1];
    assign regs[0] = d;
    assign q = regs[depth];
    generate
        for (x = 0; x < depth; x = x + 1) begin
            assign regs[x+1] = regs[x];
        end
    endgenerate
endmodule
