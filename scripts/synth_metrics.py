#!/usr/bin/env python3
import subprocess
import re
import sys

# Define the top module
TOP_MODULE = "hash_sampler_unit"

def generate_yosys_script():
    """Generates the Yosys command file. No temporary text files needed."""
    script = f"""
    # 1. Read and Elaborate
    read_slang -f build.f
    hierarchy -check -top {TOP_MODULE}

    # Save the elaborated state so we don't have to re-parse Slang for every metric
    design -save pre_synth

    # --- METRIC 1: FPGA (LUT6) & TIMING (LTP) ---
    synth -top {TOP_MODULE}
    abc -lut 6
    stat
    opt
    ltp

    # --- METRIC 2: ASIC (Gate Equivalents) ---
    design -load pre_synth
    synth -top {TOP_MODULE}
    abc -g cmos2
    stat
    """
    with open("metrics.ys", "w") as f:
        f.write(script)

def run_and_extract_metrics():
    """Runs Yosys, captures stdout, and parses the metrics directly."""
    print("🚀 Running Yosys Synthesis Metrics (This may take a minute)...")

    try:
        # Run Yosys, capture all output into memory (stdout)
        result = subprocess.run(
            ["yosys", "-m", "slang", "metrics.ys"],
            capture_output=True,
            text=True,
            check=True
        )
        log = result.stdout

        # Print the log so it still shows up in the GitHub Actions UI
        print(log)

    except subprocess.CalledProcessError as e:
        print("❌ Yosys synthesis failed! Check your RTL for syntax errors.")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

    # Initialize defaults
    metrics = {"fpga_luts": "N/A", "asic_ge": "N/A", "ltp": "N/A"}

    # 1. Extract FPGA LUTs (e.g., "$lut     9250")
    match_lut = re.search(r'\$lut\s+(\d+)', log)
    if match_lut:
        metrics["fpga_luts"] = match_lut.group(1)

    # 2. Extract ASIC Gate Area (e.g., "Chip area for module '\hash_sampler_unit': 81597.528")
    match_asic = re.search(r'Chip area for module.*?:\s+([\d\.]+)', log)
    if match_asic:
        metrics["asic_ge"] = match_asic.group(1)

    # 3. Extract Longest Topological Path (e.g., "(length=40):")
    match_ltp = re.search(r'Longest topological path.*?\(length=(\d+)\)', log)
    if match_ltp:
        metrics["ltp"] = match_ltp.group(1)

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
    print("\n✅ Metrics successfully extracted and saved to pr_comment.md:")
    print(f"   LUTs: {metrics['fpga_luts']} | GEs: {metrics['asic_ge']} | Path: {metrics['ltp']}")

if __name__ == "__main__":
    generate_yosys_script()
    metrics_data = run_and_extract_metrics()
    generate_markdown(metrics_data)
