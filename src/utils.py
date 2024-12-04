import os

def log_to_file(log_file, message):
    try:
        log_dir = os.path.join(os.getcwd(), "logs")

        if not log_file:
            log_file = "app.log"

        log_file_path = os.path.join(log_dir, log_file)
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        max_message_length = 1024
        if len(message) > max_message_length:
            message = message[:max_message_length] + "... [truncated]"

        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
            
    except OSError as e:
        print(f"Error writing to log file: {e}")