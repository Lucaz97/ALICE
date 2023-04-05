import os
import logging
import logging.handlers
import sys
class RedactionConfig:

    def __init__(self, options, file_list):
        self.topmodule = options.topmodule
        self.include = options.include
        self.define = options.define
        self.strategy = options.method
        self.not_allowed_size = []
        self.exclude_modules = options.exclude_modules
        if options.not_allowed_size:
            self.not_allowed_size = options.not_allowed_size
        else:
            self.not_allowed_size.append(4)
        self.module_names = options.module_names
        self.signal_names = []
        if options.signal_names:
            with open(options.signal_names, "r") as f:
                for line in f:
                    self.signal_names.append(line if line[-1 ] != '\n' else line[:-1])
                
        self.max_io_num = int(options.max_io_num) if options.max_io_num is not None else None
        self.file_list = file_list
        self.max_fpga_num = int(options.max_fpga_num) if options.max_fpga_num is not None else None
        self.max_instances = 30
        self.rank = float(options.rank) if options.rank is not None else None
        # setup work dir
        #os.mkdir(options.out_dir)
        os.makedirs(options.out_dir, exist_ok=True)
        self.target = options.out_dir

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