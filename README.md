

# ALICE: An automatic design flow for eFPGA redaction

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Lucaz97/ALICE/main?urlpath=vscode)

ALICE is a framework for eFPGA redaction. It helps identifying the best module combination to fit on the eFPGA with the fabric of your choice. you can either specify the relevant modules or select what outputs you want to protect and let ALICE do the work. 

If you use our tool for your research please cite us! 

    Tomajoli, C. M., Collini, L., Bhandari, J., Moosa, A. K. T., Tan, B., Tang, X., Gaillardon, P. E., Karri, R., & Pilato, C. (2022). 
    ALICE: An Automatic Design Flow for eFPGA Redaction. In Proceedings of the 59th ACM/IEEE Design Automation Conference,
    DAC 2022 (pp. 781-786). (Proceedings - Design Automation Conference). Institute of Electrical and Electronics Engineers Inc..  
    https://doi.org/10.1145/3489517.3530543

[OPEN ACCESS PAPER PDF](https://arxiv.org/pdf/2205.07425.pdf)

## Setting up ALICE:
The only requirement that you need to install for ALICE is OpenFPGA, you can find instructions on how to install OpenFPGA [HERE](https://openfpga.readthedocs.io/en/latest/tutorials/getting_started/compile/)

Before you run ALICE, you need to export the following environment variables, examples report bash syntax:

    export OPENFPGA_FLOW_PATH=path/to/OpenFPGA/openfpga_flow
in OpenFGPA home : 

    export OPENFPGA_FLOW_PATH=$PWD/openfpga_flow
    
    export OPENFPGA_PY_INT=path/to/python/env

If you did not make a dedicated python environment for OpenFPGA, 

    export OPENFPGA_PY_INT=python3

While in the root folder of this repo:

    export RTL_REDACTION_PATH=$PWD

If you want to try ALICE without committing to set up OpenFPGA yourself, you can open a ready to run binder by clicking on the Binder button at the top of this README. 
The binder will load our docker file taken from [OpenFPGA](https://github.com/lnis-uofu/OpenFPGA) and clone the later version of this repo. You can then cd in this repo and play with ALICE!

If you are familiar with Docker, you can also run the container locally on your machine.

# Run ALICE:
You can run one of our tests by entering in the specific test folder and run make. By default we read the options.yaml file, you can specify another yaml option file with the flag -f. 

Example from ALICE main folder:

    cd tests/CEP/fir
    make
 

## Configuration File
For a reference configuration file, please refer to tests/CEP/fir/options.yaml
