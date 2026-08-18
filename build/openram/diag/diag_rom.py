# OpenROM bit/address-ordering DIAGNOSTIC (model2rtl Stage 2).
# One-hot data so every row has exactly one programmed cell:
#   row 0 = 0x01, row 1 = 0x02, row 2 = 0x04, ... row 7 = 0x80
# Netlist only: we read the ordering straight out of the generated SPICE.
word_size = 1
# words_per_row: left to the OpenROM heuristic (16 for this shape)
check_lvsdrc = False
netlist_only = False
use_nix = False
rom_data = "diag.hex"
data_type = "hex"
output_name = "diag_rom"
output_path = "/home/rithwik/model2rtl/build/openram/diag/out/"
tech_name = "sky130"
nominal_corner_only = True
route_supplies = "ring"
