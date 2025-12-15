"""Probe helpers that use ffprobe to discover media streams."""

import json
from typing import Any, Dict, List
from .runner import run_command


def get_audio_streams(media_path: str, logger) -> List[Dict[str, Any]]:
    """Get audio stream information using ffprobe with multiple fallbacks."""
    ffprobe_cmd = [
        "ffprobe", "-i", media_path,
        "-show_streams", "-select_streams", "a",
        "-loglevel", "quiet", "-print_format", "json"
    ]
    try:
        result = run_command(ffprobe_cmd)
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            try:
                fallback_cmd = [
                    "ffprobe", "-v", "error", "-select_streams", "a",
                    "-show_entries", "stream=index,codec_name,channels,tags", "-print_format", "json", media_path
                ]
                fallback_proc = run_command(fallback_cmd)
                fallback_data = json.loads(fallback_proc.stdout) if fallback_proc.stdout else {}
                streams = fallback_data.get("streams", [])
                logger.info(f"ffprobe fallback returned {len(streams)} audio streams for {media_path}")
            except Exception:
                streams = []
            if not streams:
                try:
                    probe_count_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", media_path]
                    probe_count_proc = run_command(probe_count_cmd)
                    lines = probe_count_proc.stdout.strip().splitlines() if probe_count_proc.stdout else []
                    if lines:
                        logger.info(f"Creating {len(lines)} placeholder audio stream entries for {media_path}")
                        streams = []
                        for idx in range(len(lines)):
                            streams.append({"index": idx, "tags": {}})
                except Exception:
                    pass
        return streams
    except Exception as e:
        logger.error(f"ffprobe failed: {e}")
        return []


def get_video_streams(media_path: str) -> List[Dict[str, Any]]:
    """Get video stream information using ffprobe."""
    ffprobe_cmd = [
        "ffprobe", "-i", media_path,
        "-show_streams", "-select_streams", "v",
        "-loglevel", "quiet", "-print_format", "json"
    ]
    result = run_command(ffprobe_cmd)
    data = json.loads(result.stdout)
    return data.get("streams", [])
