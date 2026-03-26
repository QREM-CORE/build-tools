import sys
import os

def parse_filelist(file_path):
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
                # Extract the filename after the flag
                included_f = line.split(maxsplit=1)[1]
                # Resolve its path relative to the current .f file
                included_path = os.path.join(base_dir, included_f)
                # Recursively parse the included file
                parse_filelist(included_path)

            # Otherwise, it's a standard RTL file
            else:
                # Resolve the RTL file's absolute path
                sv_path = os.path.join(base_dir, line)
                # Print the cleaned-up absolute path
                print(os.path.normpath(sv_path))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 flatten_f.py <top_level_filelist.f>", file=sys.stderr)
        sys.exit(1)

    parse_filelist(sys.argv[1])
