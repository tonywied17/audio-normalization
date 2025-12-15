"""
Core processing functions for individual files (normalize / boost).
"""

from typing import Dict, Any


def boost_file(audio_processor, file_path: str, boost_percent: float, dry_run: bool = False, show_ui: bool = False) -> Dict[str, Any]:
    """Boost a single audio file."""
    if dry_run:
        return {"success": True, "message": "Dry Run"}
    try:
        res = audio_processor.boost_audio(file_path, boost_percent, show_ui=show_ui, dry_run=dry_run)
        if res:
            return {"success": True}
        return {"success": False, "message": "Boost failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def normalize_file(audio_processor, file_path: str, dry_run: bool = False, progress_callback=None, show_ui: bool = False) -> Dict[str, Any]:
    """Normalize a single audio file."""
    if dry_run:
        return {"success": True, "message": "Dry Run"}
    try:
        res = audio_processor.normalize_audio(file_path, show_ui=show_ui, progress_callback=progress_callback)
        if res:
            return {"success": True}
        return {"success": False, "message": "Normalization failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}
