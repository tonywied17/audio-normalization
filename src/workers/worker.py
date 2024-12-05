from rich.console import Console
from rich.table import Table
from rich import box
import os

console = Console()


class Worker:
    def __init__(self, worker_id, max_workers):
        self.worker_id = worker_id
        self.max_workers = max_workers
        self.is_busy = False
        self.task_description = None
        self.file_path = None
        self.status = "Idle"

    def assign_task(self, task_description, file_path, status="Processing"):
        """Assign a task to the worker if it's not already busy."""
        if not self.is_busy:
            self.is_busy = True
            self.task_description = task_description
            self.file_path = file_path
            self.status = status
            return True
        return False

    def complete_task(self, process_queue_callback, live=None):
        """Complete the task and set worker status back to Idle."""
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


class WorkerPool:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers or os.cpu_count()
        self.workers = [Worker(i + 1, self.max_workers) for i in range(self.max_workers)]

    def get_idle_worker(self):
        """Returns an idle worker from the pool."""
        for worker in self.workers:
            if not worker.is_busy:
                return worker
        return None

    def update_worker_table(self, queue):
        """
        Generate a dynamic Rich table showing the status of workers and a formatted queue section.
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

        table.add_column("Worker ID", justify="center", style="cyan", width=5)
        table.add_column("Task", justify="left", style="italic magenta", width=20)
        table.add_column("File Path", justify="left", style="dim cyan", width=40)
        table.add_column("Status", justify="center", style="bold green", width=20)

        # workers
        for worker in self.workers:
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

        if all(not worker.is_busy for worker in self.workers) and not queue:
            return

        return table

    def print_summary_table(self, results):
        """
        Generate and print the summary table for all completed tasks.
        """
        summary_table = Table(
            title="📋 Task Summary",
            title_style="bold green",
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE,
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

        console.clear()
        console.print(summary_table)


# Expose a single pool instance
worker_pool = WorkerPool()
__all__ = ["worker_pool"]