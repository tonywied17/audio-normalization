import os
import json
from datetime import datetime

def log_to_file(log_file, message):
    try:
        log_dir = os.path.join(os.getcwd(), "logs")

        # Ensure log_file is a non-empty list
        if isinstance(log_file, list) and log_file:
            log_file = log_file[0]
        elif not log_file:
            log_file = "default.log"  # Default log file name if log_file is empty or None

        log_file_path = os.path.join(log_dir, log_file)
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Truncate the message if it's too long
        max_message_length = 1024
        if len(message) > max_message_length:
            message = message[:max_message_length] + "... [truncated]"

        # Open and write the message to the log file
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
            
    except OSError as e:
        print(f"Error writing to log file: {e}")



def append_processed_files(file_path: str, processed_files_list: str = "processed_files.json") -> None:
    """
    Appends a file path to a JSON list of processed files.
    
    Args:
        file_path (str): The file path to add to the processed list.
        processed_files_list (str): Path to the JSON file. Defaults to 'processed_files.json'.
    """
    if os.path.exists(processed_files_list):
        with open(processed_files_list, "r") as f:
            processed_files = json.load(f)
    else:
        processed_files = []

    if file_path not in processed_files:
        processed_files.append(file_path)

    with open(processed_files_list, "w") as f:
        json.dump(processed_files, f, indent=4)
