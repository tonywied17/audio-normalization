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
            file_path (str): File path.
            status (str, optional): Task status. Defaults to "Processing".

        Returns:
            _type_: _description_
        """
        if not self.is_busy:
            self.is_busy = True
            self.task_description = task_description
            self.file_path = file_path
            self.status = status
            logger.info(f"Assigned to Worker {self.worker_id}.\n\n[bold]Task:[/bold] {self.task_description}\n[bold]File:[/bold] {self.file_path}")
            return True
        else:
            logger.warning(f"Worker {self.worker_id} is busy. Task not assigned.")
        return False


    def complete_task(self, task_processor, live=None):
        """Complete the task and update the worker status.

        Args:
            task_processor (TaskProcessor): The TaskProcessor instance.
            live (Live, optional): Rich Live instance. Defaults to None.
        """
        self.is_busy = False
        self.task_description = None
        self.file_path = None
        self.status = "Idle"

        task_processor.display_and_update_worker_table(live)
        task_processor.process_queue(live)


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


def print_summary_table(results):
    """Prints a summary table of the task results.

    Args:
        results (list): List of task results.

    Returns:
        Table: Rich Table instance.
    """
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