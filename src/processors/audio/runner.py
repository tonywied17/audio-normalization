"""
FFmpeg/ffprobe command execution helpers.
"""

import subprocess
import os
from typing import List
from core.bundle import get_bundled_executable


def run_command(command: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the CompletedProcess result."""
    try:
        try:
            prog = command[0]
            if os.path.basename(prog) in ("ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"):
                bundled = get_bundled_executable(os.path.basename(prog))
                if bundled:
                    command = [bundled] + command[1:]
        except Exception:
            pass

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
            encoding='utf-8',
            check=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{e.stderr}")


def popen(command: List[str]) -> subprocess.Popen:
    """Start a process with stderr PIPE for live UI consumption."""
    try:
        prog = command[0]
        if os.path.basename(prog) in ("ffmpeg", "ffprobe", "ffmpeg.exe", "ffprobe.exe"):
            bundled = get_bundled_executable(os.path.basename(prog))
            if bundled:
                command = [bundled] + command[1:]
    except Exception:
        pass
    return subprocess.Popen(command, stderr=subprocess.PIPE, text=True, encoding='utf-8')
