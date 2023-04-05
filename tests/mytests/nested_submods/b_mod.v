

module b_mod(in1, out1);



input in1;
output out1; 

wire a;


c_mod	c_inst0(
		.in1(	in1	),
		.out1(	a )
		);

c_mod	c_inst1(
		.in1(	a	),
		.out1(	out1 )
		);

endmodule 