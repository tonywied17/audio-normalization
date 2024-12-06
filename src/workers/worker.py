from rich.console import Console
from rich.table import Table
from rich import box
from src.util.values import CoreCount
from src.util.logger import Logger

console = Console()
logger = Logger(log_file="process.log")

class Worker:
    def __init__(self, worker_id, max_workers):
        """Initialize the Worker instance.

        Args:
            worker_id (int): Worker ID.
            max_workers (int): Maximum number of workers.
        """
        self.worker_id = worker_id
        self.max_workers = max_workers
        self.is_busy = False
        self.task_description = None
        self.file_path = None
        self.status = "Idle"


    def assign_task(self, task_description, file_path, status="Processing"):
        """Assign a task to the worker.

        Args:
            task_description (str): Task description.
            file_path (str): Path to the file.
            status (str, optional): Task status. Defaults to "Processing".

        Returns:
            bool: True if the task is assigned, False otherwise.
        """
        if not self.is_busy:
            self.is_busy = True
            self.task_description = task_description
            self.file_path = file_path
            self.status = status
            return True
        return False


    def complete_task(self, process_queue_callback, live=None):
        """Complete the task and update the worker status.

        Args:
            process_queue_callback (function): Callback function to process the queue.
            live (Live, optional): Rich Live instance. Defaults to None.
        """
        self.is_busy = False
        self.task_description = None
        self.file_path = None
        self.status = "Idle"
        
        if process_queue_callback:
            process_queue_callback(live)
            
    def __str__(self):
        if self.is_busy:
            return f"Worker {self.worker_id} - {self.task_description} - {self.file_path} - Status: {self.status}"
        else:
            return f"Worker {self.worker_id} - Idle - Status: {self.status}"



#! Global worker pool
max_workers = CoreCount.get_core_count('physical')
workers = [Worker(i + 1, max_workers) for i in range(max_workers)]

def get_idle_worker():
    """Returns an idle worker from the global worker pool."""
    for worker in workers:
        if not worker.is_busy:
            return worker
    return None 


def update_worker_table(workers, queue):
    """Update the worker status table with the current worker and queue status.

    Args:
        workers (list): List of Worker instances.
        queue (list): List of tuples containing task and file path.

    Returns:
        Table: Updated worker status table.
    """
    table = Table(
        title="🎯 Worker Status",
        title_style="bold green",
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
        show_footer=False,
        expand=True,
        show_lines=True,
        style="cyan"
    )

    table.add_column("Worker ID", justify="center", style="bold cyan", width=5)
    table.add_column("Task", justify="left", style="italic magenta", width=20)
    table.add_column("File Path", justify="left", style="dim cyan", width=40)
    table.add_column("Status", justify="center", style="bold green", width=20)

    # workers
    for worker in workers:
        table.add_row(
            str(worker.worker_id),
            worker.task_description or "[italic grey]Idle[/italic grey]",
            worker.file_path or "[italic grey]None[/italic grey]",
            f"[green]{worker.status}[/green]" if worker.is_busy else "[bold grey]Idle[/bold grey]",
        )

    table.add_section()

    # queue
    for idx, (task, file_path) in enumerate(queue, 1):
        table.add_row(f"Queue-{idx}", task, file_path, "Waiting for Worker")

    if all(not worker.is_busy for worker in workers) and not queue:
        return

    return table


def print_summary_table(results):

    summary_table = Table(
        title="📋 Task Summary",
        title_style="bold green",
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
        show_footer=False,
        expand=True,
        show_lines=True,
        style="cyan"
    )
    summary_table.add_column("File Path", style="dim cyan", width=40)
    summary_table.add_column("Task", justify="center", style="italic magenta", width=20)
    summary_table.add_column("Status", justify="center", style="bold green", width=10)

    for result in results:
        summary_table.add_row(
            result["file"], 
            result["task"], 
            f"[green]{result['status']}[/green]" if result["status"] == "Success" else f"[red]{result['status']}[/red]"
        )

    return summary_table