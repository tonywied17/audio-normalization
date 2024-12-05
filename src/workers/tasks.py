import os
import concurrent.futures
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.processing.audio import AudioProcessor
from src.workers.worker import worker_pool
from src.util.logger import Logger


class TaskProcessor:
    def __init__(self, log_file="process.log"):
        self.logger = Logger(log_file=log_file)
        self.console = Console()
        self.progress = Progress(SpinnerColumn(), TextColumn("{task.description}"), console=self.console)
        self.queue = []
        self.audio_processor = AudioProcessor(log_file=log_file)

    def log_and_update_ui(self, task_desc, media_path, live=None):
        """Logs the task and updates the live table."""
        self.logger.info(f"Assigned task to worker.\n\n[bold]Task:[/bold] {task_desc}\n[bold]File:[/bold] {media_path}")
        if live:
            live.update(worker_pool.update_worker_table(self.queue))

    def process_queue(self, live=None):
        """Assign tasks from the queue to idle workers."""
        for worker in worker_pool.workers:
            if not worker.is_busy and self.queue:
                task_description, file_path = self.queue.pop(0)
                worker.assign_task(task_description, file_path)
                self.log_and_update_ui(task_description, file_path, live)
                break

    def process_directory(self, directory, temp_files=None):
        """Process all files in a directory recursively."""
        if temp_files is None:
            temp_files = []

        with self.progress:
            task_id = self.progress.add_task("Scanning for media files...", start=False)
            media_files = []

            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac')):
                        media_files.append(os.path.join(root, file))
                self.progress.advance(task_id)

            self.progress.update(task_id, total=len(media_files), completed=len(media_files), visible=False)

        if not media_files:
            self.logger.error("No media files found in the specified directory or its subdirectories.")
            return

        with Live(worker_pool.update_worker_table(self.queue), refresh_per_second=1, console=self.console) as live:
            for media_path in media_files:
                worker_assigned = False
                for worker in worker_pool.workers:
                    if worker.assign_task("Normalize Audio", media_path):
                        worker_assigned = True
                        self.log_and_update_ui("Normalize Audio", media_path, live)
                        break

                if not worker_assigned:
                    self.queue.append(("Normalize Audio", media_path))
                    self.log_and_update_ui("Normalize Audio", media_path, live)

                live.update(worker_pool.update_worker_table(self.queue))

            results = []
            task = self.progress.add_task("[cyan]Normalizing Audio...", total=len(media_files))

            with concurrent.futures.ProcessPoolExecutor(max_workers=worker_pool.max_workers) as executor:
                futures = [
                    executor.submit(self.process_file, 1, media_path, None, temp_files, False)
                    for media_path in media_files
                ]

                while futures:
                    for future in concurrent.futures.as_completed(futures):
                        task_desc, media_path, success = future.result()

                        for worker in worker_pool.workers:
                            if worker.is_busy and worker.file_path == media_path:
                                worker.complete_task(self.process_queue, live)

                        results.append({
                            "file": media_path,
                            "task": task_desc,
                            "status": "Success" if success else "Failed"
                        })

                        self.progress.advance(task)
                        live.update(worker_pool.update_worker_table(self.queue))

                    futures = [f for f in futures if not f.done()]

            self.progress.stop()

            if all(not worker.is_busy for worker in worker_pool.workers):
                worker_pool.print_summary_table(results)

    def process_file(self, option, media_path, volume_boost_percentage=None, temp_files=None, is_single_file=True):
        """Processes a single file."""
        task_description = "Normalize Audio" if option == 1 else f"Boost {volume_boost_percentage}% Audio"
        success = False

        if is_single_file:
            worker_assigned = False
            for worker in worker_pool.workers:
                if worker.assign_task(task_description, media_path):
                    worker_assigned = True
                    self.log_and_update_ui(task_description, media_path, live=None)
                    break

            if not worker_assigned:
                self.queue.append((task_description, media_path))
                self.log_and_update_ui(task_description, media_path, live=None)

            if option == 1:
                result = self.audio_processor.normalize_audio(media_path, temp_files)
                success = result is not None
            elif option == 3 and volume_boost_percentage is not None:
                result = self.audio_processor.filter_audio(media_path, volume_boost_percentage, temp_files)
                success = result is not None

            for worker in worker_pool.workers:
                if worker.is_busy and worker.file_path == media_path:
                    worker.complete_task(self.process_queue, live=None)

        else:
            if option == 1:
                result = self.audio_processor.normalize_audio(media_path, temp_files)
                success = result is not None

            for worker in worker_pool.workers:
                if worker.is_busy and worker.file_path == media_path:
                    worker.complete_task(self.process_queue, live=None)

        status_message = "Success" if success else "Failed"

        if is_single_file and all(not worker.is_busy for worker in worker_pool.workers):
            worker_pool.print_summary_table([{
                "file": media_path,
                "task": task_description,
                "status": status_message
            }])

        return task_description, media_path, success
