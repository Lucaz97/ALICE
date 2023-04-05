
module top(in1, in2, in3, out1, out2, out3, out4, out5);


input in1, in2, in3;
output out1, out2, out3, out4, out5;

wire test;


a_mod	a_inst0(
		.in1(	in1	),
		.out1(	out1		)
		);


b_mod	b_inst0(
		.in1(	in2	),
		.out1(	out2		)
		);

b_mod	b_inst1(

		.in1(	in3	),
		.out1(	out3		)
		);

a_mod	a_inst1(
		.in1(	in1	),
		.out1(	out4		)
		);

a_mod	a_inst2(
		.in1(	in1	),
		.out1(	out5		)
		);


endmodule 
