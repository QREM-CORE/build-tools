"""
=============================================================================
File        : synth_metrics.py
Author(s)   : Kiet Le
Description : A modular metrics engine for Yosys and Slang. Executes the
              "Scatter" phase of a CI architecture by performing target-specific
              synthesis, extracting hardware metrics (LUTs, GEs, Path Depth),
              and outputting matrix-compatible JSON artifacts for downstream
              aggregation.

Usage:
  Synthesis Phase (Scatter):
     python3 synth_metrics.py --top <module> --run [fpga|asic]
     (Generates metrics-<module>-<target>.json)
=============================================================================
"""
#!/usr/bin/env python3
import argparse
import subprocess
import re
import json
import sys
import os

def generate_yosys_script(target, top_module):
    script = f"""
    # 1. Read and Elaborate
    read_slang -f build.f
    hierarchy -check -top {top_module}
    """
    if target == "fpga":
        script += f"""
    # =========================================================================
    # --- METRIC 1: FPGA (Xilinx 7-Series) & TIMING (LTP) ---
    # We extract two metrics: Resource Utilization (LUTs/BRAMs/DSPs) and
    # Longest Topological Path (critical path depth in logic levels).
    # =========================================================================

    # 1. Resource Utilization: synth_xilinx automatically maps memory arrays
    #    to BRAMs and logic to LUTs/DSPs/Registers.
    synth_xilinx -family xc7 -top {top_module}
    #    Print the statistics table which our python script will parse
    stat

    # 2. Reset the Yosys state to clear Xilinx-specific mapping artifacts
    design -reset

    # 3. Longest Topological Path: We perform a clean synthesis run targeting
    #    generic 6-input LUTs without technology mapping noise (xilinx_dffopt).
    read_slang -f build.f
    hierarchy -check -top {top_module}
    synth -lut 6 -top {top_module} -flatten
    #    Calculate the critical path logic depth (ignoring logic inside flip-flops)
    ltp -noff
    """
    elif target == "asic":
        lib_file = "sky130_fd_sc_hd__tt_025C_1v80.lib"

        with open("constr.txt", "w") as f:
            f.write("set_driving_cell sky130_fd_sc_hd__inv_1\nset_load 0.0\n")

        script += f"""
    # =========================================================================
    # --- METRIC 2: ASIC Synthesis (Dual-Pass Strategy) ---
    # We perform synthesis once, but map the logic twice to extract two
    # different sets of metrics: Generic Area (GE) and Physical Timing (Sky130)
    # =========================================================================

    # 1. Generic Synthesis: Translate RTL into an abstract internal representation
    synth -top {top_module}

    # 2. Save State: Checkpoint the generic gate-level netlist before we map it
    design -save pre_map

    # =========================================================================
    # PASS 1: Generic CMOS2 Mapping (For technology-independent Area/GE metrics)
    # =========================================================================
    # Map the abstract logic to basic CMOS gates (NAND, NOR, DFF)
    abc -g cmos2
    # Print the statistics table (Area/GE) which our python regex will parse
    stat

    # =========================================================================
    # PASS 2: Skywater 130nm HD Mapping (For accurate Timing/Fmax & Physical Area)
    # =========================================================================
    # 1. Restore the generic unmapped netlist checkpoint
    design -load pre_map
    # 2. Map flip-flops to the physical Sky130 standard cells
    dfflibmap -liberty {lib_file}
    # 3. Map combinatorial logic to Sky130 standard cells using the constraint file.
    #    The constr.txt ensures timing delays are accurately driven by a physical inverter.
    abc -liberty {lib_file} -constr constr.txt
    """
    with open("metrics.ys", "w") as f:
        f.write(script)

def run_yosys(logdir, target, top_module):
    try:
        with open("metrics.ys", "r") as f:
            script_contents = f.read()
        print("::group::View Generated Yosys Script (metrics.ys)")
        print(script_contents.strip())
        print("::endgroup::\n")
    except FileNotFoundError:
        pass

    cmd = ["yosys", "-T", "-m", "slang", "metrics.ys"]
    print(f"Executing Command: {' '.join(cmd)}")

    log_file = os.path.join(logdir, f"metrics-{top_module}-{target}.log")
    if logdir != ".":
        os.makedirs(logdir, exist_ok=True)

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        print("::group::Click here to expand the raw Yosys Synthesis Log")
        print(result.stdout)
        print("::endgroup::\n")

        with open(log_file, "w") as f:
            f.write(result.stdout)
        print(f"Synthesis log saved to {log_file}")

        return result.stdout
    except subprocess.CalledProcessError as e:
        print("Error: Yosys synthesis failed!")
        print("::group::Click here to view the Failing Yosys Log")
        print(e.stdout)
        print("::endgroup::")

        with open(log_file, "w") as f:
            f.write(e.stdout)
        print(f"Synthesis error log saved to {log_file}")

        sys.exit(1)

