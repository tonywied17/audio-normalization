import os
import concurrent.futures
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.audio_processing import normalize_audio, filter_audio
from src.worker import workers, max_workers, update_worker_table, print_summary_table
from src.logger import Logger

logger = Logger(log_file="process.log")
console = Console()
progress = Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console)
queue = []


def log_and_update_ui(task_desc, video_path, live):
    """Logs the task and updates the live table."""
    logger.info(f"Assigned task: {task_desc} to worker for file: {video_path}")
    live.update(update_worker_table(workers, queue))


#! -- Process Queue --
def process_queue():
    """Assign tasks from the queue to idle workers."""
    for worker in workers:
        if not worker.is_busy and queue:
            task_description, file_path = queue.pop(0)
            worker.assign_task(task_description, file_path)
            log_and_update_ui(task_description, file_path, live)
            break


#! -- Process Directory --
def process_directory(directory, temp_files=None):
    """Process all video files in a directory recursively."""
    if temp_files is None:
        temp_files = []

    with progress:
        task_id = progress.add_task("Scanning for video files...", start=False)
        video_files = []

        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.mp4', '.mkv', '.avi')):
                    video_files.append(os.path.join(root, file))
            progress.advance(task_id)

        progress.update(task_id, total=len(video_files), completed=len(video_files), visible=False)

    if not video_files:
        logger.error("No video files found in the specified directory or its subdirectories.")
        return

    with Live(update_worker_table(workers, queue), refresh_per_second=1, console=console) as live:
        for video_path in video_files:
            worker_assigned = False
            for worker in workers:
                if worker.assign_task("Normalize Audio", video_path):
                    worker_assigned = True
                    log_and_update_ui("Normalize Audio", video_path, live)
                    break

            if not worker_assigned:
                queue.append(("Normalize Audio", video_path))
                log_and_update_ui("Normalize Audio", video_path, live)

        results = []
        task = progress.add_task("[cyan]Normalizing Audio...", total=len(video_files))

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_file, 1, video_path, None, temp_files, is_single_file=False)
                for video_path in video_files
            ]

            while futures:
                for future in concurrent.futures.as_completed(futures):
                    task_desc, video_path, success = future.result()

                    for worker in workers:
                        if worker.is_busy and worker.file_path == video_path:
                            worker.complete_task(process_queue)

                    results.append({
                        "file": video_path,
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
def process_file(option, video_path, volume_boost_percentage=None, temp_files=None, is_single_file=True):
    """
    Process a single video file: either normalize or apply a volume boost.
    """
    if temp_files is None:
        temp_files = []

    task_description = "Normalize Audio" if option == 1 else f"Boost {volume_boost_percentage}% Audio"
    success = False

    logger.info(f"Starting task: {task_description} for file: {video_path}")

    if is_single_file:
        with Live(update_worker_table(workers, queue), refresh_per_second=2, console=console) as live:
            if option == 1:
                result = normalize_audio(video_path, temp_files)
                success = result is not None

            elif option == 3 and volume_boost_percentage is not None:
                result = filter_audio(video_path, volume_boost_percentage, temp_files)
                success = result is not None
                
            process_queue()
            log_and_update_ui(task_description, video_path, live)
            for worker in workers:
                if worker.is_busy and worker.file_path == video_path:
                    worker.complete_task(process_queue)
            log_and_update_ui(task_description, video_path, live)

    else:
        # Handle batch processing (directory-wide tasks) without live updates
        if option == 1:
            result = normalize_audio(video_path, temp_files)
            success = result is not None

        for worker in workers:
            if worker.is_busy and worker.file_path == video_path:
                worker.complete_task(process_queue)

    status_message = "Success" if success else "Failed"
    logger.success(f"Task {task_description} completed with status: {status_message} for file: {video_path}") if success else logger.error(
        f"Task {task_description} failed for file: {video_path}")

    if is_single_file and all(not worker.is_busy for worker in workers):
        print_summary_table([{
            "file": video_path,
            "task": task_description,
            "status": status_message
        }])

    return task_description, video_path, success
