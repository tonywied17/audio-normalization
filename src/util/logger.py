import os
import datetime
from enum import Enum
from rich.console import Console
from rich.text import Text
from rich.table import Table
from rich import box


class LogLevel(Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class Logger:
    
    def __init__(self, log_file="app.log", log_dir="logs"):
        self.log_dir = os.path.join(os.getcwd(), log_dir)
        self.log_file = os.path.join(self.log_dir, log_file)
        self.console = Console()
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format the log message with a timestamp and level."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} | {level.value} | {message}"

    def _write_to_file(self, message: str):
        """Write the log message to the log file without newlines and strip Rich tags."""
        try:
            stripped_message = Text.from_markup(message).plain
            stripped_message = stripped_message.replace("\n", " ")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(stripped_message + "\n")
        except OSError as e:
            self.console.print(f"[red]Error writing to log file: {e}[/red]")

    def _print_log_table(self, level: LogLevel, message: str):
        """Display the log message in a rich table format."""
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE, expand=True)
        table.add_column("Level", style="bold", width=10, justify="center")
        table.add_column("Message", style="green", width=60, justify="left")
        table.add_column("Timestamp", style="dim", width=20, justify="right")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(level.value, message, timestamp)

        if level == LogLevel.INFO:
            self.console.print(table, style="cyan")
        elif level == LogLevel.ERROR:
            self.console.print(table, style="bold red")
        elif level == LogLevel.SUCCESS:
            self.console.print(table, style="green")

    def log(self, level: LogLevel, message: str):
        """Log a message with the given log level."""
        formatted_message = self._format_message(level, message)
        self._write_to_file(formatted_message)
        self._print_log_table(level, message) 

    def info(self, message: str):
        """Log an info-level message."""
        self.log(LogLevel.INFO, message)

    def error(self, message: str):
        """Log an error-level message."""
        self.log(LogLevel.ERROR, message)

    def success(self, message: str):
        """Log a success-level message."""
        self.log(LogLevel.SUCCESS, message)
