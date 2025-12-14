"""
CLI UI logic for Audio Normalization Tool.
"""
from rich.console import Console, Group
from rich.table import Table
from rich import box
from src.config import NORMALIZATION_PARAMS, AUDIO_CODEC, AUDIO_BITRATE, SUPPORTED_EXTENSIONS, LOG_DIR, LOG_FILE, VERSION
from rich.panel import Panel
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
        import platform
        import os
        import shutil
        config_title_style = "dim wheat1"

        # Normalization params panel
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

        # Supported extensions panel
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

        # Logging panel
        log_table = Table.grid(padding=(0,1))
        log_table.add_column(justify="right", style="bold grey50")
        log_table.add_column(justify="left", style="white")
        log_table.add_row("Log Directory", f"[white]{LOG_DIR}[/white]")
        log_table.add_row("Log File", f"[white]{LOG_FILE}[/white]")
        ffmpeg_log_path = "ffmpeg_debug.log"
        log_table.add_row("FFmpeg Debug Log", f"[white]{ffmpeg_log_path}[/white]")
        log_panel = Align.center(
            Group(
                Align.center(Text("Logging", style=config_title_style)),
                Padding(Align.center(log_table, vertical="top"), (1, 4)),
            ),
            vertical="top",
        )

        # Audio output panel
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

        # System info panel
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
        menu_table.add_row("[1]", "[white][bold green]Boost[/bold green] Audio Track(s) for a File or Directory[/white]")
        menu_table.add_row("[2]", "[white][bold bright_blue]Normalize[/bold bright_blue] Audio Track(s) for a File or Directory[/white]")
        menu_table.add_row("[3]", "[white][bold red]Exit[/bold red][/white]")

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
        if not results:
            return
        table = Table(
            title="📋 Processing Results",
            title_style="bold green",
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE,
            expand=True,
            style="cyan"
        )
        table.add_column("File", style="dim cyan")
        table.add_column("Task", justify="center", style="italic magenta")
        table.add_column("Status", justify="center", style="bold")
        for result in results:
            status_color = "green" if result["status"] == "Success" else "red"
            table.add_row(
                result["file"],
                result["task"],
                f"[{status_color}]{result['status']}[/{status_color}]"
            )
        self.console.print(table)
