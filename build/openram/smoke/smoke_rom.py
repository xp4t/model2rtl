# OpenROM smoke test: the official OpenRAM sample 1 kbyte SKY130 ROM.
# Run BEFORE any model2rtl parameter macro, to prove the installation works.
word_size = 1
check_lvsdrc = True
rom_data = "example_1kbyte.bin"
data_type = "bin"
output_name = "smoke_rom_1kbyte"
output_path = "/home/rithwik/model2rtl/build/openram/smoke/out/"
# Nix-based automatic tool bootstrap is disabled: this machine supplies
# magic/netgen/klayout from a user-space installation on PATH instead.
use_nix = False

tech_name = "sky130"
nominal_corner_only = True
route_supplies = "ring"
