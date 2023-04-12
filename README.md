

# rtl_redaction

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Lucaz97/RTL-eFPGA-redaction/main?urlpath=vscode)

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

    in OpenFGPA home : export OPENFPGA_FLOW_PATH=$PWD/openfpga_flow
    
And the python interpreter for openfpga at OPENFPGA_PY_INT:
    export OPENFPGA_PY_INT=path/to/python/env
If you did not make a python environment for OpenFPGA, 
    export OPENFPGA_PY_INT=python3

And the RTL_REDACTION_PATH
    While in the root folder of this repo:
    export RTL_REDACTION_PATH=$PWD