from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import shutil
import copy
import pathlib
from optparse import OptionParser
import os.path
from xml.dom import minidom
import yaml

from RedactionModuleFinder import RedactionModuleFinder
import pyverilog.vparser.ast as vast
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
from OpenFpgaAnalyzer import OpenFpgaAnalyzer
from RedactionInfo import RedactionInfo
from RedactionConfig import RedactionConfig
import RedactionUtils


# the next line can be removed after installation
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def cmd_parsing():
    help_text = """Usage: redaction.py [options] [files]
        Apply FPGA redaction on the given Verilog sources.
        More than one redaction methods are available.
        """
    optparser = OptionParser(usage=help_text)
    #optparser.add_option("-f", "--yaml_opt", dest="yaml_file", action="store", default="options.yaml", help="Option file in YAML format.")
    optparser.add_option("-I", "--include", dest="include", action="append",
                         default=[], help="Include path")
    optparser.add_option("-D", dest="define", action="append",
                         default=[], help="Macro Definition")
    optparser.add_option("-t", "--top", dest="topmodule",
                         default="TOP", help="Top module's name, default: TOP")
    '''
    optparser.add_option("--nobind", action="store_true", dest="nobind",
                         default=False, help="No binding traversal, Default=False")
    optparser.add_option("--noreorder", action="store_true", dest="noreorder",
                         default=False, help="No reordering of binding dataflow, Default=False")
    '''
    REDACTION_METHODS = ["io+out+rank", "io+module"]
    choices_m = REDACTION_METHODS
    optparser.add_option("-m", "--method", dest="method",
                         default="io+out+rank", choices=choices_m, help="Redaction module's method, default: sharing; "
                                                                    "'output' = given a certain output signal, "
                                                                    "looks for module which impact on it; "
                                                                    "'sharing' = looks for module which impact "
                                                                    "the most on other modules"
                                                                    "'io_pin' = max i/o pin constraint"
                                                                    "'io+out+rank'  = max pin, output signals of interests, rank and filter for best"
                                                                    "'io+module' = max pin and module of interest")
    optparser.add_option("-n", "--signal_name", dest="signal_names",
                         help="File with output signal to look for dependencies, when method 'output' is selected")
    optparser.add_option("-p", "--max_io_num", dest="max_io_num",
                         help="Max number of io which is acceptable for redacted fpga")
    optparser.add_option("-s", "--size", dest="not_allowed_size", action="append", type="int",
                         help="Allowed size of redacted fpga")
    optparser.add_option("-f", "--max_fpga_num", dest="max_fpga_num",
                         help="Max number of fpgas which is acceptable for redacted fpga", default=1)
    optparser.add_option("-r", "--rank", dest="rank",
                         help="Percentage of ranked modules to consider [0, 1]", default=1)
    optparser.add_option("--dir", dest="out_dir", help="Defines the output directory, default = work", default="../work")
    optparser.add_option("-e", "--exclude", dest="exclude_modules", action="append",
                         help="prefixes to exclude", default=[])
    optparser.add_option("-M", "--mod", dest="module_names", action="append",
                         help="relevant modules (for io+module)", default=[])
    
    (options, args) = optparser.parse_args()

    # to convert old make files 
    stream = open('../options.yaml', 'w')
    yaml.dump(options, stream)
    quit()


    if not os.path.exists(options.yaml_file):
        raise ValueError("Error: options file not found:", options.yaml_file)

    stream = open(options.yaml_file, 'r')
    yaml_opt = yaml.safe_load(stream)

    if yaml_opt["method"] == "io+out+rank":
        if not yaml_opt["signal_names"]:
            raise ValueError("Error: No output signal name specified")
        if not os.path.exists(yaml_opt["signal_names"]):
            raise ValueError("Error: No output signal name file is not valid: " + yaml_opt["signal_names"])
        if not yaml_opt["max_io_num"]:
            raise ValueError("Error: max number of pins has not been provided")

    file_list = yaml_opt["file_list"]
    for f in file_list:
        if not os.path.exists(f):
            raise IOError("file not found: " + f)
    return yaml_opt, file_list


