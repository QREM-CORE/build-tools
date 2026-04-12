#!/usr/bin/env python3
import subprocess
import re
import sys

# Define the top module (could be parameterized via argparse later)
TOP_MODULE = "hash_sampler_unit"

def generate_yosys_script():
    """Generates the Yosys command file to extract all 3 metrics."""
    script = f"""
    # 1. Read and Elaborate
    read_slang -f build.f
    hierarchy -check -top {TOP_MODULE}

    # Save the elaborated state so we don't have to re-parse Slang for every metric
    design -save pre_synth

    # --- METRIC 1: FPGA (LUT6) & TIMING (LTP) ---
    synth -top {TOP_MODULE}
    abc -lut 6
    stat > fpga_stat.txt
    opt
    ltp > ltp_stat.txt

    # --- METRIC 2: ASIC (Gate Equivalents) ---
    design -load pre_synth
    synth -top {TOP_MODULE}
    abc -g cmos2
    stat > asic_stat.txt
    """
    with open("metrics.ys", "w") as f:
        f.write(script)

def run_yosys():
    """Executes the generated Yosys script."""
    print("🚀 Running Yosys Synthesis Metrics (This may take a minute)...")
    try:
        subprocess.run(["yosys", "-m", "slang", "-q", "metrics.ys"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Yosys synthesis failed! Check your RTL for syntax errors.")
        sys.exit(1)

def extract_metrics():
    """Parses the generated text files to extract numbers."""
    metrics = {"fpga_luts": "N/A", "asic_ge": "N/A", "ltp": "N/A"}

    # 1. Extract FPGA LUTs
    try:
        with open("fpga_stat.txt", "r") as f:
            log = f.read()
            match = re.search(r'\$lut\s+(\d+)', log)
            if match: metrics["fpga_luts"] = match.group(1)
    except FileNotFoundError: pass

    # 2. Extract ASIC Gate Area
    try:
        with open("asic_stat.txt", "r") as f:
            log = f.read()
            match = re.search(r'Chip area for module.*?:\s+([\d\.]+)', log)
            if match: metrics["asic_ge"] = match.group(1)
    except FileNotFoundError: pass

    # 3. Extract Longest Topological Path (Critical Path)
    try:
        with open("ltp_stat.txt", "r") as f:
            log = f.read()
            match = re.search(r'Longest topological path.*?:\s+(\d+)\s+cells', log)
            if match: metrics["ltp"] = match.group(1)
    except FileNotFoundError: pass

    return metrics

def generate_markdown(metrics):
    """Formats the metrics into a GitHub PR comment."""
    md = f"""
### 📊 Hardware Synthesis Metrics (`{TOP_MODULE}`)

| Metric | Target | Value |
|--------|--------|-------|
| **Area** | FPGA (LUT6) | `{metrics['fpga_luts']} LUTs` |
| **Area** | ASIC (CMOS2) | `{metrics['asic_ge']} GEs` |
| **Timing** | Critical Path | `{metrics['ltp']} Logic Levels` |

> *Generated automatically by Yosys + Slang CI Pipeline.*
"""
    with open("pr_comment.md", "w") as f:
        f.write(md)
    print("✅ Metrics successfully extracted and saved to pr_comment.md")

if __name__ == "__main__":
    generate_yosys_script()
    run_yosys()
    metrics_data = extract_metrics()
    generate_markdown(metrics_data)
