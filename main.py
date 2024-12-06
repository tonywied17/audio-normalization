import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from src.workers.tasks import process_file, process_directory
from src.util.signal_handler import SignalHandler
from src.util.logger import Logger

class AudioNormalizationCLI:
    def __init__(self):
        self.console = Console()
        self.temp_files = []
        self.signal_handler = SignalHandler(self.temp_files)
        self.logger = Logger(log_file="app.log")

    def clean_path(self, path):
        """
        Remove any surrounding double quotes from the given path.
        """
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        return path.strip()

    def display_menu(self):
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
                process_file(3, media_path, volume_boost_percentage=volume_boost_percentage, temp_files=self.temp_files, is_single_file=True)
            except ValueError:
                self.logger.error("Invalid percentage value. Please enter a valid number.")
        
        elif choice == '2':
            media_path = self.console.input("[bold cornsilk1]Enter the path to the media file:[/bold cornsilk1] ").strip()
            media_path = self.clean_path(media_path)
            if not os.path.exists(media_path):
                self.logger.error("The specified media path does not exist, or isn't a valid media file. Please try again.")
                return
            process_file(1, media_path, temp_files=self.temp_files, is_single_file=True)

        elif choice == '3':
            directory = self.console.input("[bold cornsilk1]Enter the path to the directory:[/bold cornsilk1] ").strip()
            directory = self.clean_path(directory)
            if not os.path.isdir(directory):
                self.logger.error("The specified directory does not exist. Please try again.")
                return
            process_directory(directory, temp_files=self.temp_files)

        elif choice == '4':
            self.logger.info("Exiting program...")
            return "exit"
        else:
            self.logger.error("Invalid choice. Please try again.")

    def run(self):
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