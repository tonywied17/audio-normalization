"""
Audio processing module for normalization and boosting.
"""

import os
import re
import subprocess
import json
from typing import Optional, List, Dict, Any, Tuple
from .config import NORMALIZATION_PARAMS, AUDIO_CODEC, AUDIO_BITRATE, TEMP_SUFFIX
from .logger import Logger
from .signal_handler import SignalHandler
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.text import Text


class AudioProcessor:
    def __init__(self):
        self.logger = Logger()

    def _run_command(self, command: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a subprocess command and return the CompletedProcess."""
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                encoding='utf-8',
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed: {' '.join(command)}\n{e.stderr}")


    def _get_audio_streams(self, media_path: str) -> List[Dict[str, Any]]:
        """Retrieve audio stream information using ffprobe."""
        ffprobe_cmd = [
            "ffprobe", "-i", media_path,
            "-show_streams", "-select_streams", "a",
            "-loglevel", "quiet", "-print_format", "json"
        ]
        try:
            result = self._run_command(ffprobe_cmd)
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            if not streams:
                try:
                    fallback_cmd = [
                        "ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index,codec_name,channels,tags", "-print_format", "json", media_path
                    ]
                    fallback_proc = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                    fallback_data = json.loads(fallback_proc.stdout) if fallback_proc.stdout else {}
                    streams = fallback_data.get("streams", [])
                    self.logger.info(f"ffprobe fallback returned {len(streams)} audio streams for {media_path}")
                except Exception:
                    streams = []
                if not streams:
                    try:
                        probe_count_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", media_path]
                        probe_count_proc = subprocess.run(probe_count_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                        lines = probe_count_proc.stdout.strip().splitlines()
                        if lines:
                            self.logger.info(f"Creating {len(lines)} placeholder audio stream entries for {media_path}")
                            streams = []
                            for idx in range(len(lines)):
                                streams.append({"index": idx, "tags": {}})
                    except Exception:
                        pass
            return streams
        except Exception as e:
            self.logger.error(f"ffprobe failed: {e}")
            return []


    def _get_video_streams(self, media_path: str) -> List[Dict[str, Any]]:
        """Retrieve video stream information using ffprobe."""
        ffprobe_cmd = [
            "ffprobe", "-i", media_path,
            "-show_streams", "-select_streams", "v",
            "-loglevel", "quiet", "-print_format", "json"
        ]
        result = self._run_command(ffprobe_cmd)
        data = json.loads(result.stdout)
        return data.get("streams", [])


    def _update_track_title(self, original_title: str, operation: str, extra: str = "") -> str:
        """Update the track title to reflect the processing done."""
        cleaned = re.sub(r"\[molexAudio (Normalized|Boosted [^]]+)\] ?", "", original_title).strip()
        tag = f"[molexAudio {operation}"
        if extra:
            tag += f" {extra}"
        tag += "]"
        return f"{tag} {cleaned}".strip()


    def _create_temp_file(self, original_path: str) -> str:
        """Create a temporary file path for processing."""
        base, ext = os.path.splitext(original_path)
        temp_path = f"{base}{TEMP_SUFFIX}{ext}"
        try:
            SignalHandler.register_temp_file(temp_path)
        except Exception:
            pass
        return temp_path


    def normalize_audio(self, media_path: str, show_ui: bool = False, progress_callback=None) -> Optional[str]:
        """Apply loudness normalization to all audio streams."""
        try:
            audio_streams = self._get_audio_streams(media_path)
            if not audio_streams:
                raise ValueError("No audio streams found")

            self.logger.info(f"Found {len(audio_streams)} audio stream(s)")

            loudness_data = []
            for i, stream in enumerate(audio_streams):
                if progress_callback:
                    try:
                        progress_callback("analyzing", last_line=f"Stream {i+1}...")
                    except Exception:
                        pass
                analyze_cmd = [
                    "ffmpeg", "-i", media_path,
                    "-threads", "0",
                    "-map", f"0:a:{i}",
                    "-af", f"loudnorm=I={NORMALIZATION_PARAMS['I']}:TP={NORMALIZATION_PARAMS['TP']}:LRA={NORMALIZATION_PARAMS['LRA']}:print_format=json",
                    "-f", "null", "-"
                ]
                result = self._run_command(analyze_cmd)
                match = re.search(r'\{.*\}', result.stderr, re.DOTALL)
                if not match:
                    raise ValueError(f"Failed to get loudness data for stream {i}")
                loudness_data.append(json.loads(match.group()))

            # Notify caller that analysis finished and show detected params
            if progress_callback:
                try:
                    progress_callback("show_params")
                except Exception:
                    pass

            filter_parts = []
            for i, metadata in enumerate(loudness_data):
                filter_parts.append(
                    f"[0:a:{i}]loudnorm="
                    f"I={NORMALIZATION_PARAMS['I']}:"
                    f"TP={NORMALIZATION_PARAMS['TP']}:"
                    f"LRA={NORMALIZATION_PARAMS['LRA']}:"
                    f"measured_I={metadata['input_i']}:"
                    f"measured_TP={metadata['input_tp']}:"
                    f"measured_LRA={metadata['input_lra']}:"
                    f"measured_thresh={metadata['input_thresh']}:"
                    f"offset={metadata.get('target_offset', 0)}"
                    f"[a{i}]"
                )

            temp_output = self._create_temp_file(media_path)
            video_streams = self._get_video_streams(media_path)
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", media_path, "-threads", "0", "-filter_complex", ";".join(filter_parts)]
            if video_streams:
                ffmpeg_cmd.extend(["-map", "0:v"])

            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self._update_track_title(original_title, "Normalized")
                ffmpeg_cmd.extend([
                    "-map", f"[a{i}]",
                    f"-metadata:s:a:{i}", f"title={new_title}"
                ])

            ffmpeg_cmd.extend([
                "-c:v", "copy",
                "-c:a", AUDIO_CODEC,
                "-b:a", AUDIO_BITRATE,
                temp_output
            ])

            # self.logger.info("Applying normalization...")
            # self.logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            if progress_callback:
                try:
                    progress_callback("normalizing")
                except Exception:
                    pass
            self._run_command(ffmpeg_cmd, capture_output=(not show_ui))

            final_path = media_path
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_output, final_path)
            try:
                SignalHandler.unregister_temp_file(temp_output)
            except Exception:
                pass

            self.logger.success(f"Normalization complete: {media_path}")
            return final_path

        except Exception as e:
            self.logger.error(f"Normalization failed for {media_path}: {e}")
            if 'temp_output' in locals() and os.path.exists(temp_output):
                try:
                    SignalHandler.unregister_temp_file(temp_output)
                except Exception:
                    pass
                os.remove(temp_output)
            return None


    def boost_audio(self, media_path: str, boost_percent: float, show_ui: bool = False, dry_run: bool = False) -> Optional[str]:
        """Boost the volume of all audio streams by a specified percentage."""
        try:
            self.logger.info(f"Starting volume boost ({boost_percent}%): {media_path}")

            audio_streams = self._get_audio_streams(media_path)
            if not audio_streams:
                raise ValueError("No audio streams found")

            self.logger.info(f"Found {len(audio_streams)} audio stream(s)")
            
            volume_multiplier = 1.0 + (boost_percent / 100.0)

            temp_output = self._create_temp_file(media_path)
            def _channels_to_layout(ch: int) -> str:
                return {1: 'mono', 2: 'stereo', 6: '5.1', 8: '7.1'}.get(ch, 'stereo')

            filter_parts = []
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self._update_track_title(original_title, "Boosted", f"{boost_percent}%")
                ch = int(stream.get('channels', 0) or 0)
                layout = _channels_to_layout(ch)
                try:
                    sr = int(stream.get('sample_rate') or 48000)
                except Exception:
                    sr = 48000
                filter_parts.append(
                    f"[0:a:{i}]aformat=channel_layouts={layout}:sample_fmts=s16:sample_rates={sr},volume={volume_multiplier}[a{i}]"
                )

            ffmpeg_cmd = ["ffmpeg", "-y", "-i", media_path, "-threads", "0", "-filter_complex", ";".join(filter_parts)]
            video_streams = self._get_video_streams(media_path)
            if video_streams:
                ffmpeg_cmd.extend(["-map", "0:v"]) 

            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self._update_track_title(original_title, "Boosted", f"{boost_percent}%")
                ffmpeg_cmd.extend(["-map", f"[a{i}]"])
                ffmpeg_cmd.extend([f"-metadata:s:a:{i}", f"title={new_title}"])
            max_channels = 0
            for s in audio_streams:
                try:
                    ch = int(s.get('channels', 0) or 0)
                except Exception:
                    ch = 0
                max_channels = max(max_channels, ch)
            if max_channels <= 0:
                max_channels = 2
            ffmpeg_cmd.extend(["-c:v", "copy", "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE, "-ac", str(max_channels), temp_output])
            
            run_success = False
            if show_ui:
                console = Console()
                with Live(console=console, refresh_per_second=8) as live:
                    spinner = Spinner("dots", text=Text.from_markup(f"[bold green]Boosting {len(audio_streams)} audio track{'s' if len(audio_streams) != 1 else ''} by {boost_percent}%...[/bold green]"), style="green")
                    live.update(Panel(spinner, title="Boosting audio", border_style="green"))
                    import subprocess
                    ffmpeg_command_str = ' '.join(ffmpeg_cmd)
                    # self.logger.info(f"FFmpeg command: {ffmpeg_command_str}")
                    try:
                        self.logger.log_ffmpeg("BOOST_CMD_ARGS", media_path, repr(ffmpeg_cmd))
                    except Exception:
                        pass
                    try:
                        self.logger.log_ffmpeg("BOOST_CMD", media_path, ffmpeg_command_str)
                    except Exception:
                        pass
                    process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                    ffmpeg_log = []
                    try:
                        SignalHandler.register_child_pid(process.pid)
                    except Exception:
                        pass
                    for line in process.stderr:
                        last_line = line.strip()
                        ffmpeg_log.append(last_line)
                        if last_line:
                            spinner.text = Text.from_markup(f"[bold green]Boosting {len(audio_streams)} audio track{'s' if len(audio_streams) != 1 else ''} by {boost_percent}%...[/bold green]\n{last_line}")
                        else:
                            spinner.text = Text.from_markup(f"[bold green]Boosting {len(audio_streams)} audio track{'s' if len(audio_streams) != 1 else ''} by {boost_percent}%...[/bold green]")
                        live.update(Panel(spinner, title="Boosting audio", border_style="green"))
                    process.wait()
                    try:
                        SignalHandler.unregister_child_pid(process.pid)
                    except Exception:
                        pass

                    try:
                        if ffmpeg_log:
                            self.logger.log_ffmpeg("BOOST", media_path, "\n".join(ffmpeg_log))
                    except Exception:
                        pass

                    if process.returncode != 0:
                        self.logger.error(f"Boost failed for {media_path}: ffmpeg exit {process.returncode}")
                        if os.path.exists(temp_output):
                            try:
                                SignalHandler.unregister_temp_file(temp_output)
                            except Exception:
                                pass
                            try:
                                os.remove(temp_output)
                            except Exception:
                                pass
                        return None
                    run_success = True

            else:
                if dry_run:
                    return media_path
                try:
                    result = self._run_command(ffmpeg_cmd, capture_output=True)
                    try:
                        if result.stderr:
                            self.logger.log_ffmpeg("BOOST", media_path, result.stderr)
                    except Exception:
                        pass
                    run_success = True
                except Exception as e:
                    try:
                        self.logger.log_ffmpeg("BOOST_ERROR", media_path, str(e))
                    except Exception:
                        pass
                    self.logger.error(f"Boost failed for {media_path}: {e}")
                    if os.path.exists(temp_output):
                        try:
                            SignalHandler.unregister_temp_file(temp_output)
                        except Exception:
                            pass
                        try:
                            os.remove(temp_output)
                        except Exception:
                            pass
                    return None
            if not run_success:
                return None
            if not os.path.exists(temp_output):
                self.logger.error(f"Expected temp output not found: {temp_output}")
                return None
            final_path = media_path
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_output, final_path)
            try:
                SignalHandler.unregister_temp_file(temp_output)
            except Exception:
                pass
            self.logger.success(f"Boost complete: {media_path}")
            return final_path
        except Exception as e:
            self.logger.error(f"Boost failed for {media_path}: {e}")
            if 'temp_output' in locals() and os.path.exists(temp_output):
                try:
                    SignalHandler.unregister_temp_file(temp_output)
                except Exception:
                    pass
                try:
                    os.remove(temp_output)
                except Exception:
                    pass
            return None