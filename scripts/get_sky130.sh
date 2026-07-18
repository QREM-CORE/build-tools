#!/bin/bash

# =============================================================================
# File        : get_sky130.sh
# Description : Downloads the Skywater 130nm High-Density Standard Cell Library
#               (.lib format) for use in Yosys + ABC timing estimation.
# =============================================================================

LIB_URL="https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/master/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
LIB_FILE="sky130_fd_sc_hd__tt_025C_1v80.lib"

if [ ! -f "$LIB_FILE" ]; then
    echo "Downloading Sky130 HD library for ASIC timing..."
    curl -L -o "$LIB_FILE" "$LIB_URL"
    if [ $? -eq 0 ]; then
        echo "Download complete: $LIB_FILE"
    else
        echo "Error: Failed to download Sky130 library."
        exit 1
    fi
else
    echo "Sky130 HD library already exists: $LIB_FILE"
fi
