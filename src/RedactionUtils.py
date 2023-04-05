time_s = 0

# mod1 and mod2 module names in the pyverilog dotted name notation
def relatedModules(mod1, mod2):
    return (str(mod1) in str(mod2)) or (str(mod2) in str(mod1))

# returns the minimum common parent of the provided modules 
def findMCP(modules):
    mpm = modules[0]
    if len(modules) > 1:
        for module in modules[1:]:
            matches = [l1 == l2 for l1, l2 in zip(module, mpm)]
            mpm = mpm[: matches.index(0)] if 0 in matches else mpm
    else:
        mpm = mpm[:-1]
    return mpm

# given an instance and one of its parent modules find all modules in between
def findChainingModules(instance, parent):
    chaining_modules = []
    print("INSTANCE: ", instance)
    print("Parent : ", parent)

    i = 1
    while instance[:-i] != parent and i < len(instance):
        #print(instance[:-i])
        chaining_modules.append(instance[:-i])
        i += 1
    return chaining_modules



def findModuleCombinations(redactionInfo, top_list, max_fpga_IO_size, max_n_fpga= 1):
    # First find all possible clusters, then find all subsets of cluster of size max_n_fpga
    redactionInfo.redactionConfig.logInfo("Finding Module Combinations")
    redactionInfo.redactionConfig.logInfo("Top list: "+ str(top_list))
    
    # init clusters with a cluster made of one module, for each module.
    clusters = [[module] for module in top_list] # I assume that if module is in toplist, it comply the max fpga IO size
    expanded_clusters = []

    # expand clusters until completion
    extended = 1
    while extended:
        extended = 0
        for cluster in clusters[:]: # [:] sort of hack to iterate over a copy of the list so that I can extend the original one in the loop
            # Calculate the total io of current cluster (could be optimized by storing this in a dict)
            tot_io = sum((redactionInfo.getModuleTotalIOCount(redactionInfo.instances[cluster_module]) for cluster_module in cluster))

            allowed_extensions = []
            for module in top_list:
                # Check if module is related to any module in the cluster (any() returns True if any element is true)
                # Check if adding this module would make a feasible cluster
                if (tot_io + redactionInfo.getModuleTotalIOCount(redactionInfo.instances[module]) <= max_fpga_IO_size and
                    not any((relatedModules(module, cluster_module) for cluster_module in cluster)) ): 
                        allowed_extensions.append(module)
                        extended = 1
            # insert extensions
            for ext in allowed_extensions:
                new_cluster = []
                new_cluster.extend(cluster)
                new_cluster.append(ext)
                clusters.append(new_cluster)

            # remove this cluster if extended
            if allowed_extensions:
                expanded_clusters.append(cluster)
                clusters.remove(cluster)


        # Need to remove duplicates at this point not trivial because the elements are lists of objects
        clusters = [cluster for n, cluster in enumerate(clusters) if not any((sorted( [str(el) for el in cluster]) == sorted([str(el) for el in possible_duplicate]) for possible_duplicate in clusters[:n]))]
    clusters.extend(expanded_clusters)
    #print()
    print(clusters)
    #print()
    #print(clusters[-1][0][:-1])
    #print()
    #print(findMPM(clusters[-1]))
    #print(type(redactionInfo.getModuleByInstanceName(str(clusters[-1][0]))))
    #print(redactionInfo.getModuleNodeByInstanceName(clusters[-1][0]))

    #quit()
    return clusters



class Solution:
        def __init__ (self, available, selected):
            self.selected = selected
            self.available = available

        def _copy(self):
            return Solution(self.available[:], self.selected[:])

        def add(self, efpga):
            if not any(not module in self.available for module in efpga.modules_to_extract):
                # I can add the efpga to the solution
                copy = self._copy()
                copy.selected.append(efpga)
                for module in efpga.modules_to_extract:
                    for available_module in copy.available[:]:
                        if str(module) in str(available_module) or str(available_module) in str(module):
                            copy.available.remove(available_module)
                return copy
            else:
                return None
        
        def isLeaf(self, max_sol):
            return len(self.available) == 0 or len(self.selected) == max_sol

        def __repr__(self):
            return "Sol Obj: SELECTED MODULES -> " + " ".join([str(efpga.modules_to_extract) for efpga in self.selected])


def findAllowedEFPGACombinations(redactionInfo, efpga_list):

    modules_list = list(set([ module for modules in [efpga.modules_to_extract for efpga in efpga_list] for module in modules]))
    finished_solutions = []
    current_solutions = [Solution(modules_list, [])]

    for efpga in efpga_list:
        for sol in current_solutions[:]:
            new_sol = sol.add(efpga)
            if new_sol:
                # I found new solution, is this leaf?
                if new_sol.isLeaf(redactionInfo.redactionConfig.max_fpga_num):
                    finished_solutions.append(new_sol)
                else:
                    current_solutions.append(new_sol)

    finished_solutions.extend(current_solutions[1:]) # dont add empty solution
    #print(finished_solutions)
    #print(len(finished_solutions))
    #print(len(efpga_list))
    #quit()
    #ranking
    return finished_solutions


