import os
import concurrent.futures
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from src.processing.audio import AudioProcessor
from src.workers.worker import workers, max_workers, update_worker_table, print_summary_table
from src.util.logger import Logger

console = Console()
logger = Logger(log_file="process.log")
queue = []

progress = Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TextColumn("[progress.time]{task.completed}/{task.total}"),
    console=console
)

def log_and_update_ui(task_desc, media_path, live=None):
    """Logs the task and updates the live table."""
    logger.info(f"Assigned task to worker.\n\n[bold]Task:[/bold] {task_desc}\n[bold]File:[/bold] {media_path}")
    if live:
        live.update(update_worker_table(workers, queue))


#! -- Process Queue -- 
def process_queue(live=None):
    """Assign tasks from the queue to idle workers."""
    for worker in workers:
        if not worker.is_busy and queue:
            task_description, file_path = queue.pop(0)
            worker.assign_task(task_description, file_path)
            log_and_update_ui(task_description, file_path, live)
            break


#! -- Process Directory -- 
def process_directory(directory, temp_files=None):
    """Process all files in a directory recursively."""
    if temp_files is None:
        temp_files = []

    with progress:
        task_id = progress.add_task("[cyan]Scanning directory...", total=1)
        media_files = []

        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg', '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.aac')): 
                    media_files.append(os.path.join(root, file))
            progress.advance(task_id)

        progress.update(task_id, total=len(media_files), completed=len(media_files), visible=False)

    if not media_files:
        logger.error("No media files found in the specified directory or its subdirectories.")
        return

    with Live(update_worker_table(workers, queue), refresh_per_second=1, console=console) as live:
        for media_path in media_files:
            worker_assigned = False
            for worker in workers:
                if worker.assign_task("Normalize Audio", media_path):
                    worker_assigned = True
                    log_and_update_ui("Normalize Audio", media_path, live)
                    break

            if not worker_assigned:
                queue.append(("Normalize Audio", media_path))
                log_and_update_ui("Normalize Audio", media_path, live)
                
            live.update(update_worker_table(workers, queue))

        results = []
        task = progress.add_task("[cyan]Normalizing Audio...", total=len(media_files))

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_file, 1, media_path, None, temp_files, is_single_file=False)
                for media_path in media_files
            ]

            while futures:
                for future in concurrent.futures.as_completed(futures):
                    task_desc, media_path, success = future.result()

                    for worker in workers:
                        if worker.is_busy and worker.file_path == media_path:
                            worker.complete_task(process_queue, live)

                    results.append({
                        "file": media_path,
                        "task": task_desc,
                        "status": "Success" if success else "Failed"
                    })

                    progress.advance(task)
                    live.update(update_worker_table(workers, queue))

                futures = [f for f in futures if not f.done()]

        progress.stop()

        if all(not worker.is_busy for worker in workers):
            print_summary_table(results)


#! -- Process File -- 
def process_file(option, media_path, volume_boost_percentage=None, temp_files=None, is_single_file=True):
    
    task_description = "Normalize Audio" if option == 1 else f"Boost {volume_boost_percentage}% Audio"
    success = False
    audio_processor = AudioProcessor(temp_files=temp_files)
    
    if is_single_file:
        worker_assigned = False
        for worker in workers:
            if worker.assign_task(task_description, media_path):
                worker_assigned = True
                log_and_update_ui(task_description, media_path, live=None)
                break

        if not worker_assigned:
            queue.append((task_description, media_path))
            log_and_update_ui(task_description, media_path, live=None)

        if option == 1:
            success = audio_processor.normalize_audio(media_path) is not None
        elif option == 3 and volume_boost_percentage is not None:
            success = audio_processor.filter_audio(media_path, volume_boost_percentage) is not None

        for worker in workers:
            if worker.is_busy and worker.file_path == media_path:
                worker.complete_task(process_queue, live=None)

    else:
        if option == 1:
            success = audio_processor.normalize_audio(media_path) is not None

        for worker in workers:
            if worker.is_busy and worker.file_path == media_path:
                worker.complete_task(process_queue, live=None)

    status_message = "Success" if success else "Failed"

    if is_single_file and all(not worker.is_busy for worker in workers):
        print_summary_table([{
            "file": media_path,
            "task": task_description,
            "status": status_message
        }])

    return task_description, media_path, success
