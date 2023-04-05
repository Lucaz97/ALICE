module top #(parameter N=16)(input clk, input rst_n, input [N-1:0] in, output reg [N-1:0] out);

	always @(posedge clk) begin : proc_
		if(~rst_n) begin
			out <= 0;
		end else begin
			 out <= in;
		end
	end

endmodule 
