import os
import threading
from typing import List, Dict, Any, Optional
from rich.console import Console
from .config import SUPPORTED_EXTENSIONS, TEMP_SUFFIX, AUDIO_CODEC, AUDIO_BITRATE
from .logger import Logger
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from .audio_processor import AudioProcessor

def get_audio_track_count(filepath: str) -> int:
    """Return the number of audio streams in the media file using ffprobe."""
    import subprocess
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", filepath
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", check=True)
        lines = result.stdout.strip().splitlines()
        return len(lines)
    except Exception:
        return 0

class BatchProcessor:
    def boost_files_with_progress(self, directory: str, boost_percent: float, dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        from rich.text import Text
        from rich.console import Group
        import subprocess
        files = self.find_media_files(directory)
        valid_files = [f for f in files if TEMP_SUFFIX not in os.path.basename(f)]
        results = [{"file": valid_files[i], "task": f"Boost {boost_percent}% Audio", "status": "Waiting"} for i in range(len(valid_files))]
        spinners = [Spinner("dots", text=Text.from_markup(f"[bold magenta]Waiting...[/bold magenta]"), style="green") for _ in valid_files]
        panels = [Panel(spinners[i], title=f"{os.path.basename(valid_files[i])}", border_style="green") for i in range(len(valid_files))]
        statuses = ["waiting" for _ in valid_files]

        def worker(idx, file, output_path):
            import time
            audio_tracks = get_audio_track_count(file)
            statuses[idx] = "in-progress"
            results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "In Progress"}
            if live_ref.get("live"):
                try:
                    live_ref["live"].update(render_group())
                except Exception:
                    pass
            def update_panel(stage, last_line=None, error=False):
                if stage == "boosting":
                    text = f"[bold green]Boosting {audio_tracks} audio track{'s' if audio_tracks != 1 else ''} by {boost_percent}%...[/bold green]"
                    if last_line:
                        text += f"\n{last_line}"
                    spinners[idx].text = Text.from_markup(text)
                    panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file)}", border_style="red" if error else "green")
                    if live_ref["live"]:
                        try:
                            live_ref["live"].update(render_group())
                        except Exception:
                            pass
                elif stage == "finalizing":
                    spinners[idx].text = Text.from_markup("[green]Finalizing...[/green]")
                    panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file)}", border_style="magenta")
                    if live_ref["live"]:
                        try:
                            live_ref["live"].update(render_group())
                        except Exception:
                            pass
                elif stage == "success":
                    spinners[idx].text = Text.from_markup("[bold green]Boost complete[/bold green]")
                    panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file)}", border_style="green")
                    if live_ref["live"]:
                        try:
                            live_ref["live"].update(render_group())
                        except Exception:
                            pass
                        
            audio_streams = self.audio_processor._get_audio_streams(file)
            video_streams = self.audio_processor._get_video_streams(file)
            volume_multiplier = 1.0 + (boost_percent / 100.0)
            temp_output = self.audio_processor._create_temp_file(file)
            # build filter_complex style command for boosting
            def _channels_to_layout(ch: int) -> str:
                return {1: 'mono', 2: 'stereo', 6: '5.1', 8: '7.1'}.get(ch, 'stereo')
            filter_parts = []
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self.audio_processor._update_track_title(original_title, "Boosted", f"{boost_percent}%")
                ch = int(stream.get('channels', 0) or 0)
                layout = _channels_to_layout(ch)
                try:
                    sr = int(stream.get('sample_rate') or 48000)
                except Exception:
                    sr = 48000
                filter_parts.append(
                    f"[0:a:{i}]volume={volume_multiplier},aformat=channel_layouts={layout}:sample_fmts=s16:sample_rates={sr}[a{i}]"
                )
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", file, "-threads", "0", "-filter_complex", ";".join(filter_parts)]
            if video_streams:
                ffmpeg_cmd.extend(["-map", "0:v"])  # Copy video if present
            # map filtered audio outputs and set metadata separately
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self.audio_processor._update_track_title(original_title, "Boosted", f"{boost_percent}%")
                ffmpeg_cmd.extend(["-map", f"[a{i}]"])
                ffmpeg_cmd.extend([f"-metadata:s:a:{i}", f"title={new_title}"])
            # determine maximum channel count from streams to avoid channel layout change errors
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
            update_panel("boosting")
            try:
                ffmpeg_command_str = ' '.join(ffmpeg_cmd)
                self.logger.info(f"FFmpeg command: {ffmpeg_command_str}")
                try:
                    with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                        logf.write(f"\n[BOOST_CMD_ARGS] {file}:\n{repr(ffmpeg_cmd)}\n")
                except Exception:
                    pass
                try:
                    with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                        logf.write(f"\n[BOOST_CMD] {file}:\n{ffmpeg_command_str}\n")
                except Exception:
                    pass
                if dry_run:
                    update_panel("boosting", last_line="(dry-run) Command built", error=False)
                    statuses[idx] = "done"
                    results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Dry Run"}
                    update_panel("success")
                    return

                process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                ffmpeg_log = []
                try:
                    from .signal_handler import SignalHandler
                    SignalHandler.register_child_pid(process.pid)
                except Exception:
                    pass
                try:
                    from .signal_handler import SignalHandler
                    SignalHandler.register_child_pid(process.pid)
                except Exception:
                    pass
                for line in process.stderr:
                    last_line = line.strip()
                    ffmpeg_log.append(last_line)
                    update_panel("boosting", last_line=last_line)
                process.wait()
                try:
                    from .signal_handler import SignalHandler
                    SignalHandler.unregister_child_pid(process.pid)
                except Exception:
                    pass
                if process.returncode != 0:
                    try:
                        with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                            logf.write(f"\n[BOOST] {file}:\n" + "\n".join(ffmpeg_log) + "\n")
                    except Exception:
                        pass
                    update_panel("boosting", last_line="Boost failed", error=True)
                    statuses[idx] = "failed"
                    results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Failed"}
                    return
                final_path = file
                try:
                    if os.path.exists(temp_output):
                        if os.path.exists(final_path):
                            os.remove(final_path)
                        os.rename(temp_output, final_path)
                        try:
                            from .signal_handler import SignalHandler
                            SignalHandler.unregister_temp_file(temp_output)
                        except Exception:
                            pass
                    else:
                        update_panel("boosting", last_line="Temporary output not found", error=True)
                        statuses[idx] = "failed"
                        results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Failed"}
                        return
                except Exception as e:
                    update_panel("boosting", last_line=f"Finalizing failed: {e}", error=True)
                    statuses[idx] = "failed"
                    results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Failed"}
                    return
                # Success
                update_panel("finalizing")
                statuses[idx] = "done"
                results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Success"}
                self.logger.success(f"Boost complete: {file}")
                update_panel("success")
                time.sleep(0.25)
            except Exception as e:
                update_panel("boosting", last_line=str(e), error=True)
                statuses[idx] = "failed"
                results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Failed"}

        threads = []

        from queue import Queue
        task_queue: Queue = Queue()
        for idx, file in enumerate(valid_files):
            task_queue.put((idx, file))
        from rich.console import Group
        def render_group():
            return Group(*(p for p in panels if p is not None))
        live_ref = {"live": None}
        num_workers = min(max_workers or self.max_workers, len(valid_files)) if valid_files else 0
        if num_workers <= 0:
            num_workers = 1
        def queue_worker():
            while True:
                try:
                    idx, file = task_queue.get(block=False)
                except Exception:
                    break
                output_path = file
                statuses[idx] = "in-progress"
                results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "In Progress"}
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group())
                    except Exception:
                        pass
                worker(idx, file, output_path)
                task_queue.task_done()
        with Live(render_group(), refresh_per_second=8, console=self.console) as live:
            live_ref["live"] = live
            for _ in range(num_workers):
                t = threading.Thread(target=queue_worker)
                threads.append(t)
                t.start()
            import time
            while any(t.is_alive() for t in threads) or not task_queue.empty():
                time.sleep(0.1)
        for t in threads:
            t.join()
        return results
    def __init__(self, max_workers: Optional[int] = None):
        self.console = Console()
        self.logger = Logger()
        if max_workers is None:
            try:
                detected = os.cpu_count() or 1
            except Exception:
                detected = 1
            self.max_workers = detected
        else:
            try:
                mw = int(max_workers)
                self.max_workers = mw if mw > 0 else 1
            except Exception:
                self.max_workers = os.cpu_count() or 1
        self.logger.info(f"BatchProcessor max_workers set to: {self.max_workers}")
        self.audio_processor = AudioProcessor()

    def process_single_file_with_progress(self, file: str, dry_run: bool = False) -> Dict[str, Any]:
        output_path = file 
        if dry_run:
            try:
                from rich.text import Text
                audio_tracks = get_audio_track_count(file)
                audio_streams = self.audio_processor._get_audio_streams(file)
                loudness_data = []
                for i, stream in enumerate(audio_streams):
                    analyze_cmd = [
                        "ffmpeg", "-i", file, "-threads", "0", "-map", f"0:a:{i}",
                        "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"
                    ]
                    import subprocess, re, json
                    process = subprocess.run(analyze_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                    match = re.search(r'\{.*\}', process.stderr, re.DOTALL)
                    if match:
                        loudness_data.append(json.loads(match.group()))
                filter_parts = []
                for i, metadata in enumerate(loudness_data):
                    filter_parts.append(
                        f"[0:a:{i}]loudnorm="
                        f"I=-16:TP=-1.5:LRA=11:"
                        f"measured_I={metadata['input_i']}:"
                        f"measured_TP={metadata['input_tp']}:"
                        f"measured_LRA={metadata['input_lra']}:"
                        f"measured_thresh={metadata['input_thresh']}:"
                        f"offset={metadata.get('target_offset', 0)}"
                        f"[a{i}]"
                    )
                ffmpeg_cmd = ["ffmpeg", "-y", "-i", file, "-threads", "0", "-filter_complex", ";".join(filter_parts)]
                video_streams = self.audio_processor._get_video_streams(file)
                if video_streams:
                    ffmpeg_cmd.extend(["-map", "0:v"])
                for i, stream in enumerate(audio_streams):
                    original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                    new_title = self.audio_processor._update_track_title(original_title, "Normalized")
                    ffmpeg_cmd.extend(["-map", f"[a{i}]", f"-metadata:s:a:{i}", f"title={new_title}"])
                ffmpeg_cmd.extend(["-c:v", "copy", "-c:a", AUDIO_CODEC, "-b:a", AUDIO_BITRATE, self.audio_processor._create_temp_file(file)])
                self.logger.info(f"Dry run FFmpeg command: {' '.join(ffmpeg_cmd)}")
                success = True
            except Exception:
                success = False
        else:
            success = self._normalize_with_rich_ui(file, output_path, self.console)
        return {
            "file": file,
            "task": "Normalize Audio",
            "status": "Success" if success else "Failed"
        }

    def _normalize_with_rich_ui(self, input_path: str, output_path: str, console: Optional[Console] = None, update_panel=None) -> bool:
        from rich.text import Text
        import time
        import subprocess, re, json
        audio_tracks = get_audio_track_count(input_path)
        
        if update_panel:
            audio_streams = self.audio_processor._get_audio_streams(input_path)
            if not audio_streams:
                update_panel("analyzing", last_line="No audio streams found", error=True)
                return False
            loudness_data = []
            for i, stream in enumerate(audio_streams):
                update_panel("analyzing", last_line=f"Stream {i+1}...")
                analyze_cmd = [
                    "ffmpeg", "-i", input_path, "-threads", "0", "-map", f"0:a:{i}",
                    "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"
                ]
                process = subprocess.run(analyze_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                match = re.search(r'\{.*\}', process.stderr, re.DOTALL)
                if not match:
                    update_panel("analyzing", last_line=f"Failed to get loudness data for stream {i+1}", error=True)
                    return False
                data = json.loads(match.group())
                loudness_data.append(data)

            filter_parts = []
            for i, metadata in enumerate(loudness_data):
                filter_parts.append(
                    f"[0:a:{i}]loudnorm="
                    f"I=-16:TP=-1.5:LRA=11:"
                    f"measured_I={metadata['input_i']}:"
                    f"measured_TP={metadata['input_tp']}:"
                    f"measured_LRA={metadata['input_lra']}:"
                    f"measured_thresh={metadata['input_thresh']}"
                    f"[a{i}]"
                )
            temp_output = self.audio_processor._create_temp_file(input_path)
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", input_path, "-threads", "0",
                "-filter_complex", ";".join(filter_parts),
                "-map", "0:v"
            ]
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self.audio_processor._update_track_title(original_title, "Normalized")
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
            update_panel("normalizing")
            process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            for line in process.stderr:
                last_line = line.strip()
                update_panel("normalizing", last_line=last_line)
            process.wait()
            if process.returncode != 0:
                update_panel("normalizing", last_line="Normalization failed", error=True)
                return False

            final_path = input_path
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_output, final_path)
            update_panel("finalizing")
            time.sleep(0.5)
            return True
        else:

            video_streams = self.audio_processor._get_video_streams(input_path)
            loudness_data = []
            with Live(console=console, refresh_per_second=8) as live:
                spinner = Spinner("dots", text=Text.from_markup(f"[bold bright_blue]Analyzing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"), style="blue")
                live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))

                time.sleep(0.15)

                audio_streams = self.audio_processor._get_audio_streams(input_path)
                if not audio_streams:
                    spinner.text = Text.from_markup("[red]No audio streams found[/red]")
                    live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="red"))

                    try:
                        import subprocess
                        probe_cmd = ["ffprobe", "-v", "error", "-show_streams", "-select_streams", "a", "-print_format", "json", input_path]
                        proc = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                        self.logger.error(f"ffprobe stdout: {proc.stdout}")
                        self.logger.error(f"ffprobe stderr: {proc.stderr}")
                        try:
                            with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                                logf.write(f"\n[FFPROBE] {input_path}:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}\n")
                        except Exception:
                            pass
                    except Exception as e:
                        self.logger.error(f"Failed to run ffprobe for diagnostics: {e}")
                    return False
                for i, stream in enumerate(audio_streams):
                    spinner.text = Text.from_markup(f"[bold bright_blue]Analyzing stream {i+1} of {len(audio_streams)}...[/bold bright_blue]")
                    live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))
                    analyze_cmd = [
                        "ffmpeg", "-i", input_path, "-threads", "0", "-map", f"0:a:{i}",
                        "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"
                    ]
                    process = subprocess.run(analyze_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                    match = re.search(r'\{.*\}', process.stderr, re.DOTALL)
                    if not match:
                        spinner.text = Text.from_markup(f"[red]Failed to get loudness data for stream {i+1}[/red]")
                        live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="red"))
                        return False
                    data = json.loads(match.group())
                    loudness_data.append(data)
                    
                    time.sleep(0.05)

                spinner.text = Text.from_markup(f"[bold bright_blue]Analysis Complete! Running normalization pass...[/bold bright_blue]")
                live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))

            filter_parts = []
            for i, metadata in enumerate(loudness_data):
                filter_parts.append(
                    f"[0:a:{i}]loudnorm="
                    f"I=-16:TP=-1.5:LRA=11:"
                    f"measured_I={metadata['input_i']}:"
                    f"measured_TP={metadata['input_tp']}:"
                    f"measured_LRA={metadata['input_lra']}:"
                    f"measured_thresh={metadata['input_thresh']}"
                    f"[a{i}]"
                )
            temp_output = self.audio_processor._create_temp_file(input_path)
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", input_path, "-threads", "0",
                "-filter_complex", ";".join(filter_parts),
            ]
            if video_streams:
                ffmpeg_cmd.extend(["-map", "0:v"])
            for i, stream in enumerate(audio_streams):
                original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                new_title = self.audio_processor._update_track_title(original_title, "Normalized")
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
            with Live(console=console, refresh_per_second=8) as live:
                spinner = Spinner("dots", text=Text.from_markup(f"[bold bright_blue]Normalizing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"), style="blue")
                live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))
                process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                ffmpeg_log = []
                for line in process.stderr:
                    last_line = line.strip()
                    ffmpeg_log.append(last_line)
                    if last_line:
                        spinner.text = Text.from_markup(f"[bold bright_blue]Normalizing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]\n{last_line}")
                    else:
                        spinner.text = Text.from_markup(f"[bold bright_blue]Normalizing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]")
                    live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))
                process.wait()
                if process.returncode != 0:
                    self.logger.error(f"Normalization failed for {input_path}")
                    self.logger.error("FFmpeg stderr: " + "\n".join(ffmpeg_log))
                    spinner.text = Text.from_markup("[red]Normalization failed[/red]")
                    live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="red"))
                    return False
                spinner.text = Text.from_markup("[green]Finalizing...[/green]")
                live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="magenta"))

            final_path = input_path
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_output, final_path)
            if console:
                console.print("[green]Finalizing complete![/green]")
            return True

    def find_media_files(self, directory: str) -> List[str]:
        media_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    media_files.append(os.path.join(root, file))
        return media_files

    def process_files_with_progress(self, files: List[str], dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        from rich.text import Text
        from rich.console import Group
        from rich.panel import Panel
        from rich.table import Table
        valid_files = [f for f in files if TEMP_SUFFIX not in os.path.basename(f)]
        results = [{} for _ in valid_files]
        spinners = [Spinner("dots", text=Text.from_markup(f"[bold magenta]Waiting...[/bold magenta]"), style="green") for _ in valid_files]
        panels = [Panel(spinners[i], title=f"{os.path.basename(valid_files[i])}", border_style="bright_blue") for i in range(len(valid_files))]
        statuses = ["waiting" for _ in valid_files]
        def worker(idx, file, output_path):
            import subprocess, re, json
            audio_tracks = get_audio_track_count(file)
            analyzed_params = []
            def update_panel(stage, last_line=None, error=False, info_panel=None):
                text = ""
                if stage == "analyzing":
                    text = f"[bold bright_blue]Analyzing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"
                elif stage == "show_params":
                    text = f"[bold cyan]Analysis complete![/bold cyan]"
                elif stage == "normalizing":
                    text = "[bold bright_blue]Normalizing...[/bold bright_blue]"
                elif stage == "finalizing":
                    text = "[green]Finalizing...[/green]"
                if last_line:
                    text += f"\n{last_line}"
                content = [Text.from_markup(text)]
                if info_panel:
                    content.append(info_panel)
                panels[idx] = Panel(Group(*content), title=f"{os.path.basename(file)}", border_style="red" if error else ("magenta" if stage=="finalizing" else "blue"))
                spinners[idx].text = Text.from_markup(text)
            try:
                audio_streams = self.audio_processor._get_audio_streams(file)
                if not audio_streams:
                    update_panel("analyzing", last_line="No audio streams found", error=True)
                    try:
                        import subprocess
                        probe_cmd = ["ffprobe", "-v", "error", "-show_streams", "-select_streams", "a", "-print_format", "json", file]
                        proc = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                        self.logger.error(f"ffprobe stdout: {proc.stdout}")
                        self.logger.error(f"ffprobe stderr: {proc.stderr}")
                        try:
                            with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                                logf.write(f"\n[FFPROBE] {file}:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}\n")
                        except Exception:
                            pass
                    except Exception as e:
                        self.logger.error(f"Failed to run ffprobe for diagnostics: {e}")
                    statuses[idx] = "failed"
                    results[idx] = {"file": file, "task": "Normalize Audio", "status": "Failed"}
                    return
                video_streams = self.audio_processor._get_video_streams(file)
                loudness_data = []
                for i, stream in enumerate(audio_streams):
                    update_panel("analyzing", last_line=f"Stream {i+1}...")
                    analyze_cmd = [
                        "ffmpeg", "-i", file, "-threads", "0", "-map", f"0:a:{i}",
                        "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"
                    ]
                    process = subprocess.run(analyze_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                    try:
                        with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                            logf.write(f"\n[ANALYZE] {file} stream {i+1}:\n{process.stderr}\n")
                    except Exception as log_e:
                        self.logger.error(f"Failed to write to logs/ffmpeg_debug.log: {log_e}")
                        self.logger.error(f"FFmpeg stderr: {process.stderr}")
                    match = re.search(r'\{.*\}', process.stderr, re.DOTALL)
                    if not match:
                        update_panel("analyzing", last_line=f"Failed to get loudness data for stream {i+1}", error=True)
                        statuses[idx] = "failed"
                        results[idx] = {"file": file, "task": "Normalize Audio", "status": "Failed"}
                        return
                    data = json.loads(match.group())
                    loudness_data.append(data)
                table = Table(title="Loudness Analysis", show_header=True, header_style="bold magenta")
                table.add_column("Stream")
                table.add_column("I")
                table.add_column("TP")
                table.add_column("LRA")
                table.add_column("Thresh")
                for i, meta in enumerate(loudness_data):
                    table.add_row(str(i+1), str(meta.get("input_i","?")), str(meta.get("input_tp","?")), str(meta.get("input_lra","?")), str(meta.get("input_thresh","?")))
                update_panel("show_params", info_panel=table)
                filter_parts = []
                for i, metadata in enumerate(loudness_data):
                    filter_parts.append(
                        f"[0:a:{i}]loudnorm="
                        f"I=-16:TP=-1.5:LRA=11:"
                        f"measured_I={metadata['input_i']}:"
                        f"measured_TP={metadata['input_tp']}:"
                        f"measured_LRA={metadata['input_lra']}:"
                        f"measured_thresh={metadata['input_thresh']}:"
                        f"offset={metadata.get('target_offset', 0)}"
                        f"[a{i}]"
                    )
                temp_output = self.audio_processor._create_temp_file(file)
                self.logger.info(f"Audio streams: {audio_streams}")
                self.logger.info(f"Filter complex: {';'.join(filter_parts)}")
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", file, "-threads", "0",
                    "-filter_complex", ";".join(filter_parts),
                ]
                if video_streams:
                    ffmpeg_cmd.extend(["-map", "0:v"])
                for i, stream in enumerate(audio_streams):
                    original_title = stream.get('tags', {}).get('title', f'Track {i+1}')
                    new_title = self.audio_processor._update_track_title(original_title, "Normalized")
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
                update_panel("normalizing")
                process = subprocess.Popen(ffmpeg_cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                ffmpeg_log = []
                for line in process.stderr:
                    last_line = line.strip()
                    ffmpeg_log.append(last_line)
                    update_panel("normalizing", last_line=last_line)
                process.wait()
                try:
                    with open("logs/ffmpeg_debug.log", "a", encoding="utf-8") as logf:
                        logf.write(f"\n[NORMALIZE] {file}:\n" + "\n".join(ffmpeg_log) + "\n")
                except Exception as log_e:
                    self.logger.error(f"Failed to write to logs/ffmpeg_debug.log: {log_e}")
                    joined = "\n".join(ffmpeg_log)
                    self.logger.error(f"FFmpeg stderr: {joined}")
                if process.returncode != 0:
                    update_panel("normalizing", last_line="Normalization failed", error=True)
                    statuses[idx] = "failed"
                    results[idx] = {"file": file, "task": "Normalize Audio", "status": "Failed"}
                    return
                final_path = file
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(temp_output, final_path)
                try:
                    from .signal_handler import SignalHandler
                    SignalHandler.unregister_temp_file(temp_output)
                except Exception:
                    pass
                update_panel("finalizing")
                statuses[idx] = "done"
                results[idx] = {"file": file, "task": "Normalize Audio", "status": "Success"}
            except Exception as e:
                update_panel("normalizing", last_line=str(e), error=True)
                statuses[idx] = "failed"
                results[idx] = {"file": file, "task": "Normalize Audio", "status": "Failed"}
        threads = []
        from queue import Queue
        task_queue: Queue = Queue()
        for idx, file in enumerate(valid_files):
            task_queue.put((idx, file))
        from rich.console import Group
        def render_group():
            return Group(*(p for p in panels if p is not None))
        live_ref = {"live": None}
        num_workers = min(max_workers or self.max_workers, len(valid_files)) if valid_files else 0
        if num_workers <= 0:
            num_workers = 1
        def queue_worker():
            while True:
                try:
                    idx, file = task_queue.get(block=False)
                except Exception:
                    break
                output_path = file
                statuses[idx] = "in-progress"
                results[idx] = {"file": file, "task": "Normalize Audio", "status": "In Progress"}
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group())
                    except Exception:
                        pass
                worker(idx, file, output_path)
                task_queue.task_done()
        with Live(render_group(), refresh_per_second=8, console=self.console) as live:
            live_ref["live"] = live
            for _ in range(num_workers):
                t = threading.Thread(target=queue_worker)
                threads.append(t)
                t.start()
        def render_group():
            return Group(*(p for p in panels if p is not None))
        with Live(render_group(), refresh_per_second=8, console=self.console):
            import time
            while any(t.is_alive() for t in threads):
                time.sleep(0.1)
            while any(t.is_alive() for t in threads) or not task_queue.empty():
                time.sleep(0.1)
        for t in threads:
            t.join()
        return results

    def process_directory(self, directory: str, dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        safe_dir = directory.rstrip("/\\")
        self.logger.info(f"Scanning directory: {safe_dir}")
        media_files = self.find_media_files(directory)
        if not media_files:
            self.logger.warning("No supported media files found")
            return []
        self.logger.info(f"Found {len(media_files)} media files")
        return self.process_files_with_progress(media_files, dry_run=dry_run, max_workers=max_workers)
