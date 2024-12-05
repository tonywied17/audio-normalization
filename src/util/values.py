import os
import subprocess


#! Normalization parameters
NORMALIZATION_PARAMS = {
    "I": -16,  #? Integrated loudness
    "TP": -1.5,  #? True peak
    "LRA": 11,  #? Loudness range
}


#! CPU Core Count Utility
class CoreCount:
    """Utility class for getting the number of physical and logical CPU cores."""

    @staticmethod
    def get_windows_cores(logical=False):
        """Get the number of physical or logical cores for Windows."""
        try:
            if logical:
                return os.cpu_count()
            output = subprocess.check_output("wmic CPU get NumberOfCores", shell=True)
            cores = [int(x) for x in output.decode().split() if x.isdigit()]
            return sum(cores)
        except Exception:
            return os.cpu_count()

    @staticmethod
    def get_macos_cores(logical=False):
        """Get the number of physical or logical cores for macOS."""
        try:
            if logical:
                return os.cpu_count()
            output = subprocess.check_output(
                ["sysctl", "-n", "hw.physicalcpu"]
            ).strip()
            return int(output)
        except Exception:
            return os.cpu_count()

    @staticmethod
    def get_linux_cores(logical=False):
        """Get the number of physical or logical cores for Linux."""
        try:
            if logical:
                return os.cpu_count()

            output = subprocess.check_output(
                "lscpu | grep '^Core(s) per socket:' | awk '{print $4}'", 
                shell=True
            )
            cores_per_socket = int(output.decode().strip())
            output = subprocess.check_output(
                "lscpu | grep '^Socket(s):' | awk '{print $2}'", 
                shell=True
            )
            sockets = int(output.decode().strip())
            return cores_per_socket * sockets
        except Exception:
            return os.cpu_count()

    @staticmethod
    def get_core_count(core_type='physical'):
        """Returns the number of CPU cores (physical or logical) based on the operating system and the type."""
        os_type = os.name
        logical = core_type == 'logical'

        if os_type == "nt":
            return CoreCount.get_windows_cores(logical)
        elif os_type == "posix":
            system_type = os.uname().sysname.lower()
            if "darwin" in system_type:
                return CoreCount.get_macos_cores(logical)
            elif "linux" in system_type:
                return CoreCount.get_linux_cores(logical)
            else:
                return os.cpu_count()
        else:
            return os.cpu_count() 
