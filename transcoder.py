import subprocess
from pathlib import Path
import os
import shutil

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

