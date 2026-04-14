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

def generate_yosys_script(target, top_module):
    script = f"""
    # 1. Read and Elaborate
    read_slang -f build.f
    hierarchy -check -top {top_module}
    """
    if target == "fpga":
        script += f"""
    synth -lut 6 -top {top_module}
    stat
    opt -full
    flatten
    ltp -noff
    """
    elif target == "asic":
        script += f"""
    synth -top {top_module}
    abc -g cmos2
    stat
    """
    with open("metrics.ys", "w") as f:
        f.write(script)

def run_yosys():
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

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        print("::group::Click here to expand the raw Yosys Synthesis Log")
        print(result.stdout)
        print("::endgroup::\n")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print("Error: Yosys synthesis failed!")
        print("::group::Click here to view the Failing Yosys Log")
        print(e.stdout)
        print("::endgroup::")
        sys.exit(1)

def extract_and_save_metrics(log, target, top_module):
    metrics = {}
    if target == "fpga":
        match_lut = re.search(r'(\d+)\s+\$lut', log)
        metrics["fpga_luts"] = match_lut.group(1) if match_lut else "N/A"
        match_ltp = re.search(r'Longest topological path[^\n]*?\(length=(\d+)\)', log)
        metrics["ltp"] = match_ltp.group(1) if match_ltp else "N/A"
    elif target == "asic":
        ge_weights = {
            '$_NAND_': 1.0, '$_NOR_': 1.0, '$_NOT_': 0.5, '$_AND_': 1.5, '$_OR_': 1.5,
            '$_ANDNOT_': 1.5, '$_ORNOT_': 1.5, '$_XOR_': 2.5, '$_XNOR_': 2.5, '$_MUX_': 2.5,
            '$_DFF_PP0_': 5.0, '$_DFF_PP1_': 5.0, '$_DFFE_PP_': 6.0, '$_DFFE_PP0P_': 6.0, '$_SDFFCE_PN0P_': 7.0
        }
        total_ge = 0.0
        header = f"=== {top_module} ==="
        if header in log:
            last_stat_block = log.split(header)[-1]
            matches = re.findall(r'\s+(\d+)\s+(\$_\w+_)', last_stat_block)
            for count_str, cell_type in matches:
                total_ge += int(count_str) * ge_weights.get(cell_type, 2.0)
            if total_ge > 0:
                metrics["asic_ge"] = f"{total_ge:,.1f}"

    # Updated naming convention for matrix support
    output_file = f"metrics-{top_module}-{target}.json"
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=4)
    print(f"Metrics extracted and saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Yosys Synthesis Metrics")
    parser.add_argument("--top", required=True, help="Top level module name")
    parser.add_argument("--run", required=True, choices=['fpga', 'asic'], help="Target platform")
    args = parser.parse_args()

    print(f"--- Starting Synthesis: {args.top} ({args.run.upper()}) ---")
    generate_yosys_script(args.run, args.top)
    raw_log = run_yosys()
    extract_and_save_metrics(raw_log, args.run, args.top)
