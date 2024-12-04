import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from src.manage_tasks import process_file, process_directory
from src.signal_handler import SignalHandler

temp_files = []
signal_handler = SignalHandler(temp_files)
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
                title="🎵 Audio Normalization CLI 🎥",
                title_style="bold magenta",
                box=box.SIMPLE,
                pad_edge=True,
                show_lines=True,
                style="cyan",
            )
            menu_table.add_column("Option", justify="center", style="bold yellow")
            menu_table.add_column("Description", justify="left", style="italic green")

            menu_table.add_row("1", "Normalize Audio Track for a Video File")
            menu_table.add_row("2", "Normalize Audio Tracks for All Video Files in a Directory")
            menu_table.add_row("3", "Apply Simple Audio Boost to Video File")
            menu_table.add_row("4", "[red bold]Exit[/red bold]")

            menu_panel = Panel(
                menu_table,
                title="[bold green]Main Menu[/bold green]",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(menu_panel)

            choice = console.input("[bold yellow]Enter your choice:[/bold yellow] ").strip()

            if choice == '1':
                video_path = console.input("[bold cyan]Enter the path to the video file:[/bold cyan] ").strip()
                video_path = clean_path(video_path)

                if not os.path.exists(video_path):
                    console.print("[orange_red1]The specified video path does not exist. Please try again.[/orange_red1]")
                    continue

                process_file(1, video_path, temp_files=temp_files, is_single_file=True)

            elif choice == '2':
                directory = console.input("[bold cyan]Enter the path to the directory:[/bold cyan] ").strip()
                directory = clean_path(directory)

                if directory.lower() == 'exit':
                    continue

                if not os.path.isdir(directory):
                    console.print("[orange_red1]The specified directory does not exist. Please try again.[/orange_red1]")
                    continue

                process_directory(directory, temp_files=temp_files)

            elif choice == '3':
                video_path = console.input("[bold cyan]Enter the path to the video file:[/bold cyan] ").strip()
                video_path = clean_path(video_path)

                if not os.path.exists(video_path):
                    console.print("[orange_red1]The specified video path does not exist. Please try again.[/orange_red1]")
                    continue

                volume_boost_percentage = console.input(
                    "[bold cyan]Enter volume boost percentage (e.g., 10 for 10% increase):[/bold cyan] "
                ).strip()

                try:
                    volume_boost_percentage = float(volume_boost_percentage)
                    process_file(3, video_path, volume_boost_percentage=volume_boost_percentage, temp_files=temp_files, is_single_file=True)

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
