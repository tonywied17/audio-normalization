"""
Simple logger with Rich console output and file logging.
"""

import os
import datetime
from enum import Enum
from typing import Optional
from rich.console import Console
from rich.text import Text


class LogLevel(Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"


class Logger:
    def __init__(self, log_file: str = "app.log", log_dir: str = "logs"):
        self.log_dir = os.path.join(os.getcwd(), log_dir)
        self.log_file = os.path.join(self.log_dir, log_file)
        self.console = Console()

        os.makedirs(self.log_dir, exist_ok=True)

    def _format_message(self, level: LogLevel, message: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} | {level.value} | {message}"

    def _write_to_file(self, message: str):
        try:
            raw_message = str(message).replace('\n', ' ')
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(raw_message + "\n")
        except OSError as e:
            self.console.print(f"[red]Error writing to log file: {e}[/red]")

    def _print_to_console(self, level: LogLevel, message: str):
        if level == LogLevel.INFO:
            self.console.print(message, style="dim bright_white", markup=False, emoji=False)
        elif level == LogLevel.ERROR:
            self.console.print(message, style="red", markup=False, emoji=False)
        elif level == LogLevel.SUCCESS:
            self.console.print(message, style="green", markup=False, emoji=False)
        elif level == LogLevel.WARNING:
            self.console.print(message, style="yellow", markup=False, emoji=False)

    def log(self, level: LogLevel, message: str):
        formatted = self._format_message(level, message)
        self._write_to_file(formatted)
        self._print_to_console(level, message)

    def info(self, message: str):
        self.log(LogLevel.INFO, message)

    def error(self, message: str):
        self.log(LogLevel.ERROR, message)

    def success(self, message: str):
        self.log(LogLevel.SUCCESS, message)

    def warning(self, message: str):
        self.log(LogLevel.WARNING, message)