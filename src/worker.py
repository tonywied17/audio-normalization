from rich.console import Console
from rich.table import Table
import os
from rich.live import Live

console = Console()

class Worker:
    def __init__(self, worker_id, max_workers):
        self.worker_id = worker_id
        self.max_workers = max_workers
        self.is_busy = False
        self.task_description = None
        self.file_path = None
        self.status = "Idle"

    def assign_task(self, task_description, file_path):
        """Assign a task to the worker if it's not already busy."""
        if not self.is_busy:
            self.is_busy = True
            self.task_description = task_description
            self.file_path = file_path
            self.status = "Processing"
            return True
        return False

    def complete_task(self, process_queue_callback):
        """Complete the task and set worker status back to Idle."""
        self.is_busy = False
        self.task_description = None
        self.file_path = None
        self.status = "Idle"
        if process_queue_callback:
            process_queue_callback()

    def __str__(self):
        if self.is_busy:
            return f"Worker {self.worker_id} - {self.task_description} - {self.file_path} - Status: {self.status}"
        else:
            return f"Worker {self.worker_id} - Idle - Status: {self.status}"

max_workers = os.cpu_count()
workers = [Worker(i + 1, max_workers) for i in range(max_workers)]

def get_idle_worker():
    """Returns an idle worker from the global worker pool."""
    for worker in workers:
        if not worker.is_busy:
            return worker
    return None 

def update_worker_table(workers, queue):
    """Generate a dynamic Rich table showing the status of workers and the task queue."""
    table = Table(title="Worker Status", show_header=True, header_style="bold magenta")
    table.add_column("Worker ID", justify="center")
    table.add_column("Task", justify="left")
    table.add_column("File Path", justify="left")
    table.add_column("Status", justify="center")
    table.add_column("Queue (Pending Tasks)", justify="left")

    for worker in workers:
        queue_display = "\n".join([f"{task} ({file_path})" for task, file_path in queue])
        table.add_row(
            str(worker.worker_id),
            worker.task_description or "Idle",
            worker.file_path or "",
            "Processing" if worker.is_busy else "Idle",
            queue_display if worker.worker_id == workers[-1].worker_id else ""
        )

    return table

def print_summary_table(results):
    """
    Generate and print the summary table for all completed tasks.
    """
    summary_table = Table(title="Task Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("File Path", style="dim", width=40)
    summary_table.add_column("Task", justify="center", width=20)
    summary_table.add_column("Status", justify="center", width=10)

    for result in results:
        summary_table.add_row(result["file"], result["task"], result["status"])

    console.clear()
    console.print(summary_table)
