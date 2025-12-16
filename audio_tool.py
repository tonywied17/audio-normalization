"""
Created Date: Monday December 15th 2025
Author: Tony Wiedman
-----
Last Modified: Mon December 15th 2025 4:48:43 
Modified By: Tony Wiedman
-----
Copyright (c) 2025 Molex

Top-level launcher for the Audio Normalization and Boosting Tool.

Run this from the project root:

    python audio_tool.py

Or run as a module (recommended):

    python -m audio_tool
"""

from cli import parse_args, AudioNormalizationCLI, CommandHandler
from core.signal_handler import SignalHandler
from core.config import NORMALIZATION_PARAMS
import os
import sys
import ctypes
try:
    from ctypes import wintypes
except Exception:
    wintypes = None

if getattr(sys, "frozen", False):
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.AllocConsole()
        try:
            kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
        try:
            STD_OUTPUT_HANDLE = -11
            STD_ERROR_HANDLE = -12
            out_handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            err_handle = kernel32.GetStdHandle(STD_ERROR_HANDLE)
            mode = ctypes.c_uint()
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            if kernel32.GetConsoleMode(out_handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(out_handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
            if kernel32.GetConsoleMode(err_handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(err_handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        except Exception:
            pass
        try:
            user32 = ctypes.windll.user32
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                try:
                    SWP_NOZORDER = 0x0004
                    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
                    user32.SetWindowPos.restype = ctypes.c_bool
                    DESIRED_WIDTH = 1100
                    DESIRED_HEIGHT = 600
                    POS_X = 100
                    POS_Y = 50
                    user32.SetWindowPos(hwnd, 0, POS_X, POS_Y, DESIRED_WIDTH, DESIRED_HEIGHT, SWP_NOZORDER)
                except Exception:
                    pass
                try:
                    kernel32.SetConsoleTitleW("[molexAudio] Audio Normalization and Booster Tool")
                except Exception:
                    try:
                        user32.SetWindowTextW(hwnd, "[molexAudio] Audio Normalization and Booster Tool")
                    except Exception:
                        pass
        except Exception:
            pass

        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

def run_interactive(cli: AudioNormalizationCLI, handler: CommandHandler, signal_handler: SignalHandler, debug: bool = False):
    """Run the interactive CLI loop."""
    while True:
        cli.display_menu()
        try:
            cli.console.print("\n\n\n")
        except Exception:
            try:
                print("\n\n\n")
            except Exception:
                pass
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
                    try:
                        install_success = any(
                            s.get("name", "").lower().startswith("install ffmpeg") and s.get("success")
                            for s in results
                        )
                        if install_success and getattr(cli, "_debug_no_ffmpeg", False):
                            try:
                                delattr(cli, "_debug_no_ffmpeg")
                            except Exception:
                                try:
                                    del cli._debug_no_ffmpeg
                                except Exception:
                                    cli._debug_no_ffmpeg = False
                    except Exception:
                        pass
                else:
                    handler.logger.info("FFmpeg setup canceled by user")
            elif choice == "2":
                handler.logger.info("Exiting...")
                break
            else:
                handler.logger.error("Invalid choice")
    signal_handler.cleanup_temp_files()


def main():
    """Main entry point for the audio normalization tool."""
    args = parse_args()
    handler = CommandHandler(max_workers=getattr(args, 'workers', None) if args else None)
    cli = AudioNormalizationCLI(handler)
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
