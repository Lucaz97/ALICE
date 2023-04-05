import copy
import pyverilog.vparser.ast as vast


def fpga_redaction(ast, redaction_instances, frame_table):
    """

    Starting from an AST and from the instances to redact,
    it generates two different new ASTs, according to the carried out redaction

    NOTE: in this version of the code, redaction modules are examined one by time
    Anyway, this has been coded to be extensible
    """

    # Perform deep copy of the original ast
    ast_ASIC = copy.deepcopy(ast)
    ast_FPGA = copy.deepcopy(ast)

    # List of ModuleDef objects
    modules_list = find_child_class(ast_FPGA.description, "ModuleDef")

    # HYP: all submodules of FPGA redaction modules will go into FPGA as well
    # So if there are some instances whose parent instance has been selected as well
    # just consider this last one.
    instances = list(redaction_instances.keys())
    instances_to_remove = []
    for k in instances:
        for j in instances:
            if (j != k) and (j in k):
                instances_to_remove.append(k)
    instances_to_remove = list(dict.fromkeys(instances_to_remove))
    for r in instances_to_remove:
        redaction_instances.pop(r)
    ####

    ### TEST for openFPGA flow
    k = instances[-1]
    redaction_instances = {k: redaction_instances[k]}
    TOP = redaction_instances[k] + "_FPGA"
    ###

    # Finds names of redaction modules
    redaction_modules_names = []  # List of redaction modules names
    fpga_modules_names = []  # List of redaction modules and their submodules names
    for module in modules_list:
        # print(module_num_ff_inferr(module,modules_list))
        # print(module_num_io(module))
        if is_redaction_module(module, redaction_instances):
            redaction_modules_names.append(module.name)
            fpga_modules_names.extend(find_all_submodules(module, modules_list))
            fpga_modules_names.append(module.name)

    fpga_modules_names = list(dict.fromkeys(fpga_modules_names))  # Delete duplicates TODO set??
    redaction_modules_names = list(dict.fromkeys(redaction_modules_names))
    fpga_submodules_list = [mod for mod in fpga_modules_names if mod not in redaction_modules_names]
    # Adjust the definitions of FPGA ast

    definitions_list = list(ast_FPGA.description.definitions)
    # Remove the not-in-FPGA modules
    for module in modules_list:
        if module.name not in fpga_modules_names:
            definitions_list.remove(module)
    # Update redaction modules (and submodules) names and references with the suffix "_FPGA"
    for defin in definitions_list:
        if isinstance(defin, vast.ModuleDef):
            defin.name = defin.name + "_FPGA"  # Modify module name
            # Modify instances name
            instance_list = find_child_class(defin, "InstanceList")
            for inst in instance_list:
                inst.module = inst.module + "_FPGA"
                # TODO review this
                inst.instances[0].module = inst.instances[0].module + "_FPGA"

    ast_FPGA.description.definitions = tuple(definitions_list)

    # Check if in asic_definitions there are some modules which are never instantiated
    modules_list = find_child_class(ast_ASIC.description, "ModuleDef")
    definitions_list = list(ast_ASIC.description.definitions)

    # For each redaction instance, it's necessary to find the other instances in its path
    # since the directly instantiating module has a different definition, due to subfix _FPGA
    # of submodule (redaction instance)
    for instance in redaction_instances.keys():
        inst_chain = instance.split(".")
        already_dup = False
        parentmodule = str_to_obj_module(inst_chain[0], modules_list)  # this should be actually the top module

        inst_c = inst_chain[0]
        for c in inst_chain[1:-1]:
            inst_c += "." + c  # recover the instance name in the frameTable
            keys = frame_table.dict.keys()
            for k in keys:  # this is done since the keys of this dictionaries are not strings
                if str(k) == inst_c:
                    modname = frame_table.dict[k].modulename
                    break
            module = str_to_obj_module(modname, modules_list)  # recover the moduleDef object of the instance

            # Duplication

            # 'already_dup' indicates if a previous module in the chain has already been duplicated
            # in such a case, the current module has to be duplicated in any case
            if already_dup is False:
                for mod in modules_list:
                    instanceList_list = find_child_class(mod, "InstanceList")
                    for inst in instanceList_list:
                        # if the instance is instantiated by other module than its parent module in the path
                        # or its parent module instantiates also a different instance
                        if (inst.module == modname) and (inst.instances[0].name != c or mod != parentmodule):
                            already_dup = True

            if already_dup is True:
                dup_mod = copy.deepcopy(module)
                definitions_list.insert(definitions_list.index(module), dup_mod)
                modules_list.insert(modules_list.index(module), dup_mod)
                module.name = module.name + "_r"
                frame_table.dict[k].modulename = frame_table.dict[k].modulename + "_r"

                # after duplication, the parent module's instances names must be updated
                instanceList_list = find_child_class(parentmodule, "InstanceList")  # module is a ModuleDef object
                for inst in instanceList_list:
                    if inst.instances[0].name == c:  # Find the instantiation
                        # Change the instance name, adding the suffix
                        inst.module = inst.module + "_r"
                        # TODO review this
                        inst.instances[0].module = inst.instances[0].module + "_r"

            parentmodule = module

        # the last piece in the chain is the effective redaction instance name
        fpga_instance_name = inst_chain[-1]
        # inst_c += "." + fpga_instance_name
        inst_c = instance

        keys = frame_table.dict.keys()
        for k in keys:
            if str(k) == inst_c:
                fpga_module_name = frame_table.dict[k].modulename
                break
        # fpga_module_name = redaction_instances[instance]
        fpga_module = str_to_obj_module(fpga_module_name, modules_list)

        # now add the subfix _FPGA to redaction instance instantiation
        instanceList_list = find_child_class(parentmodule, "InstanceList")  # module is a ModuleDef object
        for inst in instanceList_list:
            if inst.instances[0].name == fpga_instance_name:  # Find the instantiation
                # Change the instance name, adding the suffix
                inst.module = inst.module + "_FPGA"
                # TODO review this
                inst.instances[0].module = inst.instances[0].module + "_FPGA"

        # if the redaction instance module doesn't have instantiations inside ASIC
        # no need to be in asic ast
        to_delete = True
        if already_dup is False:
            for mod in modules_list:
                instanceList_list = find_child_class(mod, "InstanceList")
                for inst in instanceList_list:
                    # TODO review this, actually the definition of parentmodule has been changed
                    if (inst.module == fpga_module_name) and (inst.instances[
                                                                  0].name != fpga_instance_name or mod != parentmodule):  # then you need to duplicate the definition
                        to_delete = False

        if to_delete is True:
            definitions_list.remove(fpga_module)
            modules_list.remove(fpga_module)

    # all submodules of redaction modules, must be put in FPGA
    # need of verifying if there are other instantiations in asic
    # in the case, their definitions have to be in asic as well
    for submod_name in fpga_submodules_list:
        be_in_ASIC = False
        for defin in definitions_list:
            if isinstance(defin, vast.ModuleDef):
                instList_List = find_child_class(defin, "InstanceList")
                for i in instList_List:
                    if i.module == submod_name:
                        be_in_ASIC = True
                        break
        if be_in_ASIC is False:
            submod = str_to_obj_module(submod_name, modules_list)
            definitions_list.remove(submod)

    ast_ASIC.description.definitions = tuple(definitions_list)
    return TOP, ast_FPGA, ast_ASIC


