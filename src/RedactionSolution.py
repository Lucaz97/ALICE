# this class holds one redaction alternative with its modified ast with wrapper modules and needed changes
from RedactionUtils import *

class RedactionSolution:
    def __init__(self, redactionInfo, efpga_list):
        self.redactionInfo = redactionInfo
        self.efpga_list = efpga_list

    def build_ast(self):
        
        # find MCP
        # TODO: adapt to actual implementation
        mcp = findMCP(self.modules_to_extract)
        print()
        print("----")
        print("MCM: ",mcp)
        # TODO FileExistsError()

        # for each module see if need to fix any chaining modules
        for module in self.modules_to_extract:
            if module != mcp:
                print()
                for to_fix in findChainingModules(module, mcp):
                    print("TOFIX: ", to_fix)
                    # TODO fix