def fix_instances(RedactionInfo, to_fix, mpm, p_it, new_assign, with_def):
    while to_fix != mpm:
        # find instancing of to_fix in to_fix parent
        parent_node = RedactionInfo.getParentModuleNodeByInstanceName(to_fix)
        new_items = ()

        for it in parent_node.items:
            if isinstance(it, vast.InstanceList):
                instances = ()
                for it_it in it.instances:
                    if it_it.name == str(to_fix[-1]):
                        it_it.portlist += (vast.PortArg(new_assign, vast.Identifier(new_assign)),)
        # if to_fix[:-1] is not mpm i need to add the wires and the assigns as well
        if to_fix[:-1] != mpm:
            #new_items += (vast.Wire(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed)),)
            if isinstance(p_it, vast.Input):
                if with_def:
                    parent_node.portlist.ports += (vast.Ioport(vast.Output(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None),
                                                            vast.Wire(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None)),)
                else:
                    parent_node.portlist.ports += (vast.Port(new_assign, None, None, None),)
                    parent_node.items += (vast.Decl([vast.Input(new_assign, None, None, None)]),)
                #new_items += (vast.Assign(vast.Identifier(new_assign), arg_it.argname),)
            else:
                if with_def:
                    parent_node.portlist.ports += (vast.Ioport(vast.Input(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None),
                                                            vast.Wire(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None)),)
                else:
                    parent_node.portlist.ports += (vast.Port(new_assign, None, None, None),)
                    parent_node.items += (vast.Decl([vast.Output(new_assign, None, None, None)]),)
                #new_items += (vast.Assign(arg_it.argname, vast.Identifier(new_assign)),)

        parent_node.items += new_items
        to_fix = to_fix[:-1]


def renameModulesInDir(directory, name, name_changes, efpga_name):
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    for file in files:
        isNext = False
        with open(file, 'r') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            if isNext:
                to_replace = lines[i].split(" ")[1].split("(")[0]
                lines[i] = lines[i].replace(to_replace, name+"_"+to_replace, 1)
                name_changes[to_replace] = name+"_"+to_replace
                isNext = False
            if "// ----- Verilog module" in lines[i]:
                isNext = True
        with open(file, 'w') as f:
            f.writelines(lines)
    if efpga_name:
        for file in files:
            os.rename(file, str(pathlib.Path(file).parent.resolve()) + "/" + efpga_name + "_" + str(os.path.basename(file)))

def renameModulesInDirOpenFPGA(directory, name, name_changes, efpga_name):
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    for file in files:
        isNext = False
        with open(file, 'r') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            if "module " in lines[i] and " (" in lines[i]:
                to_replace = lines[i].split(" ")[1]
                lines[i] = lines[i].replace(to_replace, name+"_"+to_replace)
                name_changes[to_replace] = name+"_"+to_replace
        with open(file, 'w') as f:
            f.writelines(lines)
    if efpga_name:
        for file in files:
            os.rename(file, str(pathlib.Path(file).parent.resolve()) + "/" + efpga_name + "_" + str(os.path.basename(file)))

def fixModuleInstances(directory, name_changes, efpga_name):
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    for file in files:
        isNext = False
        with open(file, 'r') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            if " (" in lines[i]:
                # try to get instance name if exist change it
                instance_name = lines[i].split(" ")[-3].lstrip()
                if instance_name in name_changes.keys():
                    lines[i] = lines[i].replace(instance_name, name_changes[instance_name])
        with open(file, 'w') as f:
            f.writelines(lines)
    if efpga_name:
        for file in files:
            os.rename(file, str(pathlib.Path(file).parent.resolve()) + "/" + efpga_name + "_" + str(os.path.basename(file)))

