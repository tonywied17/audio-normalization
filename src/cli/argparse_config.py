"""
Argument parsing for audio normalization CLI.
"""

import sys
import argparse
from core.config import NORMALIZATION_PARAMS

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Audio Normalization CLI Tool")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-n", "--normalize",
        type=str,
        metavar="PATH",
        help="Path to a file or directory for normalization"
    )
    group.add_argument(
        "-b", "--boost",
        nargs='+',
        metavar=("PATH", "PERCENTAGE"),
        help="Path to a file or directory and boost percentage (e.g., 10 for +10%%, -10 for -10%%). If a directory is given, all supported files will be boosted."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build FFmpeg commands and show them without executing (useful for debugging)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Maximum number of concurrent worker threads to use for batch processing (default: auto-detect)"
    )

    parser.add_argument(
        "--I",
        type=float,
        default=NORMALIZATION_PARAMS.get('I'),
        help="Integrated loudness target (LUFS)"
    )
    parser.add_argument(
        "--TP",
        type=float,
        default=NORMALIZATION_PARAMS.get('TP'),
        help="True peak target (dBFS)"
    )
    parser.add_argument(
        "--LRA",
        type=float,
        default=NORMALIZATION_PARAMS.get('LRA'),
        help="Loudness range target (LU)"
    )

    parser.add_argument(
        "--debug-no-ffmpeg",
        action="store_true",
        help="Debug: show the UI as if FFmpeg is not installed (useful for testing the setup flow)"
    )

    args = parser.parse_args()

    if args.boost and any(x is not None for x in [args.I, args.TP, args.LRA]):
        print("Error: Normalization parameters cannot be used with --boost")
        sys.exit(1)

    if args.normalize is None and any(x is not None for x in [args.I, args.TP, args.LRA]):
        print("Error: Normalization parameters require --normalize")
        sys.exit(1)

    if args.boost:
        if len(args.boost) != 2:
            print("Error: --boost requires a path and a percentage (e.g., --boost <file_or_dir> <percent>)")
            sys.exit(1)
        try:
            float(args.boost[1])
        except ValueError:
            print("Error: Boost percentage must be a number.")
            sys.exit(1)

    if len(sys.argv) == 1:
        return None

    return args
