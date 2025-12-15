"""
Signal handler for graceful cleanup.
"""

import os
import sys
import signal
import threading
from typing import List
from .logger import Logger


class SignalHandler:
    def __init__(self, temp_files: List[str]):
        self.temp_files = temp_files
        self.logger = Logger()
        self.cleanup_lock = threading.Lock()
        self.child_pids: List[int] = []
        
        SignalHandler._global_instance = self

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        self.logger.info("Program interrupted. Cleaning up temporary files...")
        self.cleanup_temp_files()
        with self.cleanup_lock:
            for pid in list(self.child_pids):
                try:
                    os.kill(pid, signal.SIGTERM)
                    self.logger.info(f"Sent SIGTERM to pid {pid}")
                except Exception as e:
                    self.logger.error(f"Failed to kill pid {pid}: {e}")
        sys.exit(0)

    def cleanup_temp_files(self):
        with self.cleanup_lock:
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        self.logger.info(f"Cleaned up: {temp_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to clean up {temp_file}: {e}")

    _global_instance = None

    @classmethod
    def register_temp_file(cls, path: str):
        if cls._global_instance:
            with cls._global_instance.cleanup_lock:
                if path not in cls._global_instance.temp_files:
                    cls._global_instance.temp_files.append(path)

    @classmethod
    def unregister_temp_file(cls, path: str):
        if cls._global_instance:
            with cls._global_instance.cleanup_lock:
                if path in cls._global_instance.temp_files:
                    cls._global_instance.temp_files.remove(path)

    @classmethod
    def register_child_pid(cls, pid: int):
        if cls._global_instance:
            with cls._global_instance.cleanup_lock:
                if pid not in cls._global_instance.child_pids:
                    cls._global_instance.child_pids.append(pid)

    @classmethod
    def unregister_child_pid(cls, pid: int):
        if cls._global_instance:
            with cls._global_instance.cleanup_lock:
                if pid in cls._global_instance.child_pids:
                    cls._global_instance.child_pids.remove(pid)