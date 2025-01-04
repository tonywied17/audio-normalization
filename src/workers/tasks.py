import os
import concurrent.futures
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table
from rich import box
from src.processing.audio import AudioProcessor
from src.workers.worker import workers, max_workers, print_summary_table
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


    def display_and_update_worker_table(self, live=None):
        """Display and update the worker table.

        Args:
            live (Live, optional): The Live object. Defaults to None.
        """
    
        table = Table(title="🎯 Worker Status", title_style="bold green",
                    show_header=True, header_style="bold magenta", box=box.SIMPLE,
                    show_footer=False, expand=True, show_lines=True, style="cyan")
        table.add_column("Worker ID", justify="center", style="bold cyan", width=5)
        table.add_column("Task", justify="left", style="italic magenta", width=20)
        table.add_column("File Path", justify="left", style="dim cyan", width=40)
        table.add_column("Status", justify="center", style="bold green", width=20)

        #* Active workers
        for worker in workers:
            table.add_row(
                str(worker.worker_id), 
                worker.task_description or "[italic grey]Idle[/italic grey]",
                worker.file_path or "[italic grey]None[/italic grey]",
                f"[green]{worker.status}[/green]" if worker.is_busy else "[bold grey]Idle[/bold grey]",
                
            )

        #* Queue
        for idx, (task, file_path) in enumerate(self.queue, start=1):
            table.add_row(
                f"Queue-{idx}", 
                task, 
                file_path, 
                "Waiting for Worker",
            )

        if live:
            live.update(table)
        else:
            self.console.print(table)


    def process_queue(self, live=None):
        """Process the queue.

        Args:
            live (Live, optional): The Live object. Defaults to None.
        """
        for worker in workers:
            if not worker.is_busy and self.queue:
                task_description, file_path = self.queue.pop(0)
                worker.assign_task(task_description, file_path)
                self.display_and_update_worker_table(live)
                break


    def process_directory(self, directory, temp_files=None):
        """Process all media files in the specified directory.

        Args:
            directory (str): Path to the directory.
            temp_files (list, optional): List of temporary files. Defaults to None.
        """
        if temp_files is None:
            temp_files = []

        #@ Step 1: Scan directory for media files
        with self.progress:
            task_id = self.progress.add_task("[cyan]Scanning directory...", total=1)
            media_files = []

            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v',
                                            '.mpg', '.mpeg', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac')):
                        media_files.append(os.path.join(root, file))
                self.progress.advance(task_id)

            self.progress.update(task_id, total=len(media_files), completed=len(media_files), visible=False)

        if not media_files:
            self.logger.error("No media files found in the specified directory or its subdirectories.")
            return

        #@ Step 2: Display and update worker table using Live
        with Live(Table(title="🎯 Worker Status"), refresh_per_second=2, console=self.console) as live:
            self.display_and_update_worker_table(live)

            for media_path in media_files:
                worker_assigned = False

                #* Assign tasks to idle workers
                for worker in workers:
                    if not worker.is_busy:
                        worker.assign_task("Normalize Audio", media_path)
                        worker_assigned = True
                        self.display_and_update_worker_table(live)
                        break

                #* Append to queue if no idle workers are available
                if not worker_assigned:
                    self.logger.info(f"Adding task to queue: Normalize Audio, File: {media_path}")
                    self.queue.append(("Normalize Audio", media_path))
                    self.display_and_update_worker_table(live)

                self.process_queue(live)

            #@ Step 3: Process files using a thread pool
            task = self.progress.add_task("[cyan]Processing Media Files...", total=len(media_files))

            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(standalone_process_file, 1, media_path, None, temp_files)
                    for media_path in media_files
                ]

                while futures:
                    for future in concurrent.futures.as_completed(futures):
                        task_desc, media_path, success = future.result()

                        #* Mark worker as complete
                        for worker in workers:
                            if worker.is_busy and worker.file_path == media_path:
                                worker.complete_task(self, live)

                        #* Store in results
                        self.results.append({
                            "file": media_path,
                            "task": task_desc,
                            "status": "Success" if success else "Failed"
                        })

                        self.progress.advance(task)
                        self.process_queue(live) 

                    #* Update futures to exclude completed ones
                    futures = [f for f in futures if not f.done()]

            self.progress.stop()

            #! Print summary table after all tasks are completed
            if all(not worker.is_busy for worker in workers):
                self.console.print(print_summary_table(self.results))