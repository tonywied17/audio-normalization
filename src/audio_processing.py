import os
import re
import subprocess
import json
import datetime
from src.utils import log_to_file
from rich.console import Console

console = Console()

def clean_and_update_title(original_title, operation, extra_info=""):
    """
    Clean up existing prefixes/suffixes and update the title.
    """
    cleaned_title = re.sub(r"molexAudio (Normalized|Boosted \d+% )?", "", original_title).strip()
    if extra_info:
        return f"[molexAudio {operation} {extra_info}] {cleaned_title}".strip()
    else:
        return f"[molexAudio {operation}] {cleaned_title}".strip()


def normalize_audio(video_path, log_file_path, temp_files):
    """
    Normalize audio levels for all audio streams in the video
    """
    file_base, file_ext = os.path.splitext(video_path)
    temp_output_path = f"{file_base}_Normalized_TEMP.mkv"
    final_output_path = f"{file_base}.mkv" if file_ext.lower() != '.mkv' else video_path
    temp_files.append(temp_output_path)
    
    try:
        # Probe audio streams
        ffprobe_command = [
            "ffprobe", "-i", video_path,
            "-show_streams", "-select_streams", "a", "-loglevel", "quiet", "-print_format", "json"
        ]
        probe_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        audio_streams = json.loads(probe_result.stdout).get("streams", [])

        if not audio_streams:
            raise Exception("No audio streams found in the video.")

        # Build FFmpeg filter complex for loudnorm
        filter_complex = [f"[0:a:{i}]loudnorm=I=-16:TP=-1.5:LRA=11[a{i}]" for i in range(len(audio_streams))]

        ffmpeg_command = [
            "ffmpeg", "-y", "-i", video_path,
            "-filter_complex", "; ".join(filter_complex)
        ]

        ffmpeg_command.extend(["-map", "0:v"])

        # Add audio streams with proper titles
        for i, audio_stream in enumerate(audio_streams):
            original_title = audio_stream.get('tags', {}).get('title', f"Track {i + 1}")
            new_title = clean_and_update_title(original_title, "Normalized")
            ffmpeg_command.extend([f"-map", f"[a{i}]", f"-metadata:s:a:{i}", f"title={new_title}"])

        ffmpeg_command.extend(["-c:v", "copy", "-c:a", "ac3", "-b:a", "256k", temp_output_path])

        # Execute FFmpeg command
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        if result.returncode != 0:
            raise Exception(result.stderr)

        if os.path.exists(video_path) and file_ext.lower() == '.mp4':
            os.remove(video_path)
            log_to_file(log_file_path, f"{datetime.datetime.now()} | INFO | Deleted original file: {video_path}")

        if os.path.exists(final_output_path):
            os.remove(final_output_path)
        os.rename(temp_output_path, final_output_path)

        log_to_file(log_file_path, f"{datetime.datetime.now()} | SUCCESS | {video_path} normalized successfully.")
        console.print(f"\n[medium_spring_green]Processed video:[/medium_spring_green] {video_path} [bright_green](Normalized)[/bright_green]")

        return final_output_path

    except Exception as e:
        log_to_file(log_file_path, f"{datetime.datetime.now()} | ERROR | {video_path} | {e}")
        console.print(f"Error processing video: {video_path} | {e}")
        return None

    finally:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                console.print(f"[red]Removed temp file: {temp_file}[/red]")


def filter_audio(video_path, volume_boost_percentage, log_file_path, temp_files):
    """
    Apply audio filter with volume boost to the video, handling multiple audio tracks.
    """
    file_base, file_ext = os.path.splitext(video_path)
    temp_output_path = f"{file_base}_Boosted{file_ext}"
    volume_boost = 1.0 + (volume_boost_percentage / 100.0)
    temp_files.append(temp_output_path)
    
    try:
        # Probe audio streams
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

        # Build FFmpeg command
        ffmpeg_command = ["ffmpeg", "-y", "-i", video_path]
        for i, stream in enumerate(audio_streams):
            original_title = stream.get('tags', {}).get('title', f"Track {i + 1}")
            new_title = clean_and_update_title(original_title, "Boosted", f"{volume_boost_percentage}%")
            ffmpeg_command.extend([
                f"-filter:a:{i}", f"volume={volume_boost}",
                f"-metadata:s:a:{i}", f"title={new_title}"
            ])
        ffmpeg_command.extend(["-c:v", "copy", "-c:a", "ac3", "-b:a", "256k", temp_output_path])

        # Execute FFmpeg command
        result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        if result.returncode != 0:
            raise Exception(result.stderr)

        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(temp_output_path):
            os.rename(temp_output_path, video_path)

        log_to_file(log_file_path, f"{datetime.datetime.now()} | SUCCESS | {video_path} volume boost applied.")
        console.print(f"\n[medium_spring_green]Processed video:[/medium_spring_green] [bright_green](Volume Boosted {volume_boost_percentage}%)[/bright_green]")

        return True

    except Exception as e:
        log_to_file(log_file_path, f"{datetime.datetime.now()} | ERROR | {video_path} | {e}")
        console.print(f"Error processing video: {video_path} | {e}")
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        return False
