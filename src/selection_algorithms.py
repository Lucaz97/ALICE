import pyverilog.vparser.ast as vast
from collections import OrderedDict
from Efpga import *
from RedactionUtils import *
import time

"""
Add here functions implementing a strategy for selecting the redaction methods
"""

def choose_by_module(analyzer, module_name, top_name, exclude):
    print("Performing choice based on module: {0}".format(module_name))
    instances_tuple = analyzer.getInstances()  # tuple of (instance scope chain, module name)
   
    # we want to find all the instances within module_name
    instance_module_dict_ordered = OrderedDict()
    for instance, module in instances_tuple:
        if module == module_name:
            instance_module_dict_ordered[str(instance)] = module
    
    for rel_instance in instance_module_dict_ordered.keys():
        for instance, module in instances_tuple:
            if str(instance).startswith(rel_instance) and not any((module.startswith(e) for e in exclude)):
                instance_module_dict_ordered[str(instance)] = module

    return instance_module_dict_ordered

def choose_by_output(analyzer, output_name, top_name, exclude):
    print("Performing choice based on output: {0}".format(output_name))
    output_name = top_name + "." + output_name  # reconstruct the signal name in the scope-chain

    instances_tuple = analyzer.getInstances()  # tuple of (instance scope chain, module name)
    instance_module_dict = {}  # key = instance name; value = module name
    for inst, module in instances_tuple:  # create a dict from the tuple
        # instance_module_dict.update({str(inst): module})
        instance_module_dict[str(inst)] = module

    # Find inputs of top module
    top_inputs = []
    signals = analyzer.getSignals()  # contains all signals in the design
    for k in signals.keys():
        # if it's a signal of top module, the scope-chain is of length = 2
        # i.e. top_module_name.io_name
        if len(k) == 2 and isinstance(signals[k][0], vast.Input):
            top_inputs.append(str(k))

    # Order the list in descending order, based on the number of path tokens
    instances = sorted(instance_module_dict.keys(), key=lambda x: x.count("."), reverse=True)

    bind_dict = analyzer.getBinddict()
    bindings = []
    for bk, bv in bind_dict.items():  # for each binding
        for bvi in bv:
            bindings.append(bvi)

    instances_affecting_list = instances_affecting_signal(top_inputs, output_name, instances, analyzer.getTerms(),
                                                          bindings)
    instances_affecting_list.reverse()  # priority is given to instances "closer" to output signal
    if top_name in instances_affecting_list:
        instances_affecting_list.remove(top_name)  # otherwise everything would be in FPGA!

    """
    inst = instances_affecting_list.copy()
    for k in instances_affecting_list:
        for j in instances_affecting_list:
            if (j != k) and (j in k) and (k in inst):
                inst.remove(k)
    instances_affecting_list = inst
    """

    instance_module_dict_ordered = OrderedDict()
    for inst_name in instances_affecting_list:
        if  not any((instance_module_dict[inst_name].startswith(e) for e in exclude)):
            instance_module_dict_ordered[inst_name] = instance_module_dict[inst_name]
    return instance_module_dict_ordered


def instances_affecting_signal(top_inputs, output_signal, instances, signal_list, bindings):
    signals_chain = []  # contains signals in the signals_chain yet to be analyzed
    signals_dep = set()  # contains all signals involved in the signals_chain
    signals_chain.append(output_signal)
    inst_list = []
    while signals_chain:
        looked_signal = signals_chain.pop(0)
        if (looked_signal not in top_inputs) and (looked_signal not in signals_dep):
            signals_dep.add(looked_signal)
            inst_list.extend(instances_in_string(instances, looked_signal))
            for bind in bindings:
                if str(bind.dest) == looked_signal:
                    to_add = signals_in_string(signal_list, bind.tree.tostr())  # set
                    signals_chain.extend(list(to_add))

    inst_list = list(dict.fromkeys(inst_list))
    # inst_list = sorted(inst_list, key=lambda x: x.count("."), reverse=True)
    return inst_list


