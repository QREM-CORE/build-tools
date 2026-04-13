"""
=============================================================================
File        : synth_metrics.py
Author(s)   : Kiet Le
Description : A modular metrics engine for Yosys and Slang. Orchestrates a
              "Scatter-Gather" CI architecture by performing target-specific
              synthesis, extracting hardware metrics (LUTs, GEs, Path Depth),
              and generating unified Markdown reports for GitHub PRs.

Usage:
  1. Synthesis Phase (Scatter):
     python3 synth_metrics.py --top <module> --run [fpga|asic]
     (Generates metrics-<target>.json)

  2. Reporting Phase (Gather):
     python3 synth_metrics.py --top <module> --report
     (Consumes JSON artifacts to generate pr_comment.md)
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
    """Generates a target-specific Yosys command file."""
    script = f"""
    # 1. Read and Elaborate
    read_slang -f build.f
    hierarchy -check -top {top_module}
    """

    if target == "fpga":
        script += f"""
    # --- METRIC 1: FPGA (LUT6) & TIMING (LTP) ---
    synth -lut 6 -top {top_module}
    stat
    opt -full
    ltp
    """
    elif target == "asic":
        script += f"""
    # --- METRIC 2: ASIC (Gate Equivalents) ---
    synth -top {top_module}
    abc -g cmos2
    stat
    """

    with open("metrics.ys", "w") as f:
        f.write(script)

def run_yosys():
    """Runs Yosys, prints the script and command, and groups the log output."""
    try:
        with open("metrics.ys", "r") as f:
            script_contents = f.read()
        print("::group::View Generated Yosys Script (metrics.ys)")
        print(script_contents.strip())
        print("::endgroup::\n")
    except FileNotFoundError:
        print("Warning: Could not read metrics.ys before execution.")

    cmd = ["yosys", "-T", "-m", "slang", "metrics.ys"]
    print(f"Executing Command: {' '.join(cmd)}")
    print("Running Yosys Synthesis Metrics (This may take a minute)...\n")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        log = result.stdout

        print("::group::Click here to expand the raw Yosys Synthesis Log")
        print(log)
        print("::endgroup::\n")
        return log

    except subprocess.CalledProcessError as e:
        print("Error: Yosys synthesis failed! Check your RTL for syntax errors.")
        print("::group::Click here to view the Failing Yosys Log")
        print(e.stdout)
        print("::endgroup::")
        sys.exit(1)

def extract_and_save_metrics(log, target, top_module):
    """Parses the target-specific log and saves the data as a JSON artifact."""
    metrics = {}

    if target == "fpga":
        # Extract FPGA LUTs
        match_lut = re.search(r'(\d+)\s+\$lut', log)
        metrics["fpga_luts"] = match_lut.group(1) if match_lut else "N/A"

        # Extract Longest Topological Path
        match_ltp = re.search(r'Longest topological path[^\n]*?\(length=(\d+)\)', log)
        metrics["ltp"] = match_ltp.group(1) if match_ltp else "N/A"

    elif target == "asic":
        ge_weights = {
            '$_NAND_': 1.0, '$_NOR_': 1.0, '$_NOT_': 0.5,
            '$_AND_': 1.5, '$_OR_': 1.5, '$_ANDNOT_': 1.5, '$_ORNOT_': 1.5,
            '$_XOR_': 2.5, '$_XNOR_': 2.5, '$_MUX_': 2.5,
            '$_DFF_PP0_': 5.0, '$_DFF_PP1_': 5.0,
            '$_DFFE_PP_': 6.0, '$_DFFE_PP0P_': 6.0, '$_SDFFCE_PN0P_': 7.0
        }

        total_ge = 0.0

        # Isolate the final stat block
        header = f"=== {top_module} ==="
        if header in log:
            last_stat_block = log.split(header)[-1]
            matches = re.findall(r'\s+(\d+)\s+(\$_\w+_)', last_stat_block)

            for count_str, cell_type in matches:
                count = int(count_str)
                weight = ge_weights.get(cell_type, 2.0)
                total_ge += count * weight

            if total_ge > 0:
                metrics["asic_ge"] = f"{total_ge:,.1f}"

    output_file = f"metrics-{target}.json"
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=4)

    print(f"Metrics successfully extracted and saved to {output_file}")

def generate_report(top_module):
    """Reads all JSON artifacts from disk and builds the final Markdown table."""
    metrics = {
        "fpga_luts": "N/A",
        "asic_ge": "N/A",
        "ltp": "N/A"
    }

    # Load FPGA metrics if the artifact exists
    if os.path.exists("metrics-fpga.json"):
        with open("metrics-fpga.json", "r") as f:
            fpga_data = json.load(f)
            metrics.update(fpga_data)
    else:
        print("Warning: metrics-fpga.json not found. FPGA data will show as N/A.")

    # Load ASIC metrics if the artifact exists
    if os.path.exists("metrics-asic.json"):
        with open("metrics-asic.json", "r") as f:
            asic_data = json.load(f)
            metrics.update(asic_data)
    else:
        print("Warning: metrics-asic.json not found. ASIC data will show as N/A.")

    # Generate Markdown
    md = f"""
### Hardware Synthesis Metrics (`{top_module}`)

| Metric | Target | Value |
|--------|--------|-------|
| **Area** | FPGA (LUT6) | `{metrics['fpga_luts']} LUTs` |
| **Area** | ASIC (CMOS2) | `{metrics['asic_ge']} GEs` |
| **Timing** | Critical Path | `{metrics['ltp']} Logic Levels` |

> *Generated automatically by Yosys + Slang CI Pipeline.*
"""
    with open("pr_comment.md", "w") as f:
        f.write(md)

    print("Final report generated and saved to pr_comment.md:")
    print(f"LUTs: {metrics['fpga_luts']} | GEs: {metrics['asic_ge']} | Path: {metrics['ltp']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yosys Synthesis Metrics Engine")
    parser.add_argument("--top", required=True, help="Top level module name")

    # Mutually exclusive group: You either run a synthesis, or generate a report, but not both at once.
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", choices=['fpga', 'asic'], help="Execute Yosys for a specific target and save JSON")
    group.add_argument("--report", action="store_true", help="Consume JSON artifacts and generate Markdown report")

    args = parser.parse_args()

    if args.run:
        print(f"--- Starting Phase: Synthesis ({args.run.upper()}) ---")
        generate_yosys_script(args.run, args.top)
        raw_log = run_yosys()
        extract_and_save_metrics(raw_log, args.run, args.top)

    elif args.report:
        print("--- Starting Phase: Report Generation ---")
        generate_report(args.top)
