import os
import glob
from src.utils import log_to_file

def is_io_bound(video_path, size_threshold_mb=1024):
    """
    Determine if the task is I/O-bound based on the file size.
    
    Args:
        video_path (str): Path to the video file.
        size_threshold_mb (int): The file size threshold in MB to consider I/O-bound (default: 1024 MB).
    
    Returns:
        bool: True if I/O-bound (file size exceeds the threshold), False if CPU-bound.
    """
    try:
        file_size = os.path.getsize(video_path)
        
        size_threshold = size_threshold_mb * 1024 * 1024

        return file_size > size_threshold

    except FileNotFoundError:
        print(f"Error: File '{video_path}' not found.")
        return False 
    except Exception as e:
        print(f"Error determining if the task is I/O-bound for {video_path}: {e}")
        return False


def list_video_files(directory, extensions=(".mp4", ".mkv", ".avi")):
    """
    List all video files in a directory with the given extensions.
    """
    video_files = []
    for ext in extensions:
        video_files.extend(glob.glob(os.path.join(directory, f"*{ext}")))
    return video_files

def verify_directory(directory, log_file_path):
    """
    Check if a directory exists. If not, create it.
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            log_to_file(log_file_path, f"Created directory: {directory}")
        return True
    except Exception as e:
        log_to_file(log_file_path, f"ERROR | Unable to create directory {directory} | {e}")
        return False

def move_file(source_path, destination_dir, log_file_path):
    """
    Move a file to the specified directory.
    """
    try:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"File not found: {source_path}")

        verify_directory(destination_dir, log_file_path)
        file_name = os.path.basename(source_path)
        destination_path = os.path.join(destination_dir, file_name)

        os.rename(source_path, destination_path)
        log_to_file(log_file_path, f"Moved file: {source_path} -> {destination_path}")
        return destination_path
    except Exception as e:
        log_to_file(log_file_path, f"ERROR | Failed to move file {source_path} to {destination_dir} | {e}")
        return None

def backup_file(file_path, backup_dir, log_file_path):
    """
    Create a backup of a file in the specified directory.
    """
    try:
        verify_directory(backup_dir, log_file_path)
        file_name = os.path.basename(file_path)
        backup_path = os.path.join(backup_dir, file_name)

        with open(file_path, 'rb') as original, open(backup_path, 'wb') as backup:
            backup.write(original.read())

        log_to_file(log_file_path, f"Backup created: {file_path} -> {backup_path}")
        return backup_path
    except Exception as e:
        log_to_file(log_file_path, f"ERROR | Failed to backup file {file_path} to {backup_dir} | {e}")
        return None
