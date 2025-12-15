"""
Batch processing module for audio normalization and boosting with progress UI.
"""
import os
import threading
import time
from typing import List, Dict, Any, Optional
from rich.console import Console, Group
from rich.text import Text
from .config import SUPPORTED_EXTENSIONS, TEMP_SUFFIX, AUDIO_CODEC, AUDIO_BITRATE
from .logger import Logger
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from .audio_processor import AudioProcessor
from queue import Queue


class BatchProcessor:
    def __init__(self, max_workers: Optional[int] = None):
        """Initialize BatchProcessor with logger and AudioProcessor."""
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
        
        
    def find_media_files(self, directory: str) -> List[str]:
        """Recursively find all supported media files in `directory`."""
        media_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    media_files.append(os.path.join(root, file))
        return media_files
    
    
    def process_directory(self, directory: str, dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """Normalize all supported media files in `directory` with a Rich UI."""
        safe_dir = directory.rstrip("/\\")
        self.logger.info(f"Scanning directory: {safe_dir}")
        media_files = self.find_media_files(directory)
        if not media_files:
            self.logger.warning("No supported media files found")
            return []
        self.logger.info(f"Found {len(media_files)} media files")
        return self.process_files_with_progress(media_files, dry_run=dry_run, max_workers=max_workers)
    
    
    def boost_files_with_progress(self, directory: str, boost_percent: float, dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """Boost audio volume for all supported media files in `directory` with a Rich UI."""
        files = self.find_media_files(directory)
        valid_files = [f for f in files if TEMP_SUFFIX not in os.path.basename(f)]
        results = [{"file": valid_files[i], "task": f"Boost {boost_percent}% Audio", "status": "Waiting"} for i in range(len(valid_files))]
        spinners = [Spinner("dots", text=Text.from_markup(f"[bold magenta]Waiting...[/bold magenta]"), style="green") for _ in valid_files]
        panels = [Panel(spinners[i], title=f"{os.path.basename(valid_files[i])}", border_style="green") for i in range(len(valid_files))]
        statuses = ["waiting" for _ in valid_files]

        def worker(idx, file, output_path):
            audio_streams = self.audio_processor._get_audio_streams(file)
            audio_tracks = len(audio_streams) if audio_streams is not None else 0
            statuses[idx] = "in-progress"
            results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "In Progress"}

            def update_panel(stage, last_line=None, error=False):
                if stage == "boosting":
                    text = f"[bold green]Boosting {audio_tracks} audio track{'s' if audio_tracks != 1 else ''} by {boost_percent}%...[/bold green]"
                    if last_line:
                        text += f"\n{last_line}"
                    spinners[idx].text = Text.from_markup(text)
                    panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file)}", border_style="red" if error else "green")
                    if live_ref.get("live"):
                        try:
                            live_ref["live"].update(render_group())
                        except Exception:
                            pass
                elif stage == "finalizing":
                    spinners[idx].text = Text.from_markup("[green]Finalizing...[/green]")
                    panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file)}", border_style="magenta")
                    if live_ref.get("live"):
                        try:
                            live_ref["live"].update(render_group())
                        except Exception:
                            pass
                elif stage == "success":
                    spinners[idx].text = Text.from_markup("[bold green]Boost complete[/bold green]")
                    panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file)}", border_style="green")
                    if live_ref.get("live"):
                        try:
                            live_ref["live"].update(render_group())
                        except Exception:
                            pass
            update_panel("boosting")
            try:
                if dry_run:
                    update_panel("boosting", last_line="(dry-run) Skipping execution", error=False)
                    statuses[idx] = "done"
                    results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Dry Run"}
                    update_panel("success")
                    return

                res = self.audio_processor.boost_audio(file, boost_percent, show_ui=False)
                if res:
                    update_panel("finalizing")
                    statuses[idx] = "done"
                    results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Success"}
                    self.logger.success(f"Boost complete: {file}")
                    update_panel("success")
                else:
                    update_panel("boosting", last_line="Boost failed", error=True)
                    statuses[idx] = "failed"
                    results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Failed"}
            except Exception as e:
                update_panel("boosting", last_line=str(e), error=True)
                statuses[idx] = "failed"
                results[idx] = {"file": file, "task": f"Boost {boost_percent}% Audio", "status": "Failed"}
            time.sleep(0.2)

        threads = []

        task_queue: Queue = Queue()
        for idx, file in enumerate(valid_files):
            task_queue.put((idx, file))
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
            while any(t.is_alive() for t in threads) or not task_queue.empty():
                time.sleep(0.1)
        for t in threads:
            t.join()
        return results
    

    def process_single_file_with_progress(self, file: str, dry_run: bool = False) -> Dict[str, Any]:
        """Normalize a single file with a Rich UI."""
        try:
            if dry_run:
                self.logger.info(f"Dry run: would normalize {file}")
                return {"file": file, "task": "Normalize Audio", "status": "Dry Run"}
            success = self._normalize_with_rich_ui(file, file, self.console)
            return {"file": file, "task": "Normalize Audio", "status": "Success" if success else "Failed"}
        except Exception as e:
            self.logger.error(f"Normalization error for {file}: {e}")
            return {"file": file, "task": "Normalize Audio", "status": "Failed"}

    def _normalize_with_rich_ui(self, input_path: str, output_path: str, console: Optional[Console] = None, update_panel=None) -> bool:
        """Normalize audio with a Rich progress UI."""

        audio_streams = self.audio_processor._get_audio_streams(input_path)
        audio_tracks = len(audio_streams) if audio_streams is not None else 0

        if update_panel:
            update_panel("analyzing")
            try:
                res = self.audio_processor.normalize_audio(input_path, show_ui=False, progress_callback=update_panel)
                if res:
                    update_panel("finalizing")
                    time.sleep(0.2)
                    return True
                else:
                    update_panel("normalizing", last_line="Normalization failed", error=True)
                    return False
            except Exception as e:
                update_panel("normalizing", last_line=str(e), error=True)
                return False
        else:
            with Live(console=console, refresh_per_second=8) as live:
                spinner = Spinner("dots", text=Text.from_markup(f"[bold bright_blue]Analyzing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"), style="blue")
                live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))

                def progress_cb(stage, last_line=None, error=False):
                    if stage == "analyzing":
                        text = f"[bold bright_blue]Analyzing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"
                        if last_line:
                            text += f"\n{last_line}"
                        spinner.text = Text.from_markup(text)
                        live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))
                    elif stage == "show_params":
                        spinner.text = Text.from_markup("[bold cyan]Analysis complete![/bold cyan]")
                        live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="cyan"))
                    elif stage == "normalizing":
                        text = "[bold bright_blue]Normalizing...[/bold bright_blue]"
                        if last_line:
                            text += f"\n{last_line}"
                        spinner.text = Text.from_markup(text)
                        live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))
                    elif stage == "finalizing":
                        spinner.text = Text.from_markup("[green]Finalizing...[/green]")
                        live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="magenta"))
                    else:
                        text = f"[bold bright_blue]Normalizing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"
                        if last_line:
                            text += f"\n{last_line}"
                        spinner.text = Text.from_markup(text)
                        live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="bright_blue"))
                try:
                    res = self.audio_processor.normalize_audio(input_path, show_ui=False, progress_callback=progress_cb)
                except Exception as e:
                    self.logger.error(f"Normalization error: {e}")
                    res = None
                if not res:
                    spinner.text = Text.from_markup("[red]Normalization failed[/red]")
                    live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="red"))
                    return False
                spinner.text = Text.from_markup("[green]Finalizing...[/green]")
                live.update(Panel(spinner, title=f"{os.path.basename(input_path)}", border_style="magenta"))
                time.sleep(0.2)
                return True


    def process_files_with_progress(self, files: List[str], dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """Normalize a list of files with a Rich UI."""
        valid_files = [f for f in files if TEMP_SUFFIX not in os.path.basename(f)]
        results = [{} for _ in valid_files]
        spinners = [Spinner("dots", text=Text.from_markup(f"[bold magenta]Waiting...[/bold magenta]"), style="green") for _ in valid_files]
        panels = [Panel(spinners[i], title=f"{os.path.basename(valid_files[i])}", border_style="bright_blue") for i in range(len(valid_files))]
        statuses = ["waiting" for _ in valid_files]
        
        def worker(idx, file, output_path):
            """Worker for normalizing a single file -- delegate to AudioProcessor."""
            audio_streams = self.audio_processor._get_audio_streams(file)
            audio_tracks = len(audio_streams) if audio_streams is not None else 0
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
                update_panel("analyzing")
                if dry_run:
                    update_panel("analyzing", last_line="(dry-run) Skipping execution")
                    statuses[idx] = "done"
                    results[idx] = {"file": file, "task": "Normalize Audio", "status": "Dry Run"}
                    return

                res = self.audio_processor.normalize_audio(file)
                if res:
                    update_panel("finalizing")
                    statuses[idx] = "done"
                    results[idx] = {"file": file, "task": "Normalize Audio", "status": "Success"}
                else:
                    update_panel("normalizing", last_line="Normalization failed", error=True)
                    statuses[idx] = "failed"
                    results[idx] = {"file": file, "task": "Normalize Audio", "status": "Failed"}
            except Exception as e:
                update_panel("normalizing", last_line=str(e), error=True)
                statuses[idx] = "failed"
                results[idx] = {"file": file, "task": "Normalize Audio", "status": "Failed"}
        threads = []
        task_queue: Queue = Queue()
        for idx, file in enumerate(valid_files):
            task_queue.put((idx, file))
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
            while any(t.is_alive() for t in threads):
                time.sleep(0.1)
            while any(t.is_alive() for t in threads) or not task_queue.empty():
                time.sleep(0.1)
        for t in threads:
            t.join()
        return results
