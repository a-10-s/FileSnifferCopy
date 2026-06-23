import sys
import argparse
from pathlib import Path

def main():
    # Mimic oiiotool syntax: oiiotool <input> --compression <comp> -o <output>
    # We use a custom parser to handle positional argument at beginning, then options, then option -o
    args = sys.argv[1:]
    
    if "--help" in args:
        print("oiiotool version mock-1.0.0")
        print("Usage: oiiotool [input] --compression [comp] -o [output]")
        sys.exit(0)

    try:
        # Simple positional & flag extraction
        input_path = Path(args[0])
        
        comp_idx = args.index("--compression")
        compression = args[comp_idx + 1]
        
        out_idx = args.index("-o")
        output_path = Path(args[out_idx + 1])
    except Exception as e:
        print(f"Mock oiiotool syntax error. Args received: {args}", file=sys.stderr)
        sys.exit(1)

    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # Simulate compression by writing a file containing input text plus compression mark
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(input_path, 'r', errors='ignore') as f_in:
            content = f_in.read()
            
        with open(output_path, 'w') as f_out:
            f_out.write(f"MOCK EXR FILE\nCompression: {compression}\nOriginal:\n{content}")
            
        print(f"Mock transcode succeeded: {input_path} -> {output_path} (Compression: {compression})")
        sys.exit(0)
    except Exception as e:
        print(f"Error creating mock output: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
