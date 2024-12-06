import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from src.workers.tasks import TaskProcessor, standalone_process_file
from src.util.signal_handler import SignalHandler
from src.util.logger import Logger

class AudioNormalizationCLI:
    def __init__(self):
        """Initialize the AudioNormalizationCLI class."""
        self.console = Console()
        self.temp_files = []
        self.signal_handler = SignalHandler(self.temp_files)
        self.logger = Logger(log_file="app.log")
        self.task_processor = TaskProcessor()

    def display_menu(self):
        """Display the main menu."""
        menu_table = Table(
            title="",
            title_style="cornsilk1",
            box=box.SIMPLE,
            pad_edge=True,
            show_lines=True,
            header_style="bold magenta",
            style="cyan",
            expand=True,
        )
        menu_table.add_column("Option", justify="center", style="bold cyan")
        menu_table.add_column("Description", justify="left", style="grey82")
        menu_table.add_row("[1]", "Apply Simple Audio Boost to Media File")
        menu_table.add_row("[2]", "Normalize Audio Track for a Media File")
        menu_table.add_row("[3]", "Normalize Audio Tracks for All Media Files in a Directory")
        menu_table.add_row("[4]", "[red bold]Exit[/red bold]")
        menu_panel = Panel(
            menu_table,
            title="🎵 [bold magenta]Audio Normalization CLI[/bold magenta] 🎥",
            border_style="cyan",
            padding=(1, 2),
            expand=True,
        )
        self.console.print(menu_panel)

    def handle_option(self, choice):
        """Handle the user's choice from the main menu.

        Args:
            choice (str): The user's choice.

        Returns:
            str: The exit status.
        """
        if choice == '1':
            media_path = self.console.input("[bold cornsilk1]Enter the path to the media file:[/bold cornsilk1] ").strip()
            media_path = self.clean_path(media_path)
            if not os.path.exists(media_path):
                self.logger.error("The specified media path does not exist, or isn't a valid media file. Please try again.")
                return

            volume_boost_percentage = self.console.input(
                "[bold cornsilk1]Enter volume boost percentage (e.g., 10 for 10% increase):[/bold cornsilk1] "
            ).strip()
            try:
                volume_boost_percentage = float(volume_boost_percentage)
                task_desc, file_path, success = standalone_process_file(
                    3, media_path, volume_boost_percentage=volume_boost_percentage, temp_files=self.temp_files
                )
            except ValueError:
                self.logger.error("Invalid percentage value. Please enter a valid number.")
        
        elif choice == '2':
            media_path = self.console.input("[bold cornsilk1]Enter the path to the media file:[/bold cornsilk1] ").strip()
            media_path = self.clean_path(media_path)
            if not os.path.exists(media_path):
                self.logger.error("The specified media path does not exist, or isn't a valid media file. Please try again.")
                return
            task_desc, file_path, success = standalone_process_file(
                1, media_path, temp_files=self.temp_files
            )

        elif choice == '3':
            directory = self.console.input("[bold cornsilk1]Enter the path to the directory:[/bold cornsilk1] ").strip()
            directory = self.clean_path(directory)
            if not os.path.isdir(directory):
                self.logger.error("The specified directory does not exist. Please try again.")
                return
            self.task_processor.process_directory(directory, temp_files=self.temp_files)

        elif choice == '4':
            self.logger.info("Exiting program...")
            return "exit"
        else:
            self.logger.error("Invalid choice. Please try again.")

    def clean_path(self, path):
        """Remove double quotes from a string path.

        Args:
            path (str): The path to clean.

        Returns:
            str: The cleaned path.
        """
        return path.replace('"', "")

    def run(self):
        """Run the AudioNormalizationCLI application."""
        try:
            while True:
                self.display_menu()
                choice = self.console.input("[bold cornsilk1]Enter your choice:[/bold cornsilk1] ").strip()
                if self.handle_option(choice) == "exit":
                    break
        finally:
            self.signal_handler.cleanup_temp_files()


if __name__ == "__main__":
    app = AudioNormalizationCLI()
    app.run()