def signals_in_string(signal_list, string):
    # suppose instances_list contains ordered elements, by number of tokens
    string_signals = set()
    for sig in signal_list:
        if str(sig)+")" in string:
            string_signals.add(str(sig))
    return string_signals


def instances_in_string(instances_list, string):
    # suppose instances_list contains ordered elements, by number of tokens
    string_instances = set()
    for inst in instances_list:
        if inst in string:
            string_instances.add(inst)
            string = string.replace(inst, "")
    return string_instances


"""
"""


def choose_by_sharing(analyzer, top_name):
    print("Performing choice by sharing")
    # Get all instances names
    instances_dict = analyzer.getInstances()
    instance_module_dict = {}  # key = instance name; value = module
    instance_module_dict_ordered = OrderedDict()
    instances = []  # List of all instances
    instances_affected_dict = {}  # key = instance name; value = list of dependent other instances names
    for inst, module in instances_dict:
        inst_name = str(inst)
        instance_module_dict[inst_name] = module
        instances_affected_dict[inst_name] = []
        instances.append(inst_name)

    bind_dict = analyzer.getBinddict()
    # Order the list in descending order, based on the number of path tokens
    instances = sorted(instances, key=lambda x: x.count("."), reverse=True)
    for bk, bv in bind_dict.items():
        for bvi in bv:
            # For each assignment, count the different modules affected

            dest = str(bvi.dest)  # left part of the assignment
            # Extract the instance which the signal belongs to
            for inst in instances:
                if inst in dest:
                    dest = inst
                    break

            # Exploit tostr method, to avoid to implement specific classes methods to perform the search
            # of involved instance in the bindings
            tree_instances = instances_in_string(instances, bvi.tree.tostr())
            tree_instances.discard(dest)  # not interesting if an instance influences itself

            for inst in instances:  # For each instance
                if tree_instances and inst in tree_instances:
                    dest_list = instances_affected_dict[inst]
                    # if dest not in dest_list: ## we can keep this line if we don't want to
                    # focus on single signals, but just on number of other depending instances
                    dest_list.append(dest)
                    instances_affected_dict[inst] = dest_list

    # Order the instances based on the length of dependencies list
    instances_affected_dict.pop(top_name)  # otherwise everything would be in FPGA!
    # for inst_name, list_dep in sorted(instances_affected_dict.items(), key=lambda x: len(x[1]), \
    # reverse=True)[0:num_to_select]:
    for inst_name, list_dep in sorted(instances_affected_dict.items(), key=lambda x: len(x[1]), reverse=True):
        instance_module_dict_ordered[inst_name] = instance_module_dict[inst_name]

    return instance_module_dict_ordered


def ranking_and_filter(efpga_list, redactionInfo):
    # consider a single fpga at a time
    THRESHOLD = 100

    possible_efpgas = {}
    # calc max utilization
    max_io_occupation = 0
    for efpga in efpga_list:
        io_occupation = efpga.io_occupation_percentage
        if io_occupation > max_io_occupation:
            max_io_occupation = io_occupation
    # calc max utilization
    max_clb_occupation = 0
    for efpga in efpga_list:
        clb_occupation = efpga.clb_occupation_percentage
        if clb_occupation > max_clb_occupation:
            max_clb_occupation = clb_occupation

    for efpga in efpga_list:
        # assign a score to each fpga
        io_occupation = efpga.io_occupation_percentage
        clb_occupation = efpga.clb_occupation_percentage
        score = 0
        score += (1 - (max_io_occupation - io_occupation)/max_io_occupation)*100
        score += (1 - (max_clb_occupation - clb_occupation)/max_clb_occupation)*100
        redactionInfo.redactionConfig.logInfo (efpga.name + " --> score = " + str(score))
        # filter out low scoring efpgas
        if score > THRESHOLD:
            possible_efpgas[efpga] = score

    return possible_efpgas


def select_best(solutions, score_dict):
    # calc solution scores by summing score of solution.selected
    # return highest scoring solution
    max_sol_score = 0
    best_solution = None
    for sol in solutions:
        sol_score = 0
        for efpga in sol.selected:
            sol_score = sol_score + score_dict[efpga]
            if sol_score > max_sol_score:
                max_sol_score = sol_score
                best_solution = sol
    return best_solution


def choose_by_number_IO(instances, max_io_pins, redactionInfo):
    time_s = redactionInfo.time_s
    # Find all modules that comply with IO_count
    allowed_modules = [instanceName for instanceName in instances if redactionInfo.getModuleTotalIOCount(redactionInfo.getModuleByInstanceName(instanceName)) <= max_io_pins]    
    redactionInfo.redactionConfig.logInfo("Time elapsed (process time) for first phase (module filtering): " + str(time.time() - time_s) + "s")
    time_s = time.time()
    # Find possible combinations of modules
    combinations = findModuleCombinations(redactionInfo, allowed_modules, max_io_pins)

    redactionInfo.redactionConfig.logInfo("Time elapsed (process time) for second phase (eFPGA identification): " + str(time.time() - time_s) + "s")
    time_s = time.time()

    # build redaction RedactionAlternatives
    alternatives = []
    #temp_combinations = []
    #temp_combinations.append(combinations[0])
    #temp_combinations.append(combinations[1])
    counter = 0
    for combination in combinations:
        efpga_name = "Top_epfga_" + str(counter)
        redactionInfo.redactionConfig.logInfo(str(combination) + " --> " +  efpga_name)
        # build an Efpga object for each combination
        efpga = Efpga(redactionInfo, combination, efpga_name)
        # then for each Efpga Object build wrapper
        efpga.build_wrapper()
        if efpga.ast_fpga == None: raise Exception("Invalid eFPGA AST (" + efpga_name + ")")
        # run efpga creation (redaction)
        efpga.run_openfpga()
        counter += 1
        if efpga.valid: 
            # run sec assessment
            efpga.run_security_analysis()
            alternatives.append(efpga)

    # then order by sec result then find most secure allowed combination -> build RedactionSolution object
    
    #filter to eliminate the ones with poor score (so the selection tree is "smaller")
    score_dict = ranking_and_filter(alternatives, redactionInfo)
    #creation of the selection tree
    solutions = findAllowedEFPGACombinations(redactionInfo, score_dict.keys())
    # selection of the best (solution score is the sum of efpga scores)
    solution = select_best(solutions, score_dict)
    redactionInfo.redactionConfig.logInfo("Time elapsed (process time) for third phase (eFPGA characterization + selection): " + str(time.time() - time_s) + "s")
    

    if solution is None:
        redactionInfo.redactionConfig.logInfo("No feasible solutions found under given constraints.")
        quit()

    modules_list = list(set([ module for modules in [efpga.modules_to_extract for efpga in solution.selected] for module in modules]))

    redactionInfo.redactionConfig.logInfo("Total number of modules = " + str(len(redactionInfo.frame_table.getAllInstances())))
    redactionInfo.redactionConfig.logInfo("-----")
    redactionInfo.redactionConfig.logInfo("Number of allowed modules = " + str(len(allowed_modules)))
    redactionInfo.redactionConfig.logInfo("-----")
    redactionInfo.redactionConfig.logInfo("Number of eFPGA candidates = " + str(len(combinations)))
    redactionInfo.redactionConfig.logInfo("Number of eFPGA valid alternatives = " + str(len(alternatives)))
    redactionInfo.redactionConfig.logInfo("-----")
    redactionInfo.redactionConfig.logInfo("Number of solutions = " + str(len(solutions)))
    redactionInfo.redactionConfig.logInfo("-----")
    redactionInfo.redactionConfig.logInfo("Total number of used eFPGA = " + str(len(solution.selected)))
    for f in solution.selected:
        redactionInfo.redactionConfig.logInfo("    - " + str(f.size) + "x"  + str(f.size))    
    redactionInfo.redactionConfig.logInfo("Total number of redacted modules = " + str(len(modules_list)))

    return solution
