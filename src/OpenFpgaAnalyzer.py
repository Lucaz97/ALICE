import os
import xml.etree.ElementTree as ET

class OpenFpgaAnalyzer:
    def __init__(self, file, name, target, RedactionConfig):
        self.verilog_file = file
        self.top = name
        self.size = 3  # minimum footprint is 3x3
        self.io_occupation_percentage = 0
        self.clb_occupation_percentage = 0
        self.limitations = []
        self.valid = True
        self.target = target
        self.openfpga_log = None
        self.cfg = RedactionConfig

    def run(self):

        command = "${OPENFPGA_PY_INT}"
        command += " ${OPENFPGA_FLOW_PATH}/scripts/run_fpga_flow.py"
        command += " ${OPENFPGA_FLOW_PATH}/vpr_arch/k4_frac_N4_40nm.xml"
        #command += " ${OPENFPGA_FLOW_PATH}/vpr_arch/k4_frac_N4_tileable_40nm.xml"
        #options_k4 = "  --top_module {0} --run_dir {1} 
        command += " " + self.verilog_file
        command += " --top_module " + self.top
        command += " --run_dir " + self.target
        command += " --openfpga_arch_file ${OPENFPGA_FLOW_PATH}/openfpga_arch/k4_frac_N4_40nm_cc_openfpga.xml"
        #command += " --openfpga_arch_file ${OPENFPGA_FLOW_PATH}/openfpga_arch/k4_N4_40nm_cc_openfpga.xml"
        #command += " --openfpga_arch_file ${OPENFPGA_FLOW_PATH}/openfpga_arch/jb_k4_frac_N8.xml"
        #command += " --openfpga_shell_template ../../../../../common/OpenFPGA/myscript.openfpga"
        command += " --openfpga_shell_template " + os.getcwd() + "/../../../common/OpenFPGA/myscript.openfpga"
        command += " --openfpga_sim_setting_file ${OPENFPGA_FLOW_PATH}/openfpga_simulation_settings/fixed_sim_openfpga.xml"
        #options_k6 = " ${{OPENFPGA_FLOW_PATH}}/vpr_arch/k6_frac_N10_40nm.xml  {1}/../src/*.v --top_module {0} --run_dir {1} --openfpga_arch_file ${{OPENFPGA_FLOW_PATH}}/openfpga_arch/k6_frac_N8_40nm_openfpga.xml --openfpga_shell_template ../../../../../common/OpenFPGA/myscript.openfpga --openfpga_sim_setting_file ${{OPENFPGA_FLOW_PATH}}/openfpga_simulation_settings/fixed_sim_openfpga.xml".format(self.top, self.target)
        #opt_test = " /home/chiara/Documenti/Sviluppo\ Python/out.xml  {1}/../src/*.v --top_module {0} --run_dir {1} --openfpga_arch_file ${{OPENFPGA_FLOW_PATH}}/openfpga_arch/k6_frac_N8_40nm_openfpga.xml  --openfpga_shell_template ../../../../../common/OpenFPGA/myscript.openfpga --openfpga_sim_setting_file ${{OPENFPGA_FLOW_PATH}}/openfpga_simulation_settings/fixed_sim_openfpga.xml".format(self.top, self.target)
        os.system(command)
        self.openfpga_log = self.target + '/openfpgashell.log'


    def _fpga_size(self):
        with open(self.openfpga_log, 'r') as f:
            for line in f:
                initial_text = "FPGA sized to "
                if initial_text in line:
                    self.size = int(line.split("x")[0].split(" ")[-2])

    def _io_occupation(self):
        with open(self.openfpga_log, 'r') as f:
            for line in f:
                # TODO: substitute this with regex
                initial_text = "Block Utilization: "
                end_text = "Logical Block: io"
                if end_text in line and initial_text in line:
                    self.io_occupation_percentage = float(line[len(initial_text):len(initial_text)+4])

    def _clb_occupation(self):
        with open(self.openfpga_log, 'r') as f:
            for line in f:
                # TODO: substitute this with regex
                initial_text = "Block Utilization: "
                end_text = "Logical Block: clb"
                if end_text in line and initial_text in line:
                    self.clb_occupation_percentage = float(line[len(initial_text):len(initial_text)+4])

    def _find_limitation(self):
        with open(self.openfpga_log, 'r') as f:
            for line in f:
                initial_text = "FPGA size limited by block type(s): "
                if initial_text in line:
                    print(line)
                    self.limitations = line[len(initial_text):-1].split()

    def _read_error(self):
        with open(self.openfpga_log, 'r') as f:
            for line in f:
                if "ERROR" in line or "Error" in line:
                    if not "check_rr_graph" in line: self.valid = False

    def read_log(self):
        if not os.path.isfile(self.openfpga_log):
            print("FPGA  with {1} as redaction module failed".format(self.size, self.top))
            return 0, 0, 0, False

        self._fpga_size()
        self._io_occupation()
        self._clb_occupation()
        self._read_error()
        # If size is not the smallest possible (3x3), then specify what is the limitation
        if self.size not in self.cfg.not_allowed_size: #
            print("FPGA size {0}x{0} with {1} as redaction module".format(self.size, self.top))
        else:
            self.valid = False
        if not self.valid: print("FPGA (size {0}x{0}) not valid".format(self.size))
        return self.size, float(self.io_occupation_percentage)*100, float(self.clb_occupation_percentage)*100, self.valid


    def improve(self):
        if self.size > 3:
            self.limitations = self._find_limitation()
            "k4_frac_N4_40nm.xml"
        else:
            print("Cannot improve more. FPGA is already minimum size possible")

    def modify_architecture(self, arch_file, limitation):
        OPEN_FPGA_WORKING_DIR = "${{OPENFPGA_FLOW_PATH}}/"
        SUBPATH = "vpr_arch/"
        XML_ADDR = OPEN_FPGA_WORKING_DIR + SUBPATH + arch_file
        tree_arch = ET.parse(XML_ADDR)
        root = tree_arch.getroot()
        print(root.tag)

        iter_tile = root.iter('tile')
        if limitation == "io":
            for tile in iter_tile:
                if 'io' == tile.attrib["name"]:
                    # Double the capacity
                    tile.attrib["capacity"] = str(2 * int(tile.attrib["capacity"]))
        if limitation == "clb":
            for tile in iter_tile:
                if 'clb' == tile.attrib["name"]:
                    pass

        new_arch_file = "out.xml"
        tree_arch.write(new_arch_file)
        return new_arch_file
