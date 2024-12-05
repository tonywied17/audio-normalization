import os
import re
import subprocess
import json
from rich.console import Console
from src.util.logger import Logger
from src.util.values import NORMALIZATION_PARAMS

class AudioProcessor:
    
    def __init__(self, temp_files=None):
        self.console = Console()
        self.logger = Logger(log_file="process.log")
        self.temp_files = temp_files
        
        
    def notify_temp_file(self, temp_file_path):
        """
        Adds the temporary file to the list and triggers a signal handler if defined.
        """
        if temp_file_path not in self.temp_files:
            self.temp_files.append(temp_file_path)
            # self.logger.info(f"Temporary file for processing.\n\n[bold]Temporary file:[/bold] {temp_file_path}")


    def update_audio_track_title(self, original_title, operation, extra_info=""):
        """
        Clean up existing prefixes/suffixes and update the title.
        """
        cleaned_title = re.sub(r"molexAudio (Normalized|Boosted \d+% )?", "", original_title).strip()
        if extra_info:
            return f"[molexAudio {operation} {extra_info}] {cleaned_title}".strip()
        else:
            return f"[molexAudio {operation}] {cleaned_title}".strip()


    def normalize_audio(self, media_path):
        """
        Normalize audio levels for all audio streams in the media using a two-pass process.
        """
        file_base, file_ext = os.path.splitext(media_path)
        temp_output_path = f"{file_base}_Normalized_TEMP.mkv"
        final_output_path = f"{file_base}.mkv" if file_ext.lower() != '.mkv' else media_path
        self.notify_temp_file(temp_output_path)

        try:
            self.logger.info(f"Probing audio streams.\n\n[bold]File:[/bold] {media_path}.")
            ffprobe_command = [
                "ffprobe", "-i", media_path,
                "-show_streams", "-select_streams", "a", "-loglevel", "quiet", "-print_format", "json"
            ]
            probe_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, text=True, encoding='utf-8')
            audio_streams = json.loads(probe_result.stdout).get("streams", [])

            if not audio_streams:
                raise Exception("No audio streams found in the media.")

            self.logger.info(f"Analyzing loudness for audio normalization.\n\n[bold]File:[/bold] {media_path}\n[bold]Audio Tracks:[/bold] {len(audio_streams)}")
            loudness_metadata = []
            for i in range(len(audio_streams)):
                first_pass_command = [
                    "ffmpeg", "-i", media_path,
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

            self.logger.info("Loudness analysis complete. Proceeding with normalization.\n\n[bold]Normalization Parameters:[/bold]\n" 
                + json.dumps(NORMALIZATION_PARAMS, indent=4)
                + "\n[bold]Analysis Metadata:[/bold]\n" 
                + json.dumps(loudness_metadata, indent=4))
            
            filter_complex = []
            for i, metadata in enumerate(loudness_metadata):
                filter_complex.append(
                    f"[0:a:{i}]loudnorm=I={NORMALIZATION_PARAMS['I']}:TP={NORMALIZATION_PARAMS['TP']}:LRA={NORMALIZATION_PARAMS['LRA']}:" 
                    f"measured_I={metadata['input_i']}:measured_TP={metadata['input_tp']}:measured_LRA={metadata['input_lra']}:" 
                    f"measured_thresh={metadata['input_thresh']}:offset={metadata['target_offset']}[a{i}]"
                )

            ffmpeg_command = [
                "ffmpeg", "-y", "-i", media_path,
                "-filter_complex", "; ".join(filter_complex),
                "-map", "0:v"
            ]
            for i, audio_stream in enumerate(audio_streams):
                original_title = audio_stream.get('tags', {}).get('title', f"Track {i + 1}")
                new_title = self.update_audio_track_title(original_title, "Normalized")
                ffmpeg_command.extend([f"-map", f"[a{i}]", f"-metadata:s:a:{i}", f"title={new_title}"])

            ffmpeg_command.extend(["-c:v", "copy", "-c:a", "ac3", "-b:a", "256k", temp_output_path])

            self.logger.info(f"Running FFmpeg normalization.\n\n [bold]File:[/bold] {media_path}\n[bold]Temporary Output:[/bold] {temp_output_path}")
            result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            if result.returncode != 0:
                raise Exception(result.stderr)

            if os.path.exists(media_path) and file_ext.lower() == '.mp4':
                os.remove(media_path)
                self.logger.info(f"[bold]Replacing original file:[/bold]\n{media_path}")

            if os.path.exists(final_output_path):
                os.remove(final_output_path)
            os.rename(temp_output_path, final_output_path)
            
            self.logger.success(f"Normalization completed.\n[bold]File:[/bold] {media_path}")
            return final_output_path

        except Exception as e:
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
                self.logger.info(f"Removed temporary file:\n{temp_output_path}")
            self.logger.error(f"Normalization failed.\n[bold]File:[/bold] {media_path}\nError: {e}")
            return None


    def filter_audio(self, media_path, volume_boost_percentage):
        """
        Apply audio filter with volume boost to the media, handling multiple audio tracks.
        """
        file_base, file_ext = os.path.splitext(media_path)
        temp_output_path = f"{file_base}_Boosted{file_ext}"
        volume_boost = 1.0 + (volume_boost_percentage / 100.0)
        self.notify_temp_file(temp_output_path)

        try:
            self.logger.info(f"Probing audio streams.\n\n[bold]File:[/bold] {media_path}.")
            ffprobe_command = [
                "ffprobe", "-i", media_path, "-show_streams",
                "-select_streams", "a", "-loglevel", "quiet", "-print_format", "json"
            ]
            result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, text=True, encoding='utf-8')
            audio_streams = json.loads(result.stdout).get("streams", [])

            if not audio_streams:
                raise Exception("No audio streams found in the media.")

            self.logger.info(f"Applying volume adjustment: {volume_boost_percentage}%.")
            ffmpeg_command = ["ffmpeg", "-y", "-i", media_path]
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f"Track {i + 1}")
                new_title = self.update_audio_track_title(original_title, "Boosted", f"{volume_boost_percentage}%")
                ffmpeg_command.extend([
                    f"-filter:a:{i}", f"volume={volume_boost}",
                    f"-metadata:s:a:{i}", f"title={new_title}"
                ])
            ffmpeg_command.extend(["-c:v", "copy", "-c:a", "ac3", "-b:a", "256k", temp_output_path])

            result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            if result.returncode != 0:
                raise Exception(result.stderr)

            if os.path.exists(media_path):
                os.remove(media_path)
                self.logger.info(f"[bold]Replacing original file:[/bold]\n{media_path}")

            if os.path.exists(temp_output_path):
                os.rename(temp_output_path, media_path)

            self.logger.success(f"Volume adjustment completed: {volume_boost_percentage}%.")
            return True

        except Exception as e:
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
                self.logger.info(f"Removed temporary file:\n{temp_output_path}")
            self.logger.error(f"Volume adjustment failed: {e}")
            return False
