"""
Configuration and constants for audio normalization.
"""

from typing import Dict, Any

VERSION = "2.2"

NORMALIZATION_PARAMS: Dict[str, float] = {
    "I": -16.0,
    "TP": -1.5,
    "LRA": 11.0,
}

SUPPORTED_EXTENSIONS = (
    '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v',
    '.mpg', '.mpeg', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac'
)

AUDIO_CODEC = "ac3"
AUDIO_BITRATE = "256k"

LOG_DIR = "logs/"
LOG_FILE = "app.log"
LOG_FFMPEG_DEBUG = "ffmpeg_debug.log"

TEMP_SUFFIX = "_temp_processing"
