"""
Simple logger with Rich console output and file logging.
"""

import os
import datetime
from enum import Enum
from typing import Optional
from rich.console import Console
from .config import LOG_DIR, LOG_FILE, LOG_FFMPEG_DEBUG


class LogLevel(Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"


class Logger:
    def __init__(self, log_file: Optional[str] = None, log_dir: Optional[str] = None):
        if log_dir is None:
            log_dir = LOG_DIR
        if log_file is None:
            log_file = LOG_FILE
        self._log_dir = os.path.join(os.getcwd(), log_dir)
        self._log_file = os.path.join(self._log_dir, log_file)
        self._log_ffmpeg = LOG_FFMPEG_DEBUG
        self.console = Console()

        os.makedirs(self._log_dir, exist_ok=True)


    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format the log message with timestamp and level."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} | {level.value} | {message}"


    def _write_to_file(self, message: str):
        """Write the log message to the log file."""
        try:
            raw_message = str(message).replace('\n', ' ')
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(raw_message + "\n")
        except OSError as e:
            self.console.print(f"[red]Error writing to log file: {e}[/red]")


    def _print_to_console(self, level: LogLevel, message: str):
        """Print the log message to the console with appropriate styling."""
        if level == LogLevel.INFO:
            self.console.print(message, style="dim bright_white", markup=False, emoji=False)
        elif level == LogLevel.ERROR:
            self.console.print(message, style="red", markup=False, emoji=False)
        elif level == LogLevel.SUCCESS:
            self.console.print(message, style="green", markup=False, emoji=False)
        elif level == LogLevel.WARNING:
            self.console.print(message, style="yellow", markup=False, emoji=False)


    def log(self, level: LogLevel, message: str):
        """Log a message with the specified log level."""
        formatted = self._format_message(level, message)
        self._write_to_file(formatted)
        self._print_to_console(level, message)

    def info(self, message: str):
        """Log an informational message."""
        self.log(LogLevel.INFO, message)

    def error(self, message: str):
        """Log an error message."""
        self.log(LogLevel.ERROR, message)

    def success(self, message: str):
        """Log a success message."""
        self.log(LogLevel.SUCCESS, message)

    def warning(self, message: str):
        """Log a warning message."""
        self.log(LogLevel.WARNING, message)


    def append_to_file(self, filename: str, content: str):
        """Append content to a specified log file in the log directory."""
        try:
            os.makedirs(self._log_dir, exist_ok=True)
            target = os.path.join(self._log_dir, filename)
            with open(target, "a", encoding="utf-8") as f:
                f.write(str(content))
                f.write("\n")
        except Exception as e:
            self.console.print(f"[red]Error writing to {filename}: {e}[/red]")


    def log_ffmpeg(self, tag: str, media_path: str, content: str):
        """Log FFmpeg debug information to a separate file."""
        try:
            header = f"\n[{tag}] {media_path}:\n"
            body = content or ""
            self.append_to_file(self._log_ffmpeg, header + body + "\n")
        except Exception:
            pass