def find_child_class(parent_node, class_name):
    """

    Starting from a node, returns a list of
    the child objects belonging to the given class

    """

    nodes = []
    if type(parent_node).__name__ == class_name:
        nodes.append(parent_node)

    for child in parent_node.children():
        nodes.extend(find_child_class(child, class_name))

    return nodes

def is_redaction_module(module, redaction_instances):
    """

    Select the strategy to apply for redaction:


    """
    """
    top_module_name = "SUB"
    return is_name_module(module, top_module_name)
    """
    return module.name in redaction_instances.values()


def find_submodules(module):
    """

    This finds the submodules (returns a list) which are directly instantiated by "module"
    """
    submodules_list = []
    instance_list = find_child_class(module, "InstanceList")
    for inst in instance_list:
        submodules_list.append(inst.module)
    return submodules_list


def find_all_submodules(module, modules_list):
    """

    This return all the submodules which are needed for "module"
    """
    submodules_list = []
    submodules_list.extend(find_submodules(module))
    for submod in submodules_list:
        for mod in modules_list:
            if mod.name == submod:
                submodules_list.extend(find_submodules(mod))
    return submodules_list


def str_to_obj_module(module_name, modules_list):
    """

    Returns the corresponding ModuleDef object, starting from its name

    """
    for module in modules_list:
        if module.name == module_name:
            return module
    return None