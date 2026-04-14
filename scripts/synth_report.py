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

    # Dictionary to hold metrics grouped by module: data["module_name"]["fpga_luts"] = value
    module_data = defaultdict(lambda: {"fpga_luts": "N/A", "asic_ge": "N/A", "ltp": "N/A"})

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
        md_lines.append(f"### Target Top: `{module_name}`")
        md_lines.append("| Metric | Target | Value |")
        md_lines.append("|--------|--------|-------|")
        md_lines.append(f"| **Area** | FPGA (LUT6) | `{metrics['fpga_luts']} LUTs` |")
        md_lines.append(f"| **Area** | ASIC (CMOS2) | `{metrics['asic_ge']} GEs` |")
        md_lines.append(f"| **Timing** | Critical Path | `{metrics['ltp']} Logic Levels` |")
        md_lines.append("\n---")

    md_lines.append("\n> *Generated automatically by the centralized Yosys + Slang CI Pipeline.*")

    # Write to file
    final_md = "\n".join(md_lines)
    with open("pr_comment.md", "w") as f:
        f.write(final_md)

    print("\nConsolidated report generated and saved to pr_comment.md")

if __name__ == "__main__":
    generate_consolidated_report()
