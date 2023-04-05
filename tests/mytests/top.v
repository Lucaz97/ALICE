

module Subtractor_0x422b1f52edd46a85_FPGA
(
  input wire [0:0] clk,
  input wire [15:0] in0,
  input wire [15:0] in1,
  output reg [15:0] out,
  input wire [0:0] reset
);


  always @(*) begin
    out = in0 - in1;
  end


endmodule

