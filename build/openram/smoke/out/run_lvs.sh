#!/bin/sh
export OPENRAM_TECH="/home/rithwik/OpenRAM/technology:/home/rithwik/OpenRAM/compiler/../technology"
echo "$(date): Starting LVS using Netgen /home/rithwik/netgen-install/bin/netgen"
/home/rithwik/netgen-install/bin/netgen -noconsole << EOF
lvs {smoke_rom_1kbyte.spice smoke_rom_1kbyte} {smoke_rom_1kbyte.lvs.sp smoke_rom_1kbyte} setup.tcl smoke_rom_1kbyte.lvs.report -full -json
quit
EOF
magic_retcode=$?
echo "$(date): Finished ($magic_retcode) LVS using Netgen /home/rithwik/netgen-install/bin/netgen"
exit $magic_retcode
