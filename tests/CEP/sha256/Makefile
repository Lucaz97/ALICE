run:
	@rm -rf work
	@cd src; python3 ../../../../src/redaction.py -t sha256 -m io+out+rank -r 1 -p 96 -n ../outfile -f 2 sha256.v sha256_k_constants.v   sha256_top_wb.v  sha256_w_mem.v sha256_top_axi4lite.v
clean:
	@rm -rf work   
