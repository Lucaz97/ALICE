# rtl_redaction
RTL redaction for eFPGA implementation


## Setting up a new test:
In the test folder create a makefile with the following structure:

    run:
        @rm -rf work
        @python3 ../../../src/redaction.py -t <top-module> -m output -n <output-signal> src/<verilog-files>

    clean:
        @rm -rf work


Before running make you should export the path to openfpga_flow to the environmtne variable "OPENFPGA_FLOW_PATH":

    export OPENFPGA_FLOW_PATH=path/to/OpenFPGA/openfpga_flow
    
