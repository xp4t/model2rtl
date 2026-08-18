#!/bin/sh
export OPENRAM_TECH="/home/rithwik/OpenRAM/technology:/home/rithwik/OpenRAM/compiler/../technology"
echo "$(date): Starting GDS to MAG using Magic /home/rithwik/klayout_cf/magic/bin/magic"

/home/rithwik/klayout_cf/magic/bin/magic -dnull -noconsole << EOF
drc off
set VDD vdd
set GND gnd
set SUB gnd
gds warning default
gds flatglob *_?mos_m*
gds flatglob sky130_fd_bd_sram__sram_sp_cell_fom_serifs
gds flatglob sky130_fd_bd_sram__sram_sp_cell
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1_replica_cell
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1a_replica_cell
gds flatglob sky130_fd_bd_sram__sram_sp_cell_opt1_ce
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1_replica_ce
gds flatglob sky130_fd_bd_sram__openram_sp_cell_opt1a_replica_ce
gds flatglob sky130_fd_bd_sram__sram_sp_wlstrap_ce
gds flatglob sky130_fd_bd_sram__sram_sp_wlstrap_p_ce
gds flatten true
gds ordering true
gds read smoke_rom_1kbyte.gds
puts "Finished reading gds smoke_rom_1kbyte.gds"
load smoke_rom_1kbyte
puts "Finished loading cell smoke_rom_1kbyte"
cellname delete \(UNNAMED\)
writeall force
port makeall
extract style ngspice(si)
extract unique all
extract all
select top cell
feedback why
puts "Finished extract"
ext2spice hierarchy on
ext2spice format ngspice
ext2spice cthresh infinite
ext2spice rthresh infinite
ext2spice renumber off
ext2spice scale off
ext2spice blackbox on
ext2spice subcircuit top on
ext2spice global off
ext2spice format ngspice
ext2spice smoke_rom_1kbyte
select top cell
feedback why
puts "Finished ext2spice"
quit -noprompt
EOF
magic_retcode=$?
echo "$(date): Finished ($magic_retcode) GDS to MAG using Magic /home/rithwik/klayout_cf/magic/bin/magic"
exit $magic_retcode
