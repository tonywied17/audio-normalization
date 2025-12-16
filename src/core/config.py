"""
Configuration and constants for audio normalization.
"""

from typing import Dict, Any
import os, sys, json


#! ---- Default configuration values ---- !#

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



#! ---- Helper functions to load and override config from JSON file ---- !#

def _get_config_path() -> str:
    """Get the path to the config.json file."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base, "config.json")


def _write_default_config(path: str) -> None:
    """Write the default configuration to a JSON file."""
    defaults = {
        "VERSION": VERSION,
        "NORMALIZATION_PARAMS": NORMALIZATION_PARAMS,
        "SUPPORTED_EXTENSIONS": list(SUPPORTED_EXTENSIONS),
        "AUDIO_CODEC": AUDIO_CODEC,
        "AUDIO_BITRATE": AUDIO_BITRATE,
        "LOG_DIR": LOG_DIR,
        "LOG_FILE": LOG_FILE,
        "LOG_FFMPEG_DEBUG": LOG_FFMPEG_DEBUG,
        "TEMP_SUFFIX": TEMP_SUFFIX,
    }
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(defaults, fh, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _load_json_config():
    """Load configuration overrides from a JSON file."""
    path = _get_config_path()
    if not os.path.exists(path):
        _write_default_config(path)
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return

    global VERSION, NORMALIZATION_PARAMS, SUPPORTED_EXTENSIONS
    global AUDIO_CODEC, AUDIO_BITRATE, LOG_DIR, LOG_FILE, LOG_FFMPEG_DEBUG, TEMP_SUFFIX

    if isinstance(data.get("VERSION"), str):
        VERSION = data.get("VERSION")

    np = data.get("NORMALIZATION_PARAMS")
    if isinstance(np, dict):
        for k, v in np.items():
            try:
                NORMALIZATION_PARAMS[k] = float(v)
            except Exception:
                pass

    se = data.get("SUPPORTED_EXTENSIONS")
    if isinstance(se, (list, tuple)) and se:
        SUPPORTED_EXTENSIONS = tuple(se)

    if isinstance(data.get("AUDIO_CODEC"), str):
        AUDIO_CODEC = data.get("AUDIO_CODEC")
    if isinstance(data.get("AUDIO_BITRATE"), str):
        AUDIO_BITRATE = data.get("AUDIO_BITRATE")

    if isinstance(data.get("LOG_DIR"), str):
        LOG_DIR = data.get("LOG_DIR")
    if isinstance(data.get("LOG_FILE"), str):
        LOG_FILE = data.get("LOG_FILE")
    if isinstance(data.get("LOG_FFMPEG_DEBUG"), str):
        LOG_FFMPEG_DEBUG = data.get("LOG_FFMPEG_DEBUG")
    if isinstance(data.get("TEMP_SUFFIX"), str):
        TEMP_SUFFIX = data.get("TEMP_SUFFIX")

_load_json_config()
