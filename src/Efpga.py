import os
import copy
import resource

from OpenFpgaAnalyzer import OpenFpgaAnalyzer

import pyverilog.vparser.ast as vast
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

class Efpga:
    def __init__(self, redactionInfo, modules_to_extract, name):
        self.redactionInfo = redactionInfo
        self.name = name
        self.modules_to_extract = modules_to_extract
        self.ast_fpga = None
        self.openfpga_dest = None
        self.openfpga_result = None
        self.security_result = None
        self.size = 3
        self.valid = False
        self.io_occupation_percentage = 0
        self.clb_occupation_percentage = 0
        self.time = None

    def build_wrapper(self):
        # build wrapper and assign to ast_fpga
        self.ast_fpga = copy.deepcopy(self.redactionInfo.ast)
        #for module in self.modules_to_extract:
        #    self.ast_fpga.definitions.append(copy.deepcopy(self.redactionInfo.getModuleNodeByInstanceName(module)))
        counter = 0
        top_ast = vast.ModuleDef(self.name, vast.Paramlist([]), vast.Portlist([]), [])
        instances = []
        for module in self.modules_to_extract:
            instance_list = vast.InstanceList(self.redactionInfo.getModuleByInstanceName(module), [], [])
            instance = vast.Instance(self.redactionInfo.getModuleByInstanceName(module), "i_" + str(counter), [], [])
            counter += 1
            module_ast = self.redactionInfo.getModuleNodeByInstanceName(module)
            ports = self.redactionInfo.getModuleIOPortsNodes(self.redactionInfo.getModuleByInstanceName(module))
            for p in ports: 
                p_top = copy.deepcopy(p)
                p_top.name = str(module).replace(".", "_") + "_" + p.name
                top_ast.portlist.ports.append(vast.Port(p_top.name, None, None, None))
                top_ast.items.append(vast.Decl([p_top]))
                instance.portlist.append(vast.PortArg(p.name, vast.Identifier(p_top.name)))
            instance_list.instances.append(instance)
            instances.append(instance_list)
        top_ast.items += instances
        self.ast_fpga.description.definitions += (top_ast,)

    def run_openfpga(self):
        # run OpenFPGA and set openfpga_result
        out_dir = self.redactionInfo.redactionConfig.target + "/" + self.name
        os.makedirs(out_dir, exist_ok=True)
        filename = out_dir + "/" + self.name + ".v"
        outfile = open(filename, 'w')
        codegen = ASTCodeGenerator()
        print(codegen.visit(self.ast_fpga), file=outfile)
        outfile.close()
        self.openfpga_dest = out_dir + "/openfpga_work"
        os.mkdir(self.openfpga_dest)
        openfpga_analyzer = OpenFpgaAnalyzer(filename, self.name, self.openfpga_dest, self.redactionInfo.redactionConfig)
        openfpga_analyzer.run()
        self.size, self.io_occupation_percentage, self.clb_occupation_percentage, self.valid = openfpga_analyzer.read_log()
    
    def run_security_analysis(self):
        #TODO: run sec analysis and set security_result
        # log in self.openfpga_dest+"/openfpgashell.log"
        # read io block utilization and size 
        pass

    
    def __repr__(self):
        return "EFPGA Obj: modules to extract -> " + " ".join(str(module) for module in (self.modules_to_extract))

class OpenFPGAResult:
    def __init__(self):
        # TODO: think about what needs to be stored in this class
        pass


class SecurityResult:
    def __init__(self):
        # TODO: think about what needs to be stored in this class
        pass