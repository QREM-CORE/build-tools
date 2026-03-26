# Shared Hardware Build Tools

A centralized Makefile and script ecosystem for compiling and simulating SystemVerilog IP blocks using ModelSim and Verilator.

This toolchain automatically resolves transitive dependencies in hierarchical `.f` filelists, allowing for clean, modular IP design.

## 1. Installation

In your target hardware repository, add this tools repository as a submodule:

```bash
git submodule add <URL_TO_BUILD_TOOLS_REPO> build-tools
git submodule update --init --recursive
```

## 2. Integration

Create a `Makefile` in the root of your hardware repository. It only needs one line:

```makefile
# Optional: Override defaults here
# SIM = verilator
# INCDIRS = +incdir+rtl +incdir+lib/common_rtl

# Import the central build system
include build-tools/common.mk
```

## 3. Filelist Rules (`rtl.f`)

To ensure the filelist flattener script works correctly across all tools, your `.f` files **must** follow these rules:

1.  **No Wildcards:** You must explicitly list every `.sv` file (e.g., `rtl/my_module.sv`). Do not use `*.sv`.
2.  **Relative Paths Only:** List files relative to the directory where the `.f` file is located. Do not use environment variables or absolute paths.
3.  **Include Submodules via `-f`:** To include a submodule's filelist, use the `-f` flag.
4.  **Order Matters:** Put package files (`*_pkg.sv`) at the top of the list.

**Example `rtl.f`:**
```text
# 1. Submodules
-f lib/keccak-fips202-sv/rtl.f

# 2. Local Packages
rtl/my_pkg.sv

# 3. Local RTL
rtl/my_core.sv
```

## 4. Usage

The build system automatically discovers all testbenches ending in `_tb.sv` inside the `tb/` directory.

* **Run all tests (Default: ModelSim):**
    ```bash
    make
    ```
* **Run all tests (Verilator):**
    ```bash
    make SIM=verilator
    ```
* **Run a specific testbench:**
    ```bash
    make run_keccak_core_tb SIM=verilator
    ```
* **Clean build artifacts:**
    ```bash
    make clean
    ```
