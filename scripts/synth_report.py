"""
=============================================================================
File        : synth_report.py
Author(s)   : Kiet Le
Description : A centralized reporting engine for the Yosys and Slang CI
              pipeline. Executes the "Gather" phase of the architecture by
              consuming dynamically generated JSON artifacts across multiple
              targets and top-level modules, and outputs a consolidated
              Markdown report for GitHub Pull Requests.

Usage:
  Reporting Phase (Gather):
     python3 synth_report.py
     (Consumes metrics-*.json artifacts to generate pr_comment.md)
=============================================================================
"""
#!/usr/bin/env python3
import glob
import json
import os
from collections import defaultdict

def generate_consolidated_report():
    print("--- Starting Phase: Report Generation ---")

    # Dictionary to hold metrics grouped by module
    module_data = defaultdict(lambda: {
        "fpga_luts": "N/A", "fpga_brams": "N/A", "fpga_dsps": "N/A",
        "fpga_registers": "N/A", "asic_ge": "N/A", "asic_cells": "N/A",
        "asic_ffs": "N/A", "ltp": "N/A"
    })

    # Find all JSON artifacts in the current directory
    artifact_files = glob.glob("metrics-*.json")

    if not artifact_files:
        print("Warning: No metrics JSON files found in the directory.")
        with open("pr_comment.md", "w") as f:
            f.write("### Hardware Synthesis Metrics\n*No synthesis metrics were generated during this run.*")
        return

    # Parse filenames and load data
    for file_path in artifact_files:
        # Expected format: metrics-{module_name}-{target}.json
        filename = os.path.basename(file_path)
        parts = filename.replace("metrics-", "").replace(".json", "").rsplit("-", 1)

        if len(parts) == 2:
            module_name, target = parts
            with open(file_path, "r") as f:
                metrics = json.load(f)
                module_data[module_name].update(metrics)
                print(f"Loaded {target} metrics for {module_name}")

    # Build the Markdown string
    md_lines = ["## 📊 Hardware Synthesis Metrics\n"]

    for module_name, metrics in sorted(module_data.items()):
        md_lines.append(f"### Target Top: `{module_name}`\n")

        md_lines.append("#### FPGA Metrics (Xilinx 7-Series)")
        md_lines.append("| Metric | Value |")
        md_lines.append("|--------|-------|")
        md_lines.append(f"| **LUTs** | `{metrics.get('fpga_luts', 'N/A')} LUTs` |")
        md_lines.append(f"| **Registers** | `{metrics.get('fpga_registers', 'N/A')} FFs` |")
        md_lines.append(f"| **DSPs** | `{metrics.get('fpga_dsps', 'N/A')} DSPs` |")
        md_lines.append(f"| **BRAMs (18K)** | `{metrics.get('fpga_brams', 'N/A')} Blocks` |")
        md_lines.append(f"| **Critical Path** | `{metrics.get('ltp', 'N/A')} Logic Levels` |\n")

        md_lines.append("#### ASIC Metrics (CMOS2)")
        md_lines.append("| Metric | Value |")
        md_lines.append("|--------|-------|")
        md_lines.append(f"| **Area (GE)** | `{metrics.get('asic_ge', 'N/A')} GEs` |")
        md_lines.append(f"| **Total Cells** | `{metrics.get('asic_cells', 'N/A')} Cells` |")
        md_lines.append(f"| **Registers** | `{metrics.get('asic_ffs', 'N/A')} FFs` |\n")

        md_lines.append("---")

    md_lines.append("\n> *Generated automatically by the centralized Yosys + Slang CI Pipeline.*")

    # Write to file
    final_md = "\n".join(md_lines)
    with open("pr_comment.md", "w") as f:
        f.write(final_md)

    print("\nConsolidated report generated and saved to pr_comment.md")

if __name__ == "__main__":
    generate_consolidated_report()
