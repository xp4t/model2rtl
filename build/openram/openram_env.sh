# Stage-2 OpenRAM/OpenROM environment for model2rtl.
# Exact paths actually used on this machine. Nothing is installed system wide
# and no system Python is modified.
export OPENRAM_ROOT=/home/rithwik/OpenRAM
export OPENRAM_HOME=$OPENRAM_ROOT/compiler
export OPENRAM_TECH=$OPENRAM_ROOT/technology
export PDK_ROOT=/home/rithwik/pdk
export PDKPATH=$PDK_ROOT/sky130A
export PYTHONPATH=$OPENRAM_HOME
export OPENRAM_PYTHON=$OPENRAM_ROOT/.venv/bin/python
export ROM_COMPILER=$OPENRAM_ROOT/rom_compiler.py
# physical verification tools
export PATH=/home/rithwik/netgen-install/bin:/home/rithwik/klayout_cf/magic/bin:$PATH
