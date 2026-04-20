# QREM-CORE Build Tools & CI/CD Ecosystem

A centralized infrastructure repository for RTL hardware development. This ecosystem provides two core functions:
1. **The "Golden Pipeline":** A unified GitHub Actions CI/CD architecture for automated linting, simulation, and synthesis.
2. **The Local Build System:** A standardized `Makefile` environment for compiling and simulating SystemVerilog IP blocks using ModelSim and Verilator.

By centralizing these tools, hardware repositories remain lightweight and do not require redundant local CI environment maintenance or complex script duplication.

---

## Part A: Centralized Builder (CI/CD)

The `central-builder.yml` workflow enforces a unified standard across all target repositories. It utilizes a dynamic "Scatter-Gather" 2D matrix architecture to run targets and modules in parallel.

**Supported Toolchain:**
* **Linting:** Verible
* **Simulation:** Verilator (Fast) & ModelSim / VSIM 32-bit (Slow)
* **Synthesis:** Yosys + Slang (ASIC & FPGA targets)

### 1. Integration
To attach a hardware repository to the CI/CD pipeline, delete any local simulation workflows and create `.github/workflows/pr.yml` with the following boilerplate:

```yaml
name: PR Build Pipeline

on:
  push:
    branches: [ main ]
  pull_request:

permissions:
  pull-requests: write
  contents: read

jobs:
  call-central-builder:
    uses: QREM-CORE/build-tools/.github/workflows/central-builder.yml@main
    with:
      rtl_repo: ${{ github.repository }}
      commit_sha: ${{ github.sha }}

      # Comma-separated list of top-level modules for Synthesis
      top_modules: 'keccak_core, mlkem_core'

      # Toggles (Default is true)
      enable_synth: true
      enable_lint: true
      enable_verilator: true
      enable_vsim: true
```

### 2. Configuration & Artifacts
* **`top_modules`:** This string is dynamically parsed using `jq` into a JSON array, spawning parallel Yosys synthesis jobs for every module across both ASIC and FPGA targets.
* **Toggles:** Bypassing heavy jobs (like `enable_vsim: false`) is highly recommended for minor documentation or lint-only PRs.
* **Outputs:** The pipeline automatically aggregates the scattered matrix metrics into a unified Markdown table and posts it as a PR comment.

---

## Part B: The Local Build System

The `common.mk` file provides a dual-simulator Make environment that automatically discovers testbenches and resolves transitive dependencies in hierarchical `.f` filelists.

### 1. Installation
In your target hardware repository, add this tools repository as a submodule:

```bash
git submodule add https://github.com/QREM-CORE/build-tools.git build-tools
git submodule update --init --recursive
```

### 2. Integration
Create a `Makefile` in the root of your hardware repository. It only requires one include directive:

```makefile
# Optional: Override defaults here
# SIM = verilator
# INCDIRS = +incdir+rtl +incdir+lib/common_rtl

# Import the central build system
include build-tools/common.mk
```

### 3. Usage
The build system automatically discovers all testbenches ending in `_tb.sv` inside your local `tb/` directory.

* **Run all tests (Default: ModelSim):** `make`
* **Run all tests (Verilator):** `make SIM=verilator`
* **Run a specific testbench:** `make run_keccak_core_tb SIM=verilator`
* **Clean build artifacts:** `make clean`

---

## Part C: Filelist Architecture (`.f` Rules)

**CRITICAL:** Both the local Makefile (via `flatten_f.py`) and the cloud Yosys pipeline strictly depend on your filelists being formatted correctly.

Your `.f` files **must** follow these four rules to ensure paths resolve correctly and "Diamond Dependency" conflicts are prevented:

1.  **No Wildcards:** Explicitly list every `.sv` file (e.g., `rtl/my_module.sv`). Do not use `*.sv`.
2.  **Relative Paths Only:** List files relative to the directory where the `.f` file is located. Avoid environment variables or absolute paths.
3.  **Include Submodules via `-f`:** To include a submodule's filelist, use the `-f` flag.
4.  **Order Matters:** Place package files (`*_pkg.sv`) at the absolute top of your list.

**Example `rtl.f`:**
```text
# 1. Submodules
-f lib/keccak-fips202-sv/rtl.f

# 2. Local Packages
rtl/my_pkg.sv

# 3. Local RTL
rtl/my_core.sv
```
