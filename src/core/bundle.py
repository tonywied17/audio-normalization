"""
Helpers for locating bundled executables when frozen with PyInstaller.
"""

import os
import sys


def get_bundled_executable(exe_name: str) -> str | None:
    """Get the path to a bundled executable if running in a PyInstaller bundle."""
    try:
        if getattr(sys, "frozen", False):
            base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
            candidate = os.path.join(base, exe_name)
            if os.path.exists(candidate):
                return candidate
            if not candidate.lower().endswith('.exe'):
                candidate_exe = candidate + '.exe'
                if os.path.exists(candidate_exe):
                    return candidate_exe
    except Exception:
        pass
    return None
