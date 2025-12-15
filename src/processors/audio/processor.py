"""
Main AudioProcessor implementation, using modular helpers.
"""

import os
import re
import json
from typing import Optional, List, Dict, Any
from core.config import NORMALIZATION_PARAMS, AUDIO_CODEC, AUDIO_BITRATE
from core.logger import Logger
from core.signal_handler import SignalHandler
from .runner import run_command, popen
from .probe import get_audio_streams, get_video_streams
from .utils import update_track_title, create_temp_file, channels_to_layout
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.text import Text


class AudioProcessor:
    def __init__(self):
        self.logger = Logger()

    def _get_audio_streams(self, media_path: str):
        """Compatibility wrapper for existing callers that used a private method."""
        return get_audio_streams(media_path, self.logger)

    def normalize_audio(self, media_path: str, show_ui: bool = False, progress_callback=None) -> Optional[str]:
        """Normalize audio tracks in the given media file."""
        try:
            audio_streams = get_audio_streams(media_path, self.logger)
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
                if progress_callback:
                    process = popen(analyze_cmd)
                    ffmpeg_log = []
                    try:
                        SignalHandler.register_child_pid(process.pid)
                    except Exception:
                        pass
                    try:
                        for line in process.stderr:
                            last_line = line.strip()
                            ffmpeg_log.append(last_line)
                            if last_line:
                                try:
                                    progress_callback("analyzing", last_line=last_line)
                                except Exception:
                                    pass
                        process.wait()
                    finally:
                        try:
                            SignalHandler.unregister_child_pid(process.pid)
                        except Exception:
                            pass
                    stderr_output = "\n".join(ffmpeg_log)
                    match = re.search(r'\{.*\}', stderr_output, re.DOTALL)
                    if not match:
                        raise ValueError(f"Failed to get loudness data for stream {i}")
                    loudness_data.append(json.loads(match.group()))
                else:
                    result = run_command(analyze_cmd)
                    match = re.search(r'\{.*\}', result.stderr, re.DOTALL)
                    if not match:
                        raise ValueError(f"Failed to get loudness data for stream {i}")
                    loudness_data.append(json.loads(match.group()))

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

            temp_output = create_temp_file(media_path)
            video_streams = get_video_streams(media_path)
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", media_path, "-threads", "0", "-filter_complex", ";".join(filter_parts)]
            if video_streams:
                ffmpeg_cmd.extend(["-map", "0:v"])

            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = update_track_title(original_title, "Normalized")
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

            if progress_callback:
                try:
                    progress_callback("normalizing")
                except Exception:
                    pass
            if progress_callback:
                process = popen(ffmpeg_cmd)
                ffmpeg_log = []
                try:
                    SignalHandler.register_child_pid(process.pid)
                except Exception:
                    pass
                try:
                    for line in process.stderr:
                        last_line = line.strip()
                        ffmpeg_log.append(last_line)
                        if last_line:
                            try:
                                progress_callback("normalizing", last_line=last_line)
                            except Exception:
                                pass
                    process.wait()
                finally:
                    try:
                        SignalHandler.unregister_child_pid(process.pid)
                    except Exception:
                        pass
                try:
                    if ffmpeg_log:
                        self.logger.log_ffmpeg("NORMALIZE", media_path, "\n".join(ffmpeg_log))
                except Exception:
                    pass
                if process.returncode != 0:
                    self.logger.error(f"Normalization failed for {media_path}: ffmpeg exit {process.returncode}")
                    if 'temp_output' in locals() and os.path.exists(temp_output):
                        try:
                            SignalHandler.unregister_temp_file(temp_output)
                        except Exception:
                            pass
                        os.remove(temp_output)
                    return None
            else:
                run_command(ffmpeg_cmd, capture_output=(not show_ui))

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


    def boost_audio(self, media_path: str, boost_percent: float, show_ui: bool = False, dry_run: bool = False, progress_callback=None) -> Optional[str]:
        """Boost audio tracks in the given media file by the specified percentage."""
        try:
            self.logger.info(f"Starting volume boost ({boost_percent}%): {media_path}")

            audio_streams = get_audio_streams(media_path, self.logger)
            if not audio_streams:
                raise ValueError("No audio streams found")

            self.logger.info(f"Found {len(audio_streams)} audio stream(s)")
            
            volume_multiplier = 1.0 + (boost_percent / 100.0)

            temp_output = create_temp_file(media_path)

            filter_parts = []
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = update_track_title(original_title, "Boosted", f"{boost_percent}%")
                ch = int(stream.get('channels', 0) or 0)
                layout = channels_to_layout(ch)
                try:
                    sr = int(stream.get('sample_rate') or 48000)
                except Exception:
                    sr = 48000
                filter_parts.append(
                    f"[0:a:{i}]aformat=channel_layouts={layout}:sample_fmts=s16:sample_rates={sr},volume={volume_multiplier}[a{i}]"
                )

            ffmpeg_cmd = ["ffmpeg", "-y", "-i", media_path, "-threads", "0", "-filter_complex", ";".join(filter_parts)]
            video_streams = get_video_streams(media_path)
            if video_streams:
                ffmpeg_cmd.extend(["-map", "0:v"]) 

            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = update_track_title(original_title, "Boosted", f"{boost_percent}%")
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
                    ffmpeg_command_str = ' '.join(ffmpeg_cmd)
                    try:
                        self.logger.log_ffmpeg("BOOST_CMD_ARGS", media_path, repr(ffmpeg_cmd))
                    except Exception:
                        pass
                    try:
                        self.logger.log_ffmpeg("BOOST_CMD", media_path, ffmpeg_command_str)
                    except Exception:
                        pass
                    process = popen(ffmpeg_cmd)
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
                        if progress_callback:
                            try:
                                progress_callback("boosting", last_line=last_line)
                            except Exception:
                                pass
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
                if progress_callback:
                    if dry_run:
                        return media_path
                    process = popen(ffmpeg_cmd)
                    ffmpeg_log = []
                    try:
                        SignalHandler.register_child_pid(process.pid)
                    except Exception:
                        pass
                    try:
                        for line in process.stderr:
                            last_line = line.strip()
                            ffmpeg_log.append(last_line)
                            if last_line:
                                try:
                                    progress_callback("boosting", last_line=last_line)
                                except Exception:
                                    pass
                        process.wait()
                    finally:
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
                        result = run_command(ffmpeg_cmd, capture_output=True)
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
