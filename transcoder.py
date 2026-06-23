import subprocess
from pathlib import Path
import os
import shutil

def verify_oiiotool(oiiotool_path: str) -> tuple[bool, str]:
    """
    Check if oiiotool executable is available and callable.
    Returns:
        (success: bool, version_info/error: str)
    """
    # If the user provided a relative path or just "oiiotool.exe", check PATH
    resolved_path = shutil.which(oiiotool_path) or oiiotool_path
    
    try:
        # Run oiiotool with --help or --version
        # Use shell=False for safety on Windows
        result = subprocess.run(
            [resolved_path, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        # oiiotool --help prints help text and exits (sometimes with code 0 or 1, but we check if it ran)
        if "oiiotool" in result.stdout or "oiiotool" in result.stderr or result.returncode in (0, 1):
            return True, "oiiotool verified successfully."
        return False, f"Unexpected output: {result.stderr or result.stdout}"
    except Exception as e:
        return False, f"Could not execute oiiotool at '{resolved_path}': {str(e)}"

def verify_ffmpeg(ffmpeg_path: str) -> tuple[bool, str]:
    """
    Check if FFmpeg executable is available and callable.
    Returns:
        (success: bool, version_info/error: str)
    """
    resolved_path = shutil.which(ffmpeg_path) or ffmpeg_path
    try:
        result = subprocess.run(
            [resolved_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if "ffmpeg" in result.stdout.lower() or result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "FFmpeg detected."
            return True, f"FFmpeg verified successfully: {version_line}"
        return False, f"Unexpected output: {result.stderr or result.stdout}"
    except Exception as e:
        return False, f"Could not execute FFmpeg at '{resolved_path}': {str(e)}"


def transcode_exr(oiiotool_path: str, src: Path, dst: Path, compression: str = "dwab") -> tuple[bool, int, str]:
    """
    Run oiiotool to transcode an EXR to a different compression.
    Args:
        oiiotool_path: Path to oiiotool executable.
        src: Source EXR file.
        dst: Destination EXR file.
        compression: Target compression (e.g., 'dwab', 'dwaa', 'zip', 'piz').
    Returns:
        (success: bool, output_size: int, error_message: str)
    """
    resolved_path = shutil.which(oiiotool_path) or oiiotool_path
    
    if not src.exists():
        return False, 0, f"Source file '{src}' does not exist."
        
    # Ensure target compression is valid syntax for oiiotool
    # oiiotool expects lowercase compression settings
    comp_arg = compression.lower().strip()
    
    # Base command: oiiotool <input> --compression <comp> -o <output>
    # oiiotool preserves all channels, layers, and metadata by default
    cmd = [
        resolved_path,
        str(src.resolve()),
        "--compression", comp_arg,
        "-o", str(dst.resolve())
    ]
    
    try:
        # Run subprocess
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0 and dst.exists():
            try:
                out_size = dst.stat().st_size
                return True, out_size, ""
            except Exception as e:
                return False, 0, f"Could not read size of output file: {str(e)}"
        else:
            err = result.stderr or result.stdout or f"Exit code: {result.returncode}"
            return False, 0, f"oiiotool failed. Error: {err}"
            
    except Exception as e:
        return False, 0, f"Failed to run oiiotool subprocess: {str(e)}"
