# =========================================================
# Shared Dual-Simulator Build System
# =========================================================

# Allow the local Makefile to override these variables, but set defaults
INCDIRS ?= +incdir+rtl
SIM     ?= vsim
FILELIST ?= rtl.f

# Automatically discover all testbenches in the local tb/ folder
TESTBENCHES = $(patsubst tb/%.sv,%,$(wildcard tb/*_tb.sv))

# Find where THIS common.mk file is located so we can find the scripts
BUILD_TOOLS_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

VERILATOR_FLAGS = --binary -j 0 --timing --trace -Wall -Wno-fatal

# =====================
# STANDARD TARGETS
# =====================
all: run_all

.PHONY: run_all clean run_%

# Generate the flat filelist using the central script
build.f: $(FILELIST)
	@echo "=== Flattening hierarchical filelists ==="
	python3 $(BUILD_TOOLS_DIR)/scripts/flatten_f.py $(FILELIST) > build.f

run_all: build.f
	@for tb in $(TESTBENCHES); do \
		$(MAKE) run_$$tb SIM=$(SIM); \
	done

run_%: build.f
	@echo "=== Running $* with $(SIM) ==="
ifeq ($(SIM), verilator)
	verilator $(VERILATOR_FLAGS) $(INCDIRS) --top-module $* -f build.f tb/$*.sv
	bash -c "set -o pipefail; ./obj_dir/V$* 2>&1 | tee $*.log"
else
	vlib work
	vlog -work work -sv $(INCDIRS) -f build.f tb/$*.sv

	@echo 'vcd file "$*.vcd"' > run_$*.macro
	@echo 'vcd add -r /$*/*' >> run_$*.macro
	@echo 'run -all' >> run_$*.macro
	@echo 'quit' >> run_$*.macro
	vsim -c -do run_$*.macro work.$* -l $*.log
	@rm -f run_$*.macro
endif

clean:
	rm -rf work *.vcd transcript vsim.wlf run_*.macro *.log obj_dir build.f
