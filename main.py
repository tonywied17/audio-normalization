import os
import logging
from rich.console import Console
from rich.table import Table
from src.manage_tasks import process_file, process_directory
from src.signal_handler import SignalHandler

temp_files = []

logging.basicConfig(level=logging.INFO)

signal_handler = SignalHandler(temp_files, log_file='app.log')

console = Console()

def clean_path(path):
    """
    Remove any surrounding double quotes from the given path.
    """
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path.strip()

def main():
    try:
        while True:
            menu_table = Table(
                box=None,
                pad_edge=True,
            )
            menu_table.add_column("Option", style="bold")
            menu_table.add_column("Description", style="italic")

            menu_table.add_row("1", "Normalize Audio Track for a Video File")
            menu_table.add_row("2", "Normalize Audio Tracks for All Video Files in a Directory")
            menu_table.add_row("3", "Apply Simple Audio Boost to Video File")
            menu_table.add_row("4", "Exit")

            console.print(menu_table)

            choice = input("Enter your choice: ").strip()

            if choice == '1':
                video_path = input("Enter the path to the video file (e.g., E:\\Movies\\video.mkv): ").strip()
                video_path = clean_path(video_path)

                if not os.path.exists(video_path):
                    console.print("[orange_red1]The specified video path does not exist. Please try again.[/orange_red1]")
                    continue

                console.print("\n[green]Processing video for Normalization...[/green]")
                temp_files.append(f"{os.path.splitext(video_path)[0]}_Normalized_TEMP.mkv")
                process_file(1, video_path, temp_files=temp_files, is_single_file=True)

            elif choice == '2':
                directory = input("Enter the path to the directory (or 'exit' to return to the main menu): ").strip()
                directory = clean_path(directory)

                if directory.lower() == 'exit':
                    continue

                if not os.path.isdir(directory):
                    console.print("[orange_red1]The specified directory does not exist. Please try again.[/orange_red1]")

                console.print("\n[green]Processing directory...[/green]")
                process_directory(directory, temp_files=temp_files)

            elif choice == '3':
                video_path = input("Enter the path to the video file (e.g., E:\\Movies\\video.mkv): ").strip()
                video_path = clean_path(video_path)

                if not os.path.exists(video_path):
                    console.print("[orange_red1]The specified video path does not exist. Please try again.[/orange_red1]")
                    continue

                volume_boost_percentage = input("Enter volume boost percentage (e.g., 10 for 10% increase): ").strip()

                try:
                    volume_boost_percentage = float(volume_boost_percentage)
                    console.print(f"\n[green]Applying {volume_boost_percentage}% volume boost to {video_path}...[/green]")
                    process_file(3, video_path, volume_boost_percentage=volume_boost_percentage, temp_files=temp_files)

                except ValueError:
                    console.print("[orange_red1]Invalid percentage value. Please enter a valid number.[/orange_red1]")

            elif choice == '4':
                console.print("[medium_spring_green]Exiting program...[/medium_spring_green]")
                break
            else:
                console.print("[yellow]Invalid choice. Please try again.[/yellow]")

    finally:
        signal_handler.cleanup_temp_files()


if __name__ == "__main__":
    main()
