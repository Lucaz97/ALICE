from pyverilog.vparser.parser import parse
from pyverilog.dataflow.dataflow_analyzer import VerilogDataflowAnalyzer
from pyverilog.dataflow.modulevisitor import ModuleVisitor
from pyverilog.dataflow.signalvisitor import SignalVisitor
import pyverilog.vparser.ast as vast
import time


class RedactionInfo:
    def __init__(self, cfg):
        self.redactionConfig = cfg
        self.redactionConfig.logInfo("Running Dataflow Analyzer")
        self.time_s = time.time()
        self.analyzer = VerilogDataflowAnalyzer(cfg.file_list, cfg.topmodule, preprocess_include=cfg.include, preprocess_define=cfg.define)
        self.analyzer.generate()
        self.redactionConfig.logInfo("Done running Dataflow Analyzer")
        self.ast, self.directives = parse(cfg.file_list, preprocess_include=cfg.include, preprocess_define=cfg.define)
        self.frame_table = self.analyzer.getFrameTable()
        self.instances = dict(self.analyzer.getInstances()) # keys are instance name, values are instance type
        #self.ast.show()
        module_visitor = ModuleVisitor()
        module_visitor.visit(self.ast)
        self.moduleinfotable = module_visitor.get_moduleinfotable()
        cfg.logInfo("INSTANCES:" + str(self.instances))

        for module in set(self.instances.values()):
            self.redactionConfig.logInfo("Module IO count: " + str(module) +" : "+ str(self.getModuleTotalIOCount(module)))

    def getModuleIOPortsNames(self, mod_name):
        return self.moduleinfotable.getIOPorts(mod_name)
    
    def getModuleIOPortsNodes(self, mod_name):
        port_nodes = self.moduleinfotable.dict[mod_name].ioports_nodes
        if type(port_nodes[0]) == vast.Port:
            # only has the name -> gotta find the Input and Output nodes
            port_nodes = [self.moduleinfotable.dict[mod_name].variables.getSignal(n.name)[0] for n in port_nodes]
        return port_nodes

    def getModuleSignalsDict(self, mod_name):
        return self.moduleinfotable.dict[mod_name].variables.signal.dict
    
    def getModuleTotalIOCount(self, mod_name):
        for exclude in self.redactionConfig.exclude_modules:
            if mod_name.startswith(exclude):
                return float("inf")
        count = 0
        signalDict = self.getModuleSignalsDict(mod_name)
        ioNodes = self.getModuleIOPortsNodes(mod_name)
        ioNamesList = self.getModuleIOPortsNames(mod_name) # list of strings
        ioNamesSigList = [item for item in signalDict.keys() if item in ioNamesList]

        # if the complete declaration of io is in the signal section
        for ioPort in ioNamesSigList:
            width = signalDict[ioPort][0].width
            if width:
                lsb = int(width.lsb.value) #will fail if param
                msb = int(width.msb.value)
                count += abs(lsb - msb) + 1
            else:
                count += 1

        # if the io has been completely declared into the port map
        for ioNode in ioNodes:
            if ioNode.name not in ioNamesSigList:
                if ioNode.width:
                    lsb = int(ioNode.width.lsb.value) #will fail if param
                    msb = int(ioNode.width.msb.value)
                    count += abs(lsb - msb) + 1
                else:
                    count += 1
        
        return count

    def getInstanceByName(self, name): # name either string or scopechain
        string_name = str(name)
        for instance in self.instances.keys():
            if str(instance) == string_name:
                return instance
        return None

    def getModuleByInstanceName(self, instance): #name either string or scopechain
        if isinstance(instance, str):
            i = self.getInstanceByName(instance)
            if instance is None:
                raise ValueError("Error: instance name does not correspond to any instance: "+ instance)
            else:
                instance = i
        
        return self.instances[instance]

    def getModuleNodeByInstanceName(self, instance):
        return self.moduleinfotable.getDefinition(self.getModuleByInstanceName(instance))
    
    def getParentModuleNodeByInstanceName(self, instance):
        return self.getModuleNodeByInstanceName(instance[:-1])
    