"""
Main entry point for the Audio Normalization and Boosting Tool.
"""

import os
from src.argparse_config import parse_args
from src.commands import CommandHandler
from src.cli import AudioNormalizationCLI
from src.signal_handler import SignalHandler
from src.config import NORMALIZATION_PARAMS


def run_interactive(cli: AudioNormalizationCLI, handler: CommandHandler, signal_handler: SignalHandler):
    """Run the interactive CLI loop."""
    while True:
        cli.display_menu()
        choice = cli.console.input("[bold wheat1]Enter choice: [/bold wheat1]").strip()
        if choice == "1":
            path = cli.console.input("[bold wheat1]Enter file or directory path: [/bold wheat1]").strip()
            percentage = cli.console.input("[bold wheat1]Enter boost percentage: [/bold wheat1]").strip()
            results = handler.handle_boost(path, percentage)
            cli.display_results(results)
        elif choice == "2":
            path = cli.console.input("[bold wheat1]Enter file or directory path: [/bold wheat1]").strip()
            if os.path.exists(path):
                results = handler.handle_normalize(path)
                cli.display_results(results)
            else:
                handler.logger.error("File or directory not found")
        elif choice == "3":
            handler.logger.info("Exiting...")
            break
        else:
            handler.logger.error("Invalid choice")
    signal_handler.cleanup_temp_files()

def main():
    """Main function to run the application."""
    args = parse_args()
    handler = CommandHandler(max_workers=getattr(args, 'workers', None) if args else None)
    cli = AudioNormalizationCLI(handler)
    signal_handler = SignalHandler([])

    if args and getattr(args, 'normalize', None):
        if args.I is not None:
            NORMALIZATION_PARAMS['I'] = args.I
        if args.TP is not None:
            NORMALIZATION_PARAMS['TP'] = args.TP
        if args.LRA is not None:
            NORMALIZATION_PARAMS['LRA'] = args.LRA

    if args is None:
        run_interactive(cli, handler, signal_handler)
    else:
        if getattr(args, 'normalize', None):
            dry_run = getattr(args, 'dry_run', False)
            workers = getattr(args, 'workers', None)
            results = handler.handle_normalize(args.normalize, dry_run=dry_run, max_workers=workers)
            cli.display_results(results)
        elif getattr(args, 'boost', None):
            dry_run = getattr(args, 'dry_run', False)
            workers = getattr(args, 'workers', None)
            results = handler.handle_boost(args.boost[0], args.boost[1], dry_run=dry_run, max_workers=workers)
            cli.display_results(results)
        signal_handler.cleanup_temp_files()

if __name__ == "__main__":
    main()
