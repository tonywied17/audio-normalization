"""
CLI module for the Audio Normalization and Boosting.
"""

import platform
import os
import shutil
from rich.console import Console, Group
from rich.table import Table
from rich import box
from core.config import NORMALIZATION_PARAMS, AUDIO_CODEC, AUDIO_BITRATE, SUPPORTED_EXTENSIONS, LOG_DIR, LOG_FILE, LOG_FFMPEG_DEBUG, VERSION
from rich.padding import Padding
from rich.align import Align
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns


class AudioNormalizationCLI:
    def __init__(self, command_handler):
        self.console = Console()
        self.command_handler = command_handler

    def display_menu(self):
        """Display the main menu with configuration panels."""
        config_title_style = "dim wheat1"

        try:
            ffmpeg_path = shutil.which("ffmpeg")
        except Exception:
            ffmpeg_path = None
        if getattr(self, "_debug_no_ffmpeg", False):
            ffmpeg_path = None
        self.ffmpeg_found = bool(ffmpeg_path)
        if ffmpeg_path:
            ffmpeg_status = "[dim green]Found[/dim green]"
            ffmpeg_link = ""
        else:
            ffmpeg_status = "[red]Not found[/red]"
            ffmpeg_link = " — [link=https://ffmpeg.org/download.html]Download FFmpeg[/link]"

        #! Normalization params panel
        norm_table = Table.grid(padding=(0,1))
        norm_table.add_column(justify="right", style="bold grey50")
        norm_table.add_column(justify="left", style="white")
        norm_table.add_row("Integrated Loudness (I)", f"[white]{NORMALIZATION_PARAMS['I']} LUFS[/white]")
        norm_table.add_row("True Peak (TP)", f"[white]{NORMALIZATION_PARAMS['TP']} dBFS[/white]")
        norm_table.add_row("Loudness Range (LRA)", f"[white]{NORMALIZATION_PARAMS['LRA']} LU[/white]")
        norm_panel = Align.center(
            Group(
                Align.center(Text("Normalization Params", style=config_title_style)),
                Padding(Align.center(norm_table, vertical="top"), (1, 4)),
            ),
            vertical="top",
        )

        #! Supported extensions panel
        ext_table = Table.grid(padding=(0,1))
        ext_table.add_column(justify="left", style="white")
        ext_table.add_row(", ".join([f"[white]{ext}[/white]" for ext in sorted(list(SUPPORTED_EXTENSIONS))]))
        ext_panel = Align.center(
            Group(
                Align.center(Text("Supported Extensions", style=config_title_style)),
                Padding(Align.center(ext_table, vertical="top"), (1, 4)),
            ),
            vertical="top",
        )

        #! Logging panel
        log_table = Table.grid(padding=(0,1))
        log_table.add_column(justify="right", style="bold grey50")
        log_table.add_column(justify="left", style="white")
        log_table.add_row("Log Directory", f"[white]{LOG_DIR}[/white]")
        log_table.add_row("Log File", f"[white]{LOG_FILE}[/white]")
        log_table.add_row("FFmpeg Debug Log", f"[white]{LOG_FFMPEG_DEBUG}[/white]")
        log_table.add_row("FFmpeg", f"{ffmpeg_status}{ffmpeg_link}")
        log_panel = Align.center(
            Group(
                Align.center(Text("Logging", style=config_title_style)),
                Padding(Align.center(log_table, vertical="top"), (1, 4)),
            ),
            vertical="top",
        )

        #! Audio output panel
        audio_table = Table.grid(padding=(0,1))
        audio_table.add_column(justify="right", style="bold grey50")
        audio_table.add_column(justify="left", style="white")
        audio_table.add_row("Audio Codec", f"[white]{AUDIO_CODEC}[/white]")
        audio_table.add_row("Audio Bitrate", f"[white]{AUDIO_BITRATE}[/white]")
        audio_panel = Align.center(
            Group(
                Align.center(Text("Audio Output", style=config_title_style)),
                Padding(Align.center(audio_table, vertical="top"), (1, 4)),
            ),
            vertical="top",
        )

        #! System info panel
        cpu = platform.processor() or platform.machine() or "Unknown"
        core_count = os.cpu_count() or "Unknown"
        sys_table = Table.grid(padding=(0,1))
        sys_table.add_column(justify="right", style="bold grey50")
        sys_table.add_column(justify="left", style="white")
        sys_table.add_row("CPU", f"[white]{cpu}[/white]")
        sys_table.add_row("Cores", f"[white]{core_count}[/white]")
        sys_panel = Align.center(
            Group(
                Align.center(Text("System Info", style=config_title_style)),
                Padding(Align.center(sys_table, vertical="top"), (1, 4)),
            ),
            vertical="top",
        )

        config_panels = [sys_panel, norm_panel, audio_panel, log_panel, ext_panel]
        config_group = Align.center(
            Columns(config_panels, align="center", expand=True, equal=True, width=None, padding=(0, 2)),
            vertical="top",
        )

        menu_table = Table(
            box=box.ROUNDED,
            pad_edge=True,
            show_lines=True,
            header_style="bold magenta",
            style="bold white",
            expand=True,
            border_style="dim white",
        )
        menu_table.add_column("[bold grey42]Option[/bold grey42]", justify="center", style="wheat1", width=10)
        menu_table.add_column("[bold grey42]Description[/bold grey42]", justify="left", style="white")
        if self.ffmpeg_found:
            menu_table.add_row("[1]", "[white][bold green]Boost[/bold green] Audio Track(s) for a File or Directory[/white]")
            menu_table.add_row("[2]", "[white][bold bright_blue]Normalize[/bold bright_blue] Audio Track(s) for a File or Directory[/white]")
            menu_table.add_row("[3]", "[white][bold red]Exit[/bold red][/white]")
        else:
            menu_table.add_row("[1]", "[white][bold yellow]Setup FFmpeg[/bold yellow] Install Scoop and FFmpeg (Windows only)[/white]")
            menu_table.add_row("[2]", "[white][bold red]Exit[/bold red][/white]")

        title_text = Text("🎵 Audio Normalization CLI", style="bold bright_white", justify="center")
        subtitle = Text.assemble(("by molex | ", "dim"), (f"v{VERSION}", "dim"))
        subtitle.justify = "center"

        terminal_cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        menu_width = min(80, max(40, int(terminal_cols * 0.35)))
        layout = Layout()
        layout.split_column(
            Layout(Align.center(title_text), name="title", size=3),
            Layout(Align.center(subtitle), name="subtitle", size=2),
            Layout(name="main", ratio=1)
        )

        layout["main"].split_row(
            Layout(Align.left(menu_table, vertical="top"), name="menu", size=menu_width),
            Layout(config_group, name="config")
        )
        self.console.print(layout)


    def display_results(self, results: list):
        """Display processing results using a panel-per-file layout with a summary."""
        if not results:
            self.console.print("[bold yellow]No results to display[/bold yellow]")
            return
        total = len(results)
        succeeded = sum(1 for r in results if r.get("status") == "Success")
        failed = total - succeeded

        summary = Text.assemble((f"{succeeded}", "bold green"), (" succeeded ", "dim"), ("• ", "dim"), (f"{failed}", "bold red"), (" failed", "dim"))
        self.console.rule("[bold cyan]Processing Complete[/bold cyan]")
        self.console.print(Align.center(summary))

        panels = []
        for r in results:
            file_name = os.path.basename(r.get("file", ""))
            task = r.get("task", "")
            status = r.get("status", "")
            status_color = "green" if status == "Success" else "red"
            message = r.get("message", "")

            body = Text()
            body.append(f"{task}\n", style="bold white")
            body.append(f"[{status_color}]{status}[/{status_color}]\n")
            if message:
                body.append("\n")
                body.append(message, style="dim")

            panels.append(Panel(body, title=file_name, border_style=status_color, padding=(1,2)))

        self.console.print(Columns(panels, equal=True, expand=True))
