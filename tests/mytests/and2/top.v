module top #(parameter N=5)(input a, input [N-1:0] in, output [N-1:0] out);

	genvar i;

	generate
		for (i = 0; i < N; i = i+1) begin
			and2 u0(in[i], a, out[i]);
		end
	endgenerate

endmodule