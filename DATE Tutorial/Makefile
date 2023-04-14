run: 2small

2small: clean 
	@python3 ../src/redaction.py -f 2_small_efpgas.yaml
	
1big: clean
	@python3 ../src/redaction.py -f 1_bigger_efpga.yaml

clean:
	@rm -rf work
