import os
import re
import subprocess
import json
from src.logger import Logger
from rich.console import Console
from src.constants import NORMALIZATION_PARAMS

logger = Logger(log_file="process.log")
console = Console()


def update_audio_track_title(original_title, operation, extra_info=""):
    """
    Clean up existing prefixes/suffixes and update the title.
    """
    cleaned_title = re.sub(r"molexAudio (Normalized|Boosted \d+% )?", "", original_title).strip()
    if extra_info:
        return f"[molexAudio {operation} {extra_info}] {cleaned_title}".strip()
    else:
        return f"[molexAudio {operation}] {cleaned_title}".strip()


def normalize_audio(video_path, temp_files):
    """
    Normalize audio levels for all audio streams in the video using a two-pass process.
    """
    file_base, file_ext = os.path.splitext(video_path)
    temp_output_path = f"{file_base}_Normalized_TEMP.mkv"
    final_output_path = f"{file_base}.mkv" if file_ext.lower() != '.mkv' else video_path
    temp_files.append(temp_output_path)
    
    try:
        #! Probe audio streams
        logger.info(f"Probing audio streams.\nFile: {video_path}.")
        ffprobe_command = [
            "ffprobe", "-i", video_path,
            "-show_streams", "-select_streams", "a", "-loglevel", "quiet", "-print_format", "json"
        ]
        probe_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        audio_streams = json.loads(probe_result.stdout).get("streams", [])

        if not audio_streams:
            raise Exception("No audio streams found in the video.")

        #! First pass to analyze loudness
        logger.info("Analyzing loudness for audio normalization.\nAudio tracks: " + str(len(audio_streams)))
        loudness_metadata = []
        for i in range(len(audio_streams)):
            first_pass_command = [
                "ffmpeg", "-i", video_path,
                "-map", f"0:a:{i}",
                "-af", f"loudnorm=I={NORMALIZATION_PARAMS['I']}:TP={NORMALIZATION_PARAMS['TP']}:LRA={NORMALIZATION_PARAMS['LRA']}:print_format=json",
                "-f", "null", "-"
            ]
            first_pass_result = subprocess.run(first_pass_command, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            loudness_match = re.search(r'(\{.*?\})', first_pass_result.stderr, re.DOTALL)
            if loudness_match:
                loudness_metadata.append(json.loads(loudness_match.group(1)))

        if len(loudness_metadata) != len(audio_streams):
            raise Exception("Failed to retrieve loudness metadata for all audio streams.")

        logger.info("Loudness analysis complete. Proceeding with normalization.")

        #! Build filter complex for second pass using loudness metadata
        logger.info(f"Building FFmpeg filter complex for normalization. Metadata: {loudness_metadata}")
        filter_complex = []
        for i, metadata in enumerate(loudness_metadata):
            filter_complex.append(
                f"[0:a:{i}]loudnorm=I={NORMALIZATION_PARAMS['I']}:TP={NORMALIZATION_PARAMS['TP']}:LRA={NORMALIZATION_PARAMS['LRA']}:" 
                f"measured_I={metadata['input_i']}:measured_TP={metadata['input_tp']}:measured_LRA={metadata['input_lra']}:" 
                f"measured_thresh={metadata['input_thresh']}:offset={metadata['target_offset']}[a{i}]"
            )

        ffmpeg_command = [
            "ffmpeg", "-y", "-i", video_path,
            "-filter_complex", "; ".join(filter_complex)
        ]

        #! Map video streams and normalized audio streams
        ffmpeg_command.extend(["-map", "0:v"])
        for i, audio_stream in enumerate(audio_streams):
            original_title = audio_stream.get('tags', {}).get('title', f"Track {i + 1}")
            new_title = update_audio_track_title(original_title, "Normalized")
            ffmpeg_command.extend([f"-map", f"[a{i}]", f"-metadata:s:a:{i}", f"title={new_title}"])

        ffmpeg_command.extend(["-c:v", "copy", "-c:a", "ac3", "-b:a", "256k", temp_output_path])

        #! Execute FFmpeg command for the second pass
        logger.info(f"Running FFmpeg normalization on {video_path}")
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        if result.returncode != 0:
            raise Exception(result.stderr)

        #! Replace the original file with the normalized one
        if os.path.exists(video_path) and file_ext.lower() == '.mp4':
            os.remove(video_path)
            logger.info(f"Replacing original file:\n{video_path}")

        if os.path.exists(final_output_path):
            os.remove(final_output_path)
        os.rename(temp_output_path, final_output_path)

        return final_output_path

    except Exception as e:
        return None

    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Removed temp file: {temp_file}")
                
                
def filter_audio(video_path, volume_boost_percentage, temp_files):
    """
    Apply audio filter with volume boost to the video, handling multiple audio tracks.
    """
    file_base, file_ext = os.path.splitext(video_path)
    temp_output_path = f"{file_base}_Boosted{file_ext}"
    volume_boost = 1.0 + (volume_boost_percentage / 100.0)
    temp_files.append(temp_output_path)
    
    try:
        #! Probe audio streams
        logger.info(f"Probing audio streams.\nFile: {video_path}.")
        ffprobe_command = [
            "ffprobe",
            "-i", video_path,
            "-show_streams",
            "-select_streams", "a",
            "-loglevel", "quiet",
            "-print_format", "json"
        ]
        result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        audio_streams = json.loads(result.stdout).get("streams", [])

        if not audio_streams:
            raise Exception("No audio streams found in the video.")

        #! Build FFmpeg command
        logger.info(f"Applying volume adjustment.\n{volume_boost_percentage}% Volume Adjustment\nAudio Tracks: {len(audio_streams)}\nFile: {file_base}{file_ext}.")
        ffmpeg_command = ["ffmpeg", "-y", "-i", video_path]
        for i, stream in enumerate(audio_streams):
            original_title = stream.get('tags', {}).get('title', f"Track {i + 1}")
            new_title = update_audio_track_title(original_title, "Boosted", f"{volume_boost_percentage}%")
            ffmpeg_command.extend([
                f"-filter:a:{i}", f"volume={volume_boost}",
                f"-metadata:s:a:{i}", f"title={new_title}"
            ])
        ffmpeg_command.extend(["-c:v", "copy", "-c:a", "ac3", "-b:a", "256k", temp_output_path])

        #! Execute FFmpeg command
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        if result.returncode != 0:
            raise Exception(result.stderr)

        #! Replace the original file with the boosted one
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"Replacing original file:\n{video_path}")

        if os.path.exists(temp_output_path):
            os.rename(temp_output_path, video_path)
        return True

    except Exception as e:
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            logger.info(f"Removed temporary file:\n{temp_output_path}")
        return False
