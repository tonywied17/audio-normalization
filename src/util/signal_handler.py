import os
import sys
import signal
import threading
from src.util.logger import Logger

class SignalHandler:
    def __init__(self, temp_files):
        self.temp_files = temp_files
        self.logger = Logger(log_file="app.log")
        self.cleanup_lock = threading.Lock()

        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        self.logger.info("Program interrupted or terminated. Cleaning up...")
        self.cleanup_temp_files()
        sys.exit(0)

    def cleanup_temp_files(self):
        """
        Clean up all temporary files created during the program's execution.
        Use a lock to prevent concurrent access.
        """
        with self.cleanup_lock:
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        self.logger.info(f"Temporary file {temp_file} deleted.")
                    except Exception as e:
                        self.logger.error(f"Error deleting {temp_file}: {e}")
