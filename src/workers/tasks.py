import os
import concurrent.futures
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from src.processing.audio import AudioProcessor
from src.workers.worker import workers, max_workers, update_worker_table, print_summary_table
from src.util.logger import Logger


def standalone_process_file(option, media_path, volume_boost_percentage=None, temp_files=None):
    """Standalone function to process a file, compatible with multiprocessing.

    Args:
        option (int): The processing option.
        media_path (str): Path to the media file.
        volume_boost_percentage (int, optional): The volume boost percentage. Defaults to None.
        temp_files (list, optional): List of temporary files. Defaults to None.

    Returns:
        _type_: _description_
    """
    task_description = "Normalize Audio" if option == 1 else f"Boost {volume_boost_percentage}% Audio"
    success = False
    audio_processor = AudioProcessor(temp_files=temp_files)

    if option == 1:
        success = audio_processor.normalize_audio(media_path) is not None
    elif option == 3 and volume_boost_percentage is not None:
        success = audio_processor.filter_audio(media_path, volume_boost_percentage) is not None

    return task_description, media_path, success


class TaskProcessor:
    """Class to process tasks."""
    def __init__(self, log_file="process.log"):
        self.console = Console()
        self.logger = Logger(log_file=log_file)
        self.queue = []
        self.results = []

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("[progress.time]{task.completed}/{task.total}"),
            console=self.console
        )

    def log_and_update_ui(self, task_desc, media_path, live=None):
        """Log the task and update the UI.

        Args:
            task_desc (str): The task description.
            media_path (str): Path to the media file.
            live (Live, optional): The Live object. Defaults to None.
        """
        self.logger.info(f"Assigned task to worker.\n\n[bold]Task:[/bold] {task_desc}\n[bold]File:[/bold] {media_path}")
        if live:
            live.update(update_worker_table(workers, self.queue))
        else:
            self.console.print(update_worker_table(workers, self.queue))

    def process_directory(self, directory, temp_files=None):
        """Process all media files in the specified directory.

        Args:
            directory (str): Path to the directory.
            temp_files (list, optional): List of temporary files. Defaults to None.
        """
        if temp_files is None:
            temp_files = []

        with self.progress:
            task_id = self.progress.add_task("[cyan]Scanning directory...", total=1)
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

        with Live(update_worker_table(workers, self.queue), refresh_per_second=1, console=self.console) as live:
            for media_path in media_files:
                worker_assigned = False
                for worker in workers:
                    if worker.assign_task("Normalize Audio", media_path):
                        worker_assigned = True
                        self.log_and_update_ui("Normalize Audio", media_path, live)
                        break

                if not worker_assigned:
                    self.queue.append(("Normalize Audio", media_path))
                    self.log_and_update_ui("Normalize Audio", media_path, live)

                live.update(update_worker_table(workers, self.queue))

            task = self.progress.add_task("[cyan]Normalizing Audio...", total=len(media_files))

            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(standalone_process_file, 1, media_path, None, temp_files)
                    for media_path in media_files
                ]

                while futures:
                    for future in concurrent.futures.as_completed(futures):
                        task_desc, media_path, success = future.result()

                        for worker in workers:
                            if worker.is_busy and worker.file_path == media_path:
                                worker.complete_task(self.process_queue, live)

                        self.results.append({
                            "file": media_path,
                            "task": task_desc,
                            "status": "Success" if success else "Failed"
                        })

                        self.progress.advance(task)
                        live.update(update_worker_table(workers, self.queue))

                    futures = [f for f in futures if not f.done()]

            self.progress.stop()

            if all(not worker.is_busy for worker in workers):
                self.console.print(print_summary_table(self.results))