def extract_and_save_metrics(log, target, top_module, outdir):
    metrics = {}

    # Isolate the final statistics section to prevent triple-counting
    # By splitting on the text and taking the last element [-1],
    # we automatically grab the very last stats block.
    if "Printing statistics." in log:
        if target == "fpga":
            stats_section = log.split("Printing statistics.")[-2]
        elif target == "asic":
            stats_section = log.split("Printing statistics.")[-1]

    if target == "fpga":
        # Xilinx stat outputs specific LUT types (LUT1, LUT2... LUT6)
        lut_matches = re.findall(r'(\d+)\s+LUT\d', stats_section)
        total_luts = sum(int(count) for count in lut_matches)
        metrics["fpga_luts"] = str(total_luts) if total_luts > 0 else "N/A"

        # Extract BRAMs (Normalize to 18K equivalents)
        bram18 = sum(int(c) for c in re.findall(r'(\d+)\s+RAMB18', stats_section))
        bram36 = sum(int(c) for c in re.findall(r'(\d+)\s+RAMB36', stats_section))
        total_brams = bram18 + (bram36 * 2)
        metrics["fpga_brams"] = str(total_brams) if total_brams > 0 else "0"

        # Extract DSPs (DSP48E1, DSP48E2, etc.)
        dsps = sum(int(c) for c in re.findall(r'(\d+)\s+DSP48', stats_section))
        metrics["fpga_dsps"] = str(dsps) if dsps > 0 else "0"

        # Extract Registers (Flip-Flops: Xilinx FD* + generic $_DFF*)
        xilinx_ffs = sum(int(c) for c in re.findall(r'(\d+)\s+FD[A-Z]+', stats_section))
        generic_ffs = sum(int(c) for c in re.findall(r'(\d+)\s+\$_\w*DFF\w*_', stats_section))
        total_ffs = xilinx_ffs + generic_ffs
        metrics["fpga_registers"] = str(total_ffs) if total_ffs > 0 else "0"

        # Extract Longest Topological Path
        match_ltp = re.search(r'Longest topological path[^\n]*?\(length=(\d+)\)', log)
        metrics["ltp"] = match_ltp.group(1) if match_ltp else "N/A"
    elif target == "asic":
        ge_weights = {
            '$_NAND_': 1.0, '$_NOR_': 1.0, '$_NOT_': 0.5, '$_AND_': 1.5, '$_OR_': 1.5,
            '$_ANDNOT_': 1.5, '$_ORNOT_': 1.5, '$_XOR_': 2.5, '$_XNOR_': 2.5, '$_MUX_': 2.5,
            '$_DFF_PP0_': 5.0, '$_DFF_PP1_': 5.0, '$_DFFE_PP_': 6.0, '$_DFFE_PP0P_': 6.0, '$_SDFFCE_PN0P_': 7.0
        }
        total_ge = 0.0
        total_cells = 0
        total_ffs = 0
        # We use the 'stats_section' we isolated at the top of the function
        # to ensure we don't triple-count the cells from the hierarchy breakdown.
        # Use re.MULTILINE and $ to ensure we only match the clean `stat` table lines
        # and not the `dfflibmap` logging (which looks like 'mapped 325 $_DFF_ to...').
        matches = re.findall(r'^\s+(\d+)\s+(\$_\w+_)$', stats_section, re.MULTILINE)
        for count_str, cell_type in matches:
            count = int(count_str)
            total_ge += count * ge_weights.get(cell_type, 2.0)
            total_cells += count
            if 'DFF' in cell_type:
                total_ffs += count

        if total_ge > 0:
            metrics["asic_ge"] = f"{total_ge:,.1f}"
            metrics["asic_cells"] = str(total_cells)
            metrics["asic_ffs"] = str(total_ffs)

        # Extract Sky130 Physical Metrics from ABC pass
        match_area = re.search(r'Area\s*=\s*([\d\.]+)', log)
        if match_area:
            metrics["sky130_area_um2"] = match_area.group(1)
        else:
            metrics["sky130_area_um2"] = "N/A"

        match_gates = re.search(r'Gates\s*=\s*(\d+)', log)
        if match_gates:
            metrics["sky130_gates"] = match_gates.group(1)
        else:
            metrics["sky130_gates"] = "N/A"

        match_delay = re.search(r'Delay\s*=\s*([\d\.]+)\s*ps', log)
        if match_delay:
            delay_ps = float(match_delay.group(1))
            if delay_ps > 0:
                fmax_mhz = 1_000_000 / delay_ps
                metrics["sky130_delay_ps"] = f"{delay_ps:.2f}"
                metrics["sky130_fmax_mhz"] = f"{fmax_mhz:.1f}"
        else:
            metrics["sky130_delay_ps"] = "N/A"
            metrics["sky130_fmax_mhz"] = "N/A"

    # Save to JSON
    output_file = f"metrics-{top_module}-{target}.json"
    output_path = os.path.join(outdir, output_file)

    # Create directory if it doesn't exist
    if outdir != ".":
        os.makedirs(outdir, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"Metrics extracted and saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Yosys Synthesis Metrics")
    parser.add_argument("--top", required=True, help="Top level module name")
    parser.add_argument("--run", required=True, choices=['fpga', 'asic'], help="Target platform")
    parser.add_argument("--outdir", default=".", help="Directory to save the metrics JSON files")
    parser.add_argument("--logdir", default=None, help="Directory to save the synthesis log files (defaults to outdir)")
    args = parser.parse_args()

    if args.logdir is None:
        args.logdir = args.outdir

    print(f"--- Starting Synthesis: {args.top} ({args.run.upper()}) ---")
    generate_yosys_script(args.run, args.top)
    raw_log = run_yosys(args.logdir, args.run, args.top)
    extract_and_save_metrics(raw_log, args.run, args.top, args.outdir)
