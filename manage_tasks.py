import os
import concurrent.futures
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from audio_processing import normalize_audio, filter_audio
from worker import workers, max_workers, update_worker_table, print_summary_table

queue = []
console = Console()
progress = Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console)


def process_queue():
    """Assign tasks from the queue to idle workers."""
    for worker in workers:
        if not worker.is_busy and queue:
            task_description, file_path = queue.pop(0)
            worker.assign_task(task_description, file_path)
            break
    

def process_directory(directory, log_file_path="process.log", temp_files=None):
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
        console.print("[orange_red1]No video files found in the specified directory or its subdirectories.[/orange_red1]")
        return

    for video_path in video_files:
        worker_assigned = False
        for worker in workers:
            if worker.assign_task("Normalize Audio", video_path):
                worker_assigned = True
                break

        if not worker_assigned:
            queue.append(("Normalize Audio", video_path))

    results = []
    task = progress.add_task("[cyan]Normalizing Audio...", total=len(video_files))

    with Live(update_worker_table(workers, queue), refresh_per_second=2, console=console) as live:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_file, 1, video_path, log_file_path, temp_files, is_single_file=False)
                for video_path in video_files
            ]

            while futures:
                for future in concurrent.futures.as_completed(futures):
                    task_desc, video_path, success = future.result()

                    for worker in workers:
                        if worker.is_busy and worker.file_path == video_path:
                            worker.complete_task(process_queue)

                    process_queue() 

                    results.append({
                        "file": video_path,
                        "task": task_desc,
                        "status": "Success" if success else "Failed"
                    })

                    progress.advance(task)

                    live.update(update_worker_table(workers, queue))

                futures = [f for f in futures if not f.done()]

    progress.stop()

    print_summary_table(results)


def process_file(option, video_path, volume_boost_percentage=None, log_file_path="process.log", temp_files=None, is_single_file=True):
    """
    Process a single video file: either normalize or apply a volume boost.
    """
    if temp_files is None:
        temp_files = []

    task_description = "Normalize Audio" if option == 1 else f"Boost {volume_boost_percentage}% Audio"
    temp_file = f"{os.path.splitext(video_path)[0]}_TEMP.mkv"
    temp_files.append(temp_file)

    success = False

    queue.append((task_description, video_path))

    process_queue()

    if is_single_file:
        with Live(update_worker_table(workers, queue), refresh_per_second=2, console=console) as live:
            if option == 1:
                result = normalize_audio(video_path, log_file_path, temp_files)
                success = result is not None

            elif option == 3 and volume_boost_percentage is not None:
                result = filter_audio(video_path, volume_boost_percentage, log_file_path, temp_files)
                success = result is not None

            for worker in workers:
                if worker.is_busy and worker.file_path == video_path:
                    worker.complete_task(process_queue)

            process_queue()

            live.update(update_worker_table(workers, queue))
    else:
        if option == 1:
            result = normalize_audio(video_path, log_file_path, temp_files)
            success = result is not None

        elif option == 3 and volume_boost_percentage is not None:
            result = filter_audio(video_path, volume_boost_percentage, log_file_path, temp_files)
            success = result is not None

        for worker in workers:
            if worker.is_busy and worker.file_path == video_path:
                worker.complete_task(process_queue) 

        process_queue()

    print_summary_table([{
        "file": video_path,
        "task": task_description,
        "status": "Success" if success else "Failed"
    }])

    return task_description, video_path, success
