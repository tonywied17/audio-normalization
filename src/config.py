"""
Configuration and constants for audio normalization.
"""

from typing import Dict, Any

VERSION = "2.2"

#! Normalization parameters (EBU R128 defaults)
NORMALIZATION_PARAMS: Dict[str, float] = {
    "I": -16.0,     # Integrated loudness target (LUFS)
    "TP": -1.5,     # True peak target (dBFS)
    "LRA": 11.0,    # Loudness range target (LU)
}

#! Supported media file extensions
SUPPORTED_EXTENSIONS = (
    '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v',
    '.mpg', '.mpeg', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac'
)

#! FFmpeg audio codec for output
AUDIO_CODEC = "ac3"
AUDIO_BITRATE = "256k"

#! Logging
LOG_DIR = "logs"
LOG_FILE = "app.log"

#! Temporary file suffix
TEMP_SUFFIX = "_temp_processing"