def fixIncludeNames(file, efpga_name):
    with open(file, 'r') as f:
        lines = f.readlines()
    for i in range(len(lines)):
        if not "`include" in lines[i]: continue
        lines[i] = lines[i].replace("./SRC", "./" + efpga_name)
        lines[i] = lines[i].replace("routing/", "routing/" + efpga_name + "_")
        lines[i] = lines[i].replace("lb/", "lb/" + efpga_name + "_")
        lines[i] = lines[i].replace("sub_module/", "sub_module/" + efpga_name + "_")
        lines[i] = lines[i].replace("fpga_defines.v", efpga_name + "_fpga_defines.v")
        lines[i] = lines[i].replace("fpga_top.v", efpga_name + ".v")
        lines[i] = lines[i].replace(os.getenv('OPENFPGA_FLOW_PATH'), "./" + efpga_name+"/")
        lines[i] = lines[i].replace("/verilog/", "/verilog/" + efpga_name + "_")
    with open(file, 'w') as f:
        f.writelines(lines)

def fixSDCFiles(directory, name_changes, efpga_name):
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    for file in files:
        isNext = False
        with open(file, 'r') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            # updated old names
            for name in name_changes.keys():
                if name in lines[i]:
                    lines[i] = lines[i].replace(name, name_changes[name])
                    break
            # add prefix to starred occurrences 
            if "/" in lines[i] and "*" in lines[i]:
                splitted = lines[i].split("/")
                for o in range(len(splitted)):
                    if "*" in splitted[o]:
                        splitted[o] = efpga_name + splitted[o]
                lines[i] = "/".join(splitted)
            
        with open(file, 'w') as f:
            f.writelines(lines)
    if efpga_name:
        for file in files:
            os.rename(file, str(pathlib.Path(file).parent.resolve()) + "/" + efpga_name + "_" + str(os.path.basename(file)))


