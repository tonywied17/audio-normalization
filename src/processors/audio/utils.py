"""
Utility helpers for metadata and temp file handling.
"""

import os
import re
from typing import Dict
from core.config import TEMP_SUFFIX
from core.signal_handler import SignalHandler


def update_track_title(original_title: str, operation: str, extra: str = "") -> str:
    """Update the track title with normalization/boosting tags."""
    cleaned = re.sub(r"\[molexAudio (Normalized|Boosted [^]]+)\] ?", "", original_title).strip()
    tag = f"[molexAudio {operation}"
    if extra:
        tag += f" {extra}"
    tag += "]"
    return f"{tag} {cleaned}".strip()


def create_temp_file(original_path: str) -> str:
    """Create a temporary file path based on the original file path."""
    base, ext = os.path.splitext(original_path)
    temp_path = f"{base}{TEMP_SUFFIX}{ext}"
    try:
        SignalHandler.register_temp_file(temp_path)
    except Exception:
        pass
    return temp_path


def channels_to_layout(ch: int) -> str:
    """Convert number of channels to audio layout string."""
    return {1: 'mono', 2: 'stereo', 6: '5.1', 8: '7.1'}.get(ch, 'stereo')
