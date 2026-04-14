"""
=============================================================================
File        : flatten_f.py
Author(s)   : Kiet Le
Description : A recursive HDL filelist (.f) flattener. Resolves relative paths
              to absolute locations based on the filelist's directory and
              performs base-filename deduplication. Specifically designed to
              resolve "Diamond Dependency" conflicts in nested submodules
              within the ML-KEM hardware accelerator build system.

Usage:
  python3 flatten_f.py <top_level_filelist.f>
  (Outputs a list of unique, absolute-pathed source files to stdout)
=============================================================================
"""

import sys
import os

def parse_filelist(file_path, seen_filenames=None):
    # Initialize the set on the first recursive call
    if seen_filenames is None:
        seen_filenames = set()

    # Ensure the .f file exists
    if not os.path.exists(file_path):
        print(f"Error: Could not find filelist '{file_path}'", file=sys.stderr)
        sys.exit(1)

    # Get the absolute directory of the current .f file
    base_dir = os.path.dirname(os.path.abspath(file_path))

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()

            # Ignore empty lines and comments
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # If the line is an include (e.g., "-f lib/keccak/rtl.f")
            if line.startswith('-f ') or line.startswith('-F '):
                included_f = line.split(maxsplit=1)[1]
                included_path = os.path.join(base_dir, included_f)

                # Recursively parse, passing our set of seen files
                parse_filelist(included_path, seen_filenames)

            # Otherwise, it's a standard RTL file
            else:
                sv_path = os.path.normpath(os.path.join(base_dir, line))
                filename = os.path.basename(sv_path)

                # Deduplicate based on the file name (e.g., 'axis_if.sv')
                # This perfectly solves the nested git submodule diamond dependency!
                if filename not in seen_filenames:
                    seen_filenames.add(filename)
                    print(sv_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 flatten_f.py <top_level_filelist.f>", file=sys.stderr)
        sys.exit(1)

    parse_filelist(sys.argv[1])
