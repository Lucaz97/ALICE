run:
	@rm -rf work
	@cd src; python3 ../../../../src/redaction.py -D src/timescale.v -t aes_cipher_top -m io+out+rank -r 1 -p 96 -n ../outfile  `ls *.v` 
clean:
	@rm -rf work 
