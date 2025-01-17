import os, re, sys
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from src.workers.tasks import TaskProcessor, standalone_process_file
from src.util.signal_handler import SignalHandler
from src.util.logger import Logger

def parse_args():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Audio Normalization CLI Tool")
    group = parser.add_mutually_exclusive_group()

    # *Normalize flag with a required path argument
    group.add_argument("-n", "--normalize", type=str, metavar="PATH",
                       help="Path to a file or directory for normalization")

    #* Boost flag with a required file and percentage argument
    group.add_argument("-b", "--boost", nargs=2, metavar=("FILE", "PERCENTAGE"),
                       help="Path to a single file and boost percentage (e.g., +6 for 6% increase, -6 for decrease)")

    #* Parameters for normalization (only valid with --normalize)
    parser.add_argument("--I", type=float, default=None, help="Integrated loudness target (e.g., -16)")
    parser.add_argument("--TP", type=float, default=None, help="True peak target (e.g., -1.5)")
    parser.add_argument("--LRA", type=float, default=None, help="Loudness range target (e.g., 11)")

    args = parser.parse_args()

    #* Validate that boost and normalization parameters are mutually exclusive
    if args.boost and (args.I is not None or args.TP is not None or args.LRA is not None):
        print("Error: Normalization parameters (--I, --TP, --LRA) cannot be used with --boost.")
        sys.exit(1)

    #* Validate that normalization parameters are only used with --normalize
    if args.normalize is None and (args.I is not None or args.TP is not None or args.LRA is not None):
        print("Error: Normalization parameters (--I, --TP, --LRA) must be used with --normalize.")
        sys.exit(1)

    if not any(vars(args).values()):
        return None

    return args

class AudioNormalizationCLI:
    """
    Attributes:
    - console: Rich Console object
    - temp_files: List of temporary files
    - signal_handler: SignalHandler object
    - logger: Logger object
    - task_processor: TaskProcessor object
    - normalize: Normalize flag
    - boost: Boost flag
    """
    def __init__(self, normalize=None, boost=None):
        """Initialize the AudioNormalizationCLI class."""
        self.console = Console()
        self.temp_files = []
        self.signal_handler = SignalHandler(self.temp_files)
        self.logger = Logger(log_file="app.log")
        self.task_processor = TaskProcessor()
        self.normalize = normalize
        self.boost = boost

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

    def normalize_action(self, path):
        """Handle normalization for a file or directory."""
        path = self.clean_path(path)

        if os.path.isdir(path):
            self.logger.info(f"Normalizing all audio files in directory: {path}")
            self.task_processor.process_directory(path, temp_files=self.temp_files)
        elif os.path.isfile(path):
            self.logger.info(f"Normalizing single audio file: {path}")
            task_desc, file_path, success = standalone_process_file(1, path, temp_files=self.temp_files)
        else:
            self.logger.error("Invalid path. Please provide a valid file or directory.")

    def boost_action(self, file_path, percentage):
        """Handle boosting for a single file."""
        file_path = self.clean_path(file_path)

        if not os.path.isfile(file_path):
            self.logger.error("Invalid file path. Please provide a valid file.")
            return

        try:
            percentage = float(percentage)
            self.logger.info(f"Boosting audio file: {file_path} by {percentage}%")
            task_desc, file_path, success = standalone_process_file(
                3, file_path, volume_boost_percentage=percentage, temp_files=self.temp_files
            )
        except ValueError:
            self.logger.error("Invalid percentage value. Please enter a valid number.")

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
            if self.normalize:
                self.normalize_action(self.normalize)
            elif self.boost:
                self.boost_action(self.boost[0], self.boost[1])
            else:
                while True:
                    self.display_menu()
                    choice = self.console.input("[bold cornsilk1]Enter your choice:[/bold cornsilk1] ").strip()
                    if self.handle_option(choice) == "exit":
                        break
        finally:
            self.signal_handler.cleanup_temp_files()

    def handle_option(self, choice):
        """Handle the user's choice from the main menu.

        Args:
            choice (str): The user's choice.

        Returns:
            str: The exit status.
        """
        if choice == "1":
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

        elif choice == "2":
            media_path = self.console.input("[bold cornsilk1]Enter the path to the media file:[/bold cornsilk1] ").strip()
            media_path = self.clean_path(media_path)
            if not os.path.exists(media_path):
                self.logger.error("The specified media path does not exist, or isn't a valid media file. Please try again.")
                return
            task_desc, file_path, success = standalone_process_file(
                1, media_path, temp_files=self.temp_files
            )

        elif choice == "3":
            directory = self.console.input("[bold cornsilk1]Enter the path to the directory:[/bold cornsilk1] ").strip()
            directory = self.clean_path(directory)
            if not os.path.isdir(directory):
                self.logger.error("The specified directory does not exist. Please try again.")
                return
            self.task_processor.process_directory(directory, temp_files=self.temp_files)

        elif choice == "4":
            self.logger.info("Exiting program...")
            return "exit"
        else:
            self.logger.error("Invalid choice. Please try again.")

# ! --
if __name__ == "__main__":
    from src.util.values import NORMALIZATION_PARAMS

    args = parse_args()

    #* Update normalization parameters dynamically if --normalize is used
    if args and args.normalize:
        if args.I is not None:
            NORMALIZATION_PARAMS['I'] = args.I
        if args.TP is not None:
            NORMALIZATION_PARAMS['TP'] = args.TP
        if args.LRA is not None:
            NORMALIZATION_PARAMS['LRA'] = args.LRA

    if args is None:
        #* No arguments provided; run interactive mode
        app = AudioNormalizationCLI(normalize=None, boost=None)
        app.run()
    else:
        #* Handle command-line arguments
        if args.normalize:
            app = AudioNormalizationCLI(normalize=args.normalize, boost=None)
            app.run()
        elif args.boost:
            app = AudioNormalizationCLI(normalize=None, boost=args.boost)
            app.run()
