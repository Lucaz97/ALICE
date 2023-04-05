module top (a,b,c,d,e,f,out1);

	input a,b,c,d,e,f;
	output out1;

	assign out1 = a & b & c &d &e &f;
	//assign out2 =  f | d | e;

endmodule 
