"""
Command handling module for audio normalization and boosting.
"""

from processors.audio import AudioProcessor
from processors.batch import BatchProcessor
from core.logger import Logger
import os
import subprocess
import pathlib
import shlex


class CommandHandler:
    def __init__(self, max_workers: int = None):
        self.logger = Logger()
        self.batch_processor = BatchProcessor(max_workers=max_workers)


    def process_file(self, file_path: str, operation: str, **kwargs) -> bool:
        processor = AudioProcessor()
        try:
            if operation == "boost":
                boost_percent = float(kwargs.get('boost_percent', 0))
                dry_run = kwargs.get('dry_run', False)
                show_ui = kwargs.get('show_ui', True)
                return processor.boost_audio(file_path, boost_percent, show_ui=show_ui, dry_run=dry_run) is not None
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            return False

    def handle_boost_directory(self, dir_path: str, percentage: float, dry_run: bool = False, max_workers: int = None):
        self.logger.info(f"Boosting all audio files in directory: {dir_path} by {percentage}%")
        results = self.batch_processor.boost_files_with_progress(dir_path, percentage, dry_run=dry_run, max_workers=max_workers)
        return results

    def handle_normalize(self, path: str, dry_run: bool = False, max_workers: int = None):
        safe_path = path.rstrip("/\\")
        if os.path.isdir(path):
            self.logger.info(f"Normalizing directory: {safe_path}")
            results = self.batch_processor.process_directory(path, dry_run=dry_run, max_workers=max_workers)
        elif os.path.isfile(path):
            self.logger.info(f"Normalizing file: {safe_path}")
            result = self.batch_processor.process_single_file_with_progress(path, dry_run=dry_run)
            results = [result]
        else:
            self.logger.error("Invalid path provided")
            return []
        return results

    def handle_boost(self, path: str, percentage: str, dry_run: bool = False, max_workers: int = None):
        try:
            boost_percent = float(percentage)
        except ValueError:
            self.logger.error("Invalid boost percentage")
            return []
        if os.path.isdir(path):
            return self.handle_boost_directory(path, boost_percent, dry_run=dry_run, max_workers=max_workers)
        elif os.path.isfile(path):
            self.logger.info(f"Boosting {path} by {boost_percent}%")
            success = self.process_file(path, 'boost', boost_percent=boost_percent, dry_run=dry_run, show_ui=True)
            results = [{
                "file": path,
                "task": f"Boost {boost_percent}% Audio",
                "status": "Success" if success else "Failed"
            }]
            return results
        else:
            self.logger.error("Invalid file or directory path")
            return []
        
        
    def setup_ffmpeg(self) -> list:
        """Attempt to run a guided setup to install Scoop, Python, and FFmpeg on Windows.

        This runs the commands from the project's `scoop_installation_guide.md`. Each
        step is executed via PowerShell and the stdout/stderr captured. Returns a list
        of step results.
        """
        results = []
        project_root = str(pathlib.Path(__file__).resolve().parent.parent.parent)

        steps = [
            {"name": "Allow user scripts (Set-ExecutionPolicy)",
             "cmd": "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"},
            {"name": "Install Scoop bootstrap", "cmd": "iwr -useb get.scoop.sh | iex"},
            {"name": "Install FFmpeg via Scoop", "cmd": "scoop install ffmpeg"},
        ]

        for step in steps:
            name = step["name"]
            cmd = step["cmd"]
            try:
                self.logger.info(f"Running setup step: {name}")
                # Run via PowerShell to support the scoop bootstrap command
                proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], cwd=project_root, capture_output=True, text=True)
                ok = proc.returncode == 0
                out = proc.stdout.strip()
                err = proc.stderr.strip()
                results.append({"name": name, "success": ok, "stdout": out, "stderr": err})
                if ok:
                    self.logger.info(f"Setup step succeeded: {name}")
                else:
                    self.logger.error(f"Setup step failed: {name}: {err}")
            except Exception as e:
                results.append({"name": name, "success": False, "stdout": "", "stderr": str(e)})
                self.logger.error(f"Exception running setup step {name}: {e}")
        return results
