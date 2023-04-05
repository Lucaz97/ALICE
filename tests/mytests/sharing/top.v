
module top(in1, in2, in3, out1, out2, out3, out4, out5);

input in1, in2, in3;
output out1, out2, out3, out4, out5;


a_mod	a_inst0(
		.in1( in1 ),
		.in2( in2 ),
		.in3( in3 ),
		.out1( out1 )
		);


endmodule 