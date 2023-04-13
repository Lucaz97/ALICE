import os
import logging
import logging.handlers
import sys
class RedactionConfig:

    def __init__(self, yaml_opt, file_list):
        self.topmodule = yaml_opt["topmodule"]
        self.include = yaml_opt["include"]
        self.define = yaml_opt["define"]
        self.strategy = yaml_opt["method"]
        self.not_allowed_size = []
        self.exclude_modules = yaml_opt["exclude_modules"]
        if yaml_opt["not_allowed_size"]:
            self.not_allowed_size = yaml_opt["not_allowed_size"]
        else:
            self.not_allowed_size.append(3)
        self.module_names = yaml_opt["module_names"]
        self.signal_names = []
        if yaml_opt["signal_names"]:
            with open(yaml_opt["signal_names"], "r") as f:
                for line in f:
                    self.signal_names.append(line if line[-1 ] != '\n' else line[:-1])
                
        self.max_io_num = int(yaml_opt["max_io_num"]) if yaml_opt["max_io_num"] is not None else None
        self.file_list = file_list
        self.max_fpga_num = int(yaml_opt["max_fpga_num"]) if yaml_opt["max_fpga_num"] is not None else None
        self.max_instances = 30
        self.rank = float(yaml_opt["rank"]) if yaml_opt["rank"] is not None else None
        # setup work dir
        os.makedirs(yaml_opt["out_dir"], exist_ok=True)
        self.target = yaml_opt["out_dir"]
        self.vpr_arch = yaml_opt["vpr_arch"]
        self.openfpga_arch = yaml_opt["openfpga_arch"]
        

        # Change root logger level from WARNING (default) to NOTSET in order for all messages to be delegated.
        logging.getLogger().setLevel(logging.NOTSET)
        # Add stdout handler, with level INFO
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)
        # Add file assure handler, with level DEBUG
        rotatingHandler = logging.handlers.RotatingFileHandler(filename=self.target + '/redaction_flow.log', mode='w')
        rotatingHandler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)-8s: %(message)s')
        rotatingHandler.setFormatter(formatter)
        logging.getLogger().addHandler(rotatingHandler)
        self.log = logging.getLogger(self.target + '/redaction_flow.log')
        self.is_log = True

    def logInfo(self, msg):
        self.log.info(msg)

    def logWarming(self, msg):
        self.log.warning(msg+"\n")

    def logDebug(self, msg):
        self.log.debug(msg+"\n")

    def logError(self, msg):
        self.log.error(msg+"\n")