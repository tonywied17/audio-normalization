"""
Top-level launcher for the Audio Normalization and Boosting Tool.

This script keeps compatibility with the existing internal modules which
use top-level imports like `core` and `cli` by adding `src/` to `sys.path`.
Run this from the project root:

    python audio_tool.py

Or run as a module (recommended):

    python -m audio_tool

"""
import os
import sys
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cli import parse_args, AudioNormalizationCLI, CommandHandler
from core.signal_handler import SignalHandler
from core.config import NORMALIZATION_PARAMS


def run_interactive(cli: AudioNormalizationCLI, handler: CommandHandler, signal_handler: SignalHandler, debug: bool = False):
    """Run the interactive CLI loop."""
    while True:
        cli.display_menu()
        choice = cli.console.input("[bold wheat1]Enter choice: [/bold wheat1]").strip()
        if getattr(cli, "ffmpeg_found", False):
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
        else:
            if choice == "1":
                confirm = cli.console.input("[bold wheat1]Run FFmpeg setup (requires PowerShell & may need admin privileges)? (y/N): [/bold wheat1]").strip().lower()
                if confirm == "y":
                    results = handler.setup_ffmpeg()
                    for step in results:
                        name = step.get("name")
                        ok = step.get("success")
                        status = "Success" if ok else "Failed"
                        color = "green" if ok else "red"
                        cli.console.print(f"{name}: [{color}]{status}[/{color}]")
                        if step.get("stderr"):
                            cli.console.print(step.get("stderr"))
                    if not debug and getattr(cli, "_debug_no_ffmpeg", False):
                        try:
                            delattr(cli, "_debug_no_ffmpeg")
                        except Exception:
                            try:
                                del cli._debug_no_ffmpeg
                            except Exception:
                                cli._debug_no_ffmpeg = False
                else:
                    handler.logger.info("FFmpeg setup canceled by user")
            elif choice == "2":
                handler.logger.info("Exiting...")
                break
            else:
                handler.logger.error("Invalid choice")
    signal_handler.cleanup_temp_files()


def main():
    args = parse_args()
    handler = CommandHandler(max_workers=getattr(args, 'workers', None) if args else None)
    cli = AudioNormalizationCLI(handler)
    # honor debug flag to simulate missing ffmpeg
    if args and getattr(args, 'debug_no_ffmpeg', False):
        setattr(cli, '_debug_no_ffmpeg', True)
    signal_handler = SignalHandler([])

    if args is None or getattr(args, 'debug_no_ffmpeg', False):
        run_interactive(cli, handler, signal_handler, debug=getattr(args, 'debug_no_ffmpeg', False) if args else False)
    else:
        if getattr(args, 'normalize', None):
            if args.I is not None:
                NORMALIZATION_PARAMS['I'] = args.I
            if args.TP is not None:
                NORMALIZATION_PARAMS['TP'] = args.TP
            if args.LRA is not None:
                NORMALIZATION_PARAMS['LRA'] = args.LRA

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