def createOutputFiles(RedactionInfo, redaction_instances):
    out_dir = RedactionInfo.redactionConfig.target + "/OUT"
    os.makedirs(out_dir, exist_ok=True)

    asic_ast = RedactionInfo.ast
    efpga_counter = 0

    for k in redaction_instances.selected:
        os.makedirs(out_dir + "/" + k.name, exist_ok=True)
        with open(k.openfpga_dest + "/SRC/fpga_top.v", 'r') as file : filedata = file.read()
        filedata = filedata.replace('module fpga_top', 'module ' + k.name)
        with open(out_dir + "/" + k.name + "/" + k.name + ".v", 'w') as file: file.write(filedata)
        RedactionInfo.redactionConfig.logInfo("eFPGA to be generated")
        RedactionInfo.redactionConfig.logInfo(k.name)
        RedactionInfo.redactionConfig.logInfo(str(k.modules_to_extract))
        shutil.copyfile(k.openfpga_dest + "/SRC/fpga_defines.v", out_dir + "/" + k.name + "/" + k.name + "_fpga_defines.v")
        shutil.copyfile(k.openfpga_dest + "/SRC/fabric_netlists.v", out_dir + "/" + k.name + "_fabric_netlists.v")
        shutil.copytree(k.openfpga_dest + "/SRC/lb", out_dir + "/" + k.name + "/lb")
        shutil.copytree(k.openfpga_dest + "/SRC/routing", out_dir + "/" + k.name + "/routing")
        shutil.copytree(k.openfpga_dest + "/SRC/sub_module", out_dir + "/" + k.name + "/sub_module")
        shutil.copytree(k.openfpga_dest + "/SDC", out_dir + "/" + k.name + "/SDC")
        # copy os.getenv('OPENFPGA_FLOW_PATH') + openfpga_cell_library/verilog
        shutil.copytree( os.getenv('OPENFPGA_FLOW_PATH') + "/openfpga_cell_library/verilog", out_dir + "/" + k.name + "/openfpga_cell_library/verilog")
       
        #  rename all auxilary modules
        # keep track of name changes {original: new}
        name_changes = {"fpga_top": k.name}
        renameModulesInDir(out_dir + "/" + k.name + "/routing", k.name, name_changes, k.name)
        renameModulesInDir(out_dir + "/" + k.name + "/lb", k.name, name_changes, k.name)
        renameModulesInDir(out_dir + "/" + k.name + "/sub_module", k.name, name_changes, k.name)
        renameModulesInDirOpenFPGA( out_dir + "/" + k.name + "/openfpga_cell_library/verilog", k.name, name_changes, k.name)
        fixModuleInstances(out_dir + "/" + k.name + "/routing", name_changes, None)
        fixModuleInstances(out_dir + "/" + k.name + "/lb", name_changes, None)
        fixModuleInstances(out_dir + "/" + k.name + "/sub_module", name_changes, None)
        fixModuleInstances(out_dir + "/" + k.name + "/openfpga_cell_library/verilog", name_changes, None)
        fixModuleInstances(out_dir + "/" + k.name, name_changes, None) # fix insances of the efpga fabric too
        fixIncludeNames(out_dir + "/" + k.name + "_fabric_netlists.v", k.name) # fix insances of the efpga fabric too
        fixSDCFiles(out_dir + "/" + k.name + "/SDC", name_changes, k.name)

        io_file = k.openfpga_dest + "/io_mapping.xml"
        if not os.path.exists(io_file): raise Exception("IO mapping not found: " + io_file) 
        net_file = k.openfpga_dest + "/netlist_renaming.xml"
        if not os.path.exists(net_file): raise Exception("netlist renaming not found: " + net_file) 

        mpm = RedactionUtils.findMCP(k.modules_to_extract)
        print("MPM:", mpm)
        new_ports = ()
        new_decl = ()
        with_def = True
        for p in RedactionInfo.getModuleNodeByInstanceName(mpm).portlist.ports:
            if isinstance(p, vast.Port): with_def = False
        #find instances in ASIC module by following the scope and remove them
        for p in k.modules_to_extract:
            parent_node = RedactionInfo.getParentModuleNodeByInstanceName(p)

            new_items = ()
            for it in parent_node.items:
                if isinstance(it, vast.InstanceList):
                    instances = ()
                    for it_it in it.instances:
                        if it_it.name != str(p[-1]):
                            instances += (it_it,)
                        else:
                            ports = RedactionInfo.getModuleIOPortsNodes(RedactionInfo.getModuleByInstanceName(p))
                            for p_it in ports: 
                                for arg_it in it_it.portlist:
                                    if arg_it.portname == p_it.name:
                                        new_assign = str(p).replace(".", "_") + "_" + p_it.name
                                        if isinstance(p_it, vast.Input):
                                            new_items += (vast.Assign(vast.Identifier(new_assign), arg_it.argname),)
                                        else:
                                            new_items += (vast.Assign(arg_it.argname, vast.Identifier(new_assign)),)
                                        
                                        new_decl += (vast.Wire(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed)),)
                                        if p[:-1] != mpm: 
                                            # parent module is not the minimum common parent
                                            #  we need to expose the signals to the parent module
                                            if isinstance(p_it, vast.Input):
                                                if with_def:
                                                    parent_node.portlist.ports += (vast.Ioport(vast.Output(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None),
                                                                                           vast.Wire(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None)),)
                                                else:
                                                    parent_node.portlist.ports += (vast.Port(new_assign, None, None, None),)
                                                    parent_node.items += (vast.Decl([vast.Input(new_assign, None, None, None)]),)
                                            else:
                                                if with_def:
                                                    parent_node.portlist.ports += (vast.Ioport(vast.Input(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None),
                                                                                           vast.Wire(new_assign, copy.deepcopy(p_it.width), copy.deepcopy(p_it.signed), None)),)
                                                else:
                                                    parent_node.portlist.ports += (vast.Port(new_assign, None, None, None),)
                                                    parent_node.items += (vast.Decl([vast.Output(new_assign, None, None, None)]),)
                                            # need to fix above instancing
                                            to_fix = p[:-1]
                                            # propagate signals from instances to eFPGA instance
                                            fix_instances(RedactionInfo, to_fix, mpm, p_it, new_assign, with_def)

                    it.instances = instances
                    if it.instances: new_items += (it,)
                else:
                    new_items += (it,)
            parent_node.items = new_items

        #add eFPGA instance
        module = RedactionInfo.getModuleNodeByInstanceName(mpm)
        instance_list = vast.InstanceList(k.name, [], [])
        instance = vast.Instance(k.name, "i_" + str(efpga_counter), [], [])
        #add correct port mapping to eFPGA instance
        my_io_xml = minidom.parse(io_file)
        my_net_xml = minidom.parse(net_file)
        io_items = my_io_xml.getElementsByTagName('io')
        net_items = my_net_xml.getElementsByTagName('block')
        for io in io_items:
            net = io.attributes['net'].value
            name = io.attributes['name'].value 
            assign = None
            if io.attributes['dir'].value == "input":
                found = False
                for net_it in net_items:
                    if net_it.attributes['current'].value == net: 
                        assign = vast.Assign(vast.Identifier(k.name + "_" + name), vast.Identifier(net_it.attributes['previous'].value))
                        found = True
                if not found: assign = vast.Assign(vast.Identifier(k.name + "_" + name), vast.Identifier(net))
            elif io.attributes['dir'].value == "output":
                found = False
                for net_it in net_items:
                    if net_it.attributes['current'].value == "out_" + net: 
                        assign = vast.Assign(vast.Identifier(net_it.attributes['previous'].value[4:]), vast.Identifier(k.name + "_" + name))
                        found = True
                if not found: assign = vast.Assign(vast.Identifier(net), vast.Identifier(k.name + "_" + name))
            else:
                raise Exception("not supported")
            if assign: module.items += (assign,)

        instance.portlist.append(vast.PortArg("pReset", vast.Identifier(k.name + "_pReset")))
        instance.portlist.append(vast.PortArg("prog_clk", vast.Identifier(k.name + "_prog_clk")))
        instance.portlist.append(vast.PortArg("set", vast.Identifier(k.name + "_set")))
        instance.portlist.append(vast.PortArg("clk", vast.Identifier(k.name + "_clk")))
        instance.portlist.append(vast.PortArg("gfpga_pad_GPIO_PAD", vast.Identifier(k.name + "_gfpga_pad_GPIO_PAD")))
        instance.portlist.append(vast.PortArg("ccff_head", vast.Identifier(k.name + "_ccff_head")))
        instance.portlist.append(vast.PortArg("ccff_tail", vast.Identifier(k.name + "_ccff_tail")))

        max_io_pad = 0
        #get_max_io_pad
        log_file = open(k.openfpga_dest + "/openfpgashell.log", 'r')
        Lines = log_file.readlines()
        Arch = False
        for line in Lines:
            if Arch and "blocks of type: io" in line:
                token = line.split("blocks of type: io",1)[0].strip()
                if int(token) > max_io_pad: max_io_pad = int(token)
            if "Architecture" in line:
                Arch = True
            else:
                Arch = False

        
        if with_def:
            new_ports += (vast.Ioport(vast.Input(k.name + "_pReset", None, None, None),
                                      vast.Wire(k.name + "_pReset", None, None, None)),)
            new_ports += (vast.Ioport(vast.Input(k.name + "_prog_clk", None, None, None),
                                      vast.Wire(k.name + "_prog_clk", None, None, None)),)
            new_ports += (vast.Ioport(vast.Input(k.name + "_set", None, None, None),
                                      vast.Wire(k.name + "_set", None, None, None)),)
            new_ports += (vast.Ioport(vast.Input(k.name + "_clk", None, None, None),
                                      vast.Wire(k.name + "_clk", None, None, None)),)
            new_ports += (vast.Ioport(vast.Input(k.name + "_ccff_head", None, None, None),
                                      vast.Wire(k.name + "_ccff_head", None, None, None)),)
            new_ports += (vast.Ioport(vast.Output(k.name + "_ccff_tail", None, None, None),
                                      vast.Wire(k.name + "_ccff_tail", None, None, None)),)
        else:
            new_ports += (vast.Port(k.name + "_pReset", None, None, None),)
            new_ports += (vast.Port(k.name + "_prog_clk", None, None, None),)
            new_ports += (vast.Port(k.name + "_set", None, None, None),)
            new_ports += (vast.Port(k.name + "_clk", None, None, None),)
            new_ports += (vast.Port(k.name + "_ccff_head", None, None, None),)
            new_ports += (vast.Port(k.name + "_ccff_tail", None, None, None),)
            new_decl += (vast.Decl([vast.Input(k.name + "_pReset", None, None, None)]),)
            new_decl += (vast.Decl([vast.Input(k.name + "_prog_clk", None, None, None)]),)
            new_decl += (vast.Decl([vast.Input(k.name + "_set", None, None, None)]),)
            new_decl += (vast.Decl([vast.Input(k.name + "_clk", None, None, None)]),)
            new_decl += (vast.Decl([vast.Input(k.name + "_ccff_head", None, None, None)]),)
            new_decl += (vast.Decl([vast.Output(k.name + "_ccff_tail", None, None, None)]),)
        new_decl += (vast.Decl([vast.Wire(k.name + "_gfpga_pad_GPIO_PAD", vast.Width(vast.IntConst(max_io_pad-1), vast.IntConst(0)), None, None)]),)


        module.portlist.ports = new_ports + module.portlist.ports
        module.items = new_decl + module.items

        instance_list.instances.append(instance)
        module.items += (instance_list,)

        # propagate efpga signals to top module
        to_fix = mpm
        while str(to_fix) != RedactionInfo.redactionConfig.topmodule:
            # we have not got to the top module yet- 
            module = RedactionInfo.getParentModuleNodeByInstanceName(to_fix)
            for it in module.items:
                if isinstance(it, vast.InstanceList):
                    instances = ()
                    for it_it in it.instances:
                        print("Instance name:",it_it.name)
                        print("to_fix:", str(to_fix[-1]))
                        if it_it.name == str(to_fix[-1]):
                            it_it.portlist += (vast.PortArg(k.name + "_pReset", vast.Identifier(k.name + "_pReset")),)
                            it_it.portlist += (vast.PortArg(k.name + "_prog_clk", vast.Identifier(k.name + "_prog_clk")),)
                            it_it.portlist += (vast.PortArg(k.name + "_set", vast.Identifier(k.name + "_set")),)
                            it_it.portlist += (vast.PortArg(k.name + "_clk", vast.Identifier(k.name + "_clk")),)
                            it_it.portlist += (vast.PortArg(k.name + "_ccff_head", vast.Identifier(k.name + "_ccff_head")),)
                            it_it.portlist += (vast.PortArg(k.name + "_ccff_tail", vast.Identifier(k.name + "_ccff_tail")),)

            if with_def:
                module.portlist.ports += (vast.Ioport(vast.Input(k.name + "_pReset", None, None, None),
                                        vast.Wire(k.name + "_pReset", None, None, None)),)
                module.portlist.ports += (vast.Ioport(vast.Input(k.name + "_prog_clk", None, None, None),
                                        vast.Wire(k.name + "_prog_clk", None, None, None)),)
                module.portlist.ports += (vast.Ioport(vast.Input(k.name + "_set", None, None, None),
                                        vast.Wire(k.name + "_set", None, None, None)),)
                module.portlist.ports += (vast.Ioport(vast.Input(k.name + "_clk", None, None, None),
                                        vast.Wire(k.name + "_clk", None, None, None)),)
                module.portlist.ports += (vast.Ioport(vast.Input(k.name + "_ccff_head", None, None, None),
                                        vast.Wire(k.name + "_ccff_head", None, None, None)),)
                module.portlist.ports += (vast.Ioport(vast.Output(k.name + "_ccff_tail", None, None, None),
                                        vast.Wire(k.name + "_ccff_tail", None, None, None)),)
            else:
                module.portlist.ports += (vast.Port(k.name + "_pReset", None, None, None),)
                module.portlist.ports += (vast.Port(k.name + "_prog_clk", None, None, None),)
                module.portlist.ports += (vast.Port(k.name + "_set", None, None, None),)
                module.portlist.ports += (vast.Port(k.name + "_clk", None, None, None),)
                module.portlist.ports += (vast.Port(k.name + "_ccff_head", None, None, None),)
                module.portlist.ports += (vast.Port(k.name + "_ccff_tail", None, None, None),)
                module.items += (vast.Decl([vast.Input(k.name + "_pReset", None, None, None)]),)
                module.items += (vast.Decl([vast.Input(k.name + "_prog_clk", None, None, None)]),)
                module.items += (vast.Decl([vast.Input(k.name + "_set", None, None, None)]),)
                module.items += (vast.Decl([vast.Input(k.name + "_clk", None, None, None)]),)
                module.items += (vast.Decl([vast.Input(k.name + "_ccff_head", None, None, None)]),)
                module.items += (vast.Decl([vast.Output(k.name + "_ccff_tail", None, None, None)]),)
            to_fix = to_fix[:-1]
        
        efpga_counter += 1
    # end for 

    filename = out_dir + "/" + RedactionInfo.redactionConfig.topmodule + ".v"
    outfile = open(filename, 'w')
    codegen = ASTCodeGenerator()
    print(codegen.visit(asic_ast), file=outfile)
    outfile.close()
