import os
import sys
import signal
from src.utils import log_to_file

class SignalHandler:
    def __init__(self, temp_files, log_file='app.log'):
        self.temp_files = temp_files
        self.log_file = log_file

        #! Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        log_to_file(self.log_file, "Program interrupted or terminated. Cleaning up...")
        self.cleanup_temp_files()
        sys.exit(0)

    def cleanup_temp_files(self):
        """
        Clean up all temporary files created during the program's execution.
        """
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    log_to_file(self.log_file, f"Temporary file {temp_file} deleted.")
                except Exception as e:
                    log_to_file(self.log_file, f"Error deleting {temp_file}: {e}")