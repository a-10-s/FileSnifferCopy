import sys
from pathlib import Path

def main():
    args = sys.argv[1:]
    if "-version" in args or "--version" in args:
        print("ffmpeg version mock-1.0.0")
        sys.exit(0)
        
    try:
        # Log arguments to a file in the scratch folder for validation
        log_path = Path(__file__).resolve().parent / "ffmpeg_args.log"
        with open(log_path, "w") as log_f:
            log_f.write(" ".join(sys.argv))

        # The last argument is the output file path in our command structure
        output_path = Path(args[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write("MOCK MP4 PROXY VIDEO DATA")
        print(f"Mock FFmpeg compilation succeeded: {output_path}")
        sys.exit(0)
    except Exception as e:
        print(f"Error creating mock proxy video: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