# end createOutputFiles


def main():
    # Command line parsing
    yaml_opt, file_list = cmd_parsing()
 
    is_openfpga = os.getenv('OPENFPGA_FLOW_PATH', default=None)
    if not is_openfpga: raise Exception("OPENFPGA_FLOW_PATH variable not defined")
    print(is_openfpga)

    cfg = RedactionConfig(yaml_opt, file_list)
    redaction_info = RedactionInfo(cfg)
    # Find redaction modules candidates
    redaction_module_finder = RedactionModuleFinder(cfg, redaction_info)
    redaction_module_finder.find()

    # Run OpenFPGA flow for each of them
    #while redaction_module_finder.empty is False:
    #    red_module_verilog_file, top, dest = redaction_module_finder.pop_and_redact()
    #    dest = dest + "/../openfpga_work"
    #    os.mkdir(dest)
    #    openfpga_analyzer = OpenFpgaAnalyzer(red_module_verilog_file, top, dest)
    #    openfpga_analyzer.run()
    #    openfpga_analyzer.read_log() # Read results of the run
    #    # TODO: perform the improvement of the architecture

    # create Top module and output files
    createOutputFiles(redaction_info, redaction_module_finder.redaction_instances)

    # find ./ -type f -exec sed -i -e 's/`default_nettype none/\/\/`default_nettype none/g' {} \;
    os.system("find "+yaml_opt["out_dir"]+"/OUT/ -type f -exec sed -i -e 's/`default_nettype none/\/\/`default_nettype none/g' {} \;")
    # find work/OUT/ -type f -exec sed -i -e "s/(in === 1'bz)? \$random : ~in;/(in == 1'bz)? 1'b0 : ~in;/g" {} \;
    os.system("find "+yaml_opt["out_dir"]+"/OUT/ -type f -exec sed -i -e \"s/(in === 1'bz)? \$random : ~in;/ ~in;/g\" {} \;")
    os.system("find "+yaml_opt["out_dir"]+"/OUT/ -type f -exec sed -i -e \"s/(in === 1'bz)? \$random : in;/ in;/g\" {} \;")


if __name__ == '__main__':
    main()
