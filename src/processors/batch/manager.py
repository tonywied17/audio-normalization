"""Batch manager containing `BatchProcessor` class; delegates utilities to submodules."""
import os
import threading
import time
from typing import List, Dict, Any, Optional
from rich.console import Console, Group
from rich.text import Text
from core.config import SUPPORTED_EXTENSIONS, TEMP_SUFFIX
from .utils import find_media_files
from core.logger import Logger
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from processors.audio import AudioProcessor
from queue import Queue
from . import worker as bp_worker
from . import ui as bp_ui


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

    def process_directory(self, directory: str, dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """Normalize all supported media files in `directory` with a Rich UI."""
        safe_dir = directory.rstrip("/\\")
        self.logger.info(f"Scanning directory: {safe_dir}")
        media_files = find_media_files(directory, SUPPORTED_EXTENSIONS)
        if not media_files:
            self.logger.warning("No supported media files found")
            return []
        self.logger.info(f"Found {len(media_files)} media files")
        return self.process_files_with_progress(media_files, dry_run=dry_run, max_workers=max_workers)

    def process_files_with_progress(self, files: List[str], dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process a list of files with a simple threaded pool and Rich Live UI.

        This provides a lightweight progress display and returns a list of results
        with keys: `file`, `task`, `status`, and optionally `message`.
        """
        worker_count = max_workers or self.max_workers
        try:
            worker_count = int(worker_count) if worker_count else 1
        except Exception:
            worker_count = 1

        results: List[Dict[str, Any]] = []
        results_lock = threading.Lock()

        # Prepare UI slots equal to worker_count
        panels = [None] * worker_count
        spinners = [Spinner("dots", "pending") for _ in range(worker_count)]
        live_ref = {"live": None}

        # Pool of available slot indices
        slot_queue: Queue = Queue()
        for i in range(worker_count):
            slot_queue.put(i)

        sem = threading.Semaphore(worker_count)

        def run_task(file_path: str):
            sem.acquire()
            idx = None
            try:
                idx = slot_queue.get()
                # initialize panel for this slot
                spinners[idx] = Spinner("dots", "Preparing...")
                panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file_path)}")
                # probe audio streams to display correct track count in UI
                try:
                    audio_streams = self.audio_processor._get_audio_streams(file_path) or []
                except Exception:
                    audio_streams = []
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(bp_ui.render_group(panels))
                    except Exception:
                        pass

                update_cb = bp_ui.make_update_panel(idx, spinners, panels, live_ref, os.path.basename(file_path), audio_tracks=len(audio_streams))
                res = bp_worker.normalize_file(self.audio_processor, file_path, dry_run=dry_run, progress_callback=update_cb, show_ui=False)
                result_entry = {
                    "file": file_path,
                    "task": "normalize",
                    "status": "Success" if res.get("success") else "Failed",
                }
                if "message" in res:
                    result_entry["message"] = res.get("message")
                with results_lock:
                    results.append(result_entry)
            finally:
                if idx is not None:
                    slot_queue.put(idx)
                sem.release()

        threads: List[threading.Thread] = []

        with Live(bp_ui.render_group(panels), refresh_per_second=10) as live:
            live_ref["live"] = live
            # start threads for each file, but limit concurrency via semaphore
            for f in files:
                t = threading.Thread(target=run_task, args=(f,))
                t.daemon = True
                t.start()
                threads.append(t)

            # wait for all threads to finish
            for t in threads:
                t.join()

        return results

    def process_single_file_with_progress(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Process a single file and return a single result dict for compatibility with CLI handlers."""
        res_list = self.process_files_with_progress([file_path], dry_run=dry_run, max_workers=1)
        if res_list:
            return res_list[0]
        return {"file": file_path, "task": "normalize", "status": "Failed", "message": "No result"}

    def boost_files_with_progress(self, directory: str, boost_percent: float, dry_run: bool = False, max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
        """Boost all supported media files in `directory` using threaded workers and Rich UI."""
        safe_dir = directory.rstrip("/\\")
        self.logger.info(f"Scanning directory for boost: {safe_dir}")
        media_files = find_media_files(directory, SUPPORTED_EXTENSIONS)
        if not media_files:
            self.logger.warning("No supported media files found for boost")
            return []
        self.logger.info(f"Found {len(media_files)} media files for boost")

        worker_count = max_workers or self.max_workers
        try:
            worker_count = int(worker_count) if worker_count else 1
        except Exception:
            worker_count = 1

        results: List[Dict[str, Any]] = []
        results_lock = threading.Lock()

        panels = [None] * worker_count
        spinners = [Spinner("dots", "pending") for _ in range(worker_count)]
        live_ref = {"live": None}

        slot_queue: Queue = Queue()
        for i in range(worker_count):
            slot_queue.put(i)

        sem = threading.Semaphore(worker_count)

        def run_boost(file_path: str):
            sem.acquire()
            idx = None
            try:
                idx = slot_queue.get()
                spinners[idx] = Spinner("dots", "Preparing...")
                panels[idx] = Panel(spinners[idx], title=f"{os.path.basename(file_path)}")
                try:
                    audio_streams = self.audio_processor._get_audio_streams(file_path) or []
                except Exception:
                    audio_streams = []
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(bp_ui.render_group(panels))
                    except Exception:
                        pass

                update_cb = bp_ui.make_update_panel(idx, spinners, panels, live_ref, os.path.basename(file_path), boost_percent=boost_percent, audio_tracks=len(audio_streams))
                try:
                    update_cb("boosting", last_line=None)
                except Exception:
                    pass
                res = bp_worker.boost_file(self.audio_processor, file_path, boost_percent, dry_run=dry_run, show_ui=False)
                try:
                    if res.get("success"):
                        update_cb("success")
                    else:
                        update_cb("finalizing", last_line=res.get("message", ""), error=True)
                except Exception:
                    pass
                result_entry = {
                    "file": file_path,
                    "task": f"Boost {boost_percent}% Audio",
                    "status": "Success" if res.get("success") else "Failed",
                }
                if "message" in res:
                    result_entry["message"] = res.get("message")
                with results_lock:
                    results.append(result_entry)
            finally:
                if idx is not None:
                    slot_queue.put(idx)
                sem.release()

        threads: List[threading.Thread] = []

        with Live(bp_ui.render_group(panels), refresh_per_second=10) as live:
            live_ref["live"] = live
            for f in media_files:
                t = threading.Thread(target=run_boost, args=(f,))
                t.daemon = True
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        return results
