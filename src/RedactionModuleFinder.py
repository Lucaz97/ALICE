from pyverilog.vparser.parser import parse
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer

from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

from fpga_redaction_functions import *
from selection_algorithms import *
import RedactionUtils
import os

from abc import ABC, abstractmethod
from collections import Counter

import time

class RedactionModuleFinder:

    def __init__(self, cfg, design_info):
        self.cfg = cfg
        self.design_info = design_info
        self.redaction_instances = {}
        self.empty = True
        # create base dir for redaction
        self.base_dest = cfg.target + "/redaction_modules"
        os.mkdir(self.base_dest)
        self.count = 0  # counts number of redactions

    def find(self):
        # strategy pattern
        if self.cfg.strategy == "output":
            finder = Finder(ConcreteSelectionAlgorithmChooseByOutput(self.design_info.analyzer,
                                                                     self.cfg.signal_name, self.cfg.topmodule))
        elif self.cfg.strategy == "io_pins":
            finder = Finder(ConcreteSelectionAlgorithmChooseByNumberIo(self.design_info.instances.keys(), self.cfg.max_io_num, self.design_info))
        elif self.cfg.strategy == "io+out+rank":

            instances = []
            self.cfg.logInfo("FIRST FILTER: output influences")
            self.cfg.logInfo("Outputs of interest:"+str(self.cfg.signal_names))

            for signal_name in self.cfg.signal_names:

                finder = Finder(ConcreteSelectionAlgorithmChooseByOutput(self.design_info.analyzer,
                                                                        signal_name, self.cfg.topmodule, self.cfg.exclude_modules))
                found_instances = finder.apply().keys()
                self.cfg.logInfo("Instances affecting "+ str(signal_name) +": "+ str(found_instances))
                instances.extend(found_instances)
            counter = Counter(instances).most_common()
            
            n_instances = len(counter)
            n_passing = n_instances*self.cfg.rank if n_instances*self.cfg.rank > self.cfg.max_instances else  self.cfg.max_instances
            passing_instances = []
            for instance, count in counter[: n_passing]:
                passing_instances.append(self.design_info.getInstanceByName(instance))

            self.cfg.logInfo("Instances after output filter:" + str(passing_instances))
        
            finder = Finder(ConcreteSelectionAlgorithmChooseByNumberIo(passing_instances, self.cfg.max_io_num, self.design_info))
        elif self.cfg.strategy == 'io+module':
            instances = []
            self.cfg.logInfo("FIRST FILTER: relevant modules")
            self.cfg.logInfo("Modules of interest:"+str(self.cfg.module_names))

            for module_name in self.cfg.module_names:

                finder = Finder(ConcreteSelectionAlgorithmChooseByModule(self.design_info.analyzer,
                                                                        module_name, self.cfg.topmodule, self.cfg.exclude_modules))
                found_instances = finder.apply().keys()
                self.cfg.logInfo("Instances within "+ str(module_name) +": "+ str(found_instances))
                instances.extend(found_instances)
            counter = Counter(instances).most_common()
            
            n_instances = len(counter)
            n_passing = n_instances*self.cfg.rank if n_instances*self.cfg.rank > self.cfg.max_instances else  self.cfg.max_instances
            passing_instances = []
            for instance, count in counter[: n_passing]:
                passing_instances.append(self.design_info.getInstanceByName(instance))

            self.cfg.logInfo("Instances after output filter:" + str(passing_instances))
        
            finder = Finder(ConcreteSelectionAlgorithmChooseByNumberIo(passing_instances, self.cfg.max_io_num, self.design_info))
        else:
            finder = Finder(ConcreteSelectionAlgorithmChooseBySharing(self.design_info.analyzer, self.cfg.topmodule))
        self.redaction_instances = finder.apply()
        if self.redaction_instances != {}:
            self.empty = False

    def pop_and_redact(self):
        if self.redaction_instances != {}:
            red_mod_name, red_mod_type = self.redaction_instances.popitem()
            if self.redaction_instances == {}:
                self.empty = True
            # TODO: implement another class for keeping info about redaction results for each module?
            TOP, ast_FPGA, ast_ASIC = self.fpga_redaction(red_mod_name, red_mod_type)
            codegen = ASTCodeGenerator()
            rslt_ASIC = codegen.visit(ast_ASIC)
            rslt_FPGA = codegen.visit(ast_FPGA)

            # Setup redaction dir
            dest = self.base_dest + "/redaction_" + str(self.count)
            self.count += 1
            os.mkdir(dest)
            dest = dest + "/src"
            os.mkdir(dest)

            # Dump the resultant fpga verilog file
            f = open(dest+'/top.v', "w")
            f.write(rslt_FPGA)
            f.close()

            return rslt_FPGA, TOP, dest

    def fpga_redaction(self, red_mod_name, red_mod_type):
        return fpga_redaction(self.design_info.ast, {red_mod_name: red_mod_type}, self.design_info.frame_table)

# Implementation of Strategy pattern for the possible redaction module selection algorithm


# Strategy interface
class SelectionAlgorithm(ABC):
    @abstractmethod
    def execute(self):
        pass


# Context
class Finder:
    strategy: SelectionAlgorithm  # the strategy interface

    def __init__(self, strategy: SelectionAlgorithm):
        self.strategy = strategy

    def apply(self):
        return self.strategy.execute()


# Concrete strategies
class ConcreteSelectionAlgorithmChooseByOutput(SelectionAlgorithm):
    def __init__(self, analyzer, output_name, top_name, exclude):
        super().__init__()
        self.analyzer = analyzer
        self.output_name = output_name
        self.top_name = top_name
        self.exclude = exclude

    def execute(self):
        return choose_by_output(self.analyzer, self.output_name, self.top_name, self.exclude)


class ConcreteSelectionAlgorithmChooseByModule(SelectionAlgorithm):
    def __init__(self, analyzer, module_name, top_name, exclude):
        super().__init__()
        self.analyzer = analyzer
        self.module_name = module_name
        self.top_name = top_name
        self.exclude = exclude
    def execute(self):
        return choose_by_module(self.analyzer, self.module_name, self.top_name, self.exclude)



class ConcreteSelectionAlgorithmChooseBySharing(SelectionAlgorithm):
    def __init__(self, analyzer, top_name):
        super().__init__()
        self.analyzer = analyzer
        self.top_name = top_name

    def execute(self):
        return choose_by_sharing(self.analyzer, self.top_name)


class ConcreteSelectionAlgorithmChooseByNumberIo(SelectionAlgorithm):
    def __init__(self, instances, max_io_num, design_info):
        super().__init__()
        self.instances = instances
        self.max_io_num = max_io_num
        self.design_info = design_info

    def execute(self):
        return choose_by_number_IO(self.instances, self.max_io_num, self.design_info)

