"""
CLI UI logic for Audio Normalization Tool.
"""
from rich.console import Console
from rich.table import Table
from rich import box
from src.config import NORMALIZATION_PARAMS, AUDIO_CODEC, AUDIO_BITRATE, SUPPORTED_EXTENSIONS, LOG_DIR, LOG_FILE, VERSION
from rich.panel import Panel
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
        config_color = "bright_blue"
        config_title_style = "bold bright_blue"
        config_border_style = config_color

        # Normalization params panel
        norm_table = Table.grid(padding=(0,1))
        norm_table.add_column(justify="right", style="bold cyan")
        norm_table.add_column(justify="left", style="white")
        norm_table.add_row("Integrated Loudness (I)", f"[bright_white]{NORMALIZATION_PARAMS['I']} LUFS[/bright_white]")
        norm_table.add_row("True Peak (TP)", f"[bright_white]{NORMALIZATION_PARAMS['TP']} dBFS[/bright_white]")
        norm_table.add_row("Loudness Range (LRA)", f"[bright_white]{NORMALIZATION_PARAMS['LRA']} LU[/bright_white]")
        norm_panel = Panel(
            Align.left(norm_table),
            title=f"[{config_title_style}]Normalization Params[/{config_title_style}]",
            border_style=config_border_style,
            padding=(1,2),
            expand=True,
        )

        # Supported extensions panel
        ext_table = Table.grid(padding=(0,1))
        ext_table.add_column(justify="left", style="bright_white")
        ext_table.add_row(", ".join([f"[bright_white]{ext}[/bright_white]" for ext in sorted(list(SUPPORTED_EXTENSIONS))]))
        ext_panel = Panel(
            Align.left(ext_table),
            title=f"[{config_title_style}]Supported Extensions[/{config_title_style}]",
            border_style=config_border_style,
            padding=(1,2),
            expand=True,
        )

        # Logging panel
        log_table = Table.grid(padding=(0,1))
        log_table.add_column(justify="right", style="bold cyan")
        log_table.add_column(justify="left", style="white")
        log_table.add_row("Log Directory", f"[bright_white]{LOG_DIR}[/bright_white]")
        log_table.add_row("Log File", f"[bright_white]{LOG_FILE}[/bright_white]")
        log_panel = Panel(
            Align.left(log_table),
            title=f"[{config_title_style}]Logging[/{config_title_style}]",
            border_style=config_border_style,
            padding=(1,2),
            expand=True,
        )

        # Audio output panel
        audio_table = Table.grid(padding=(0,1))
        audio_table.add_column(justify="right", style="bold cyan")
        audio_table.add_column(justify="left", style="white")
        audio_table.add_row("Audio Codec", f"[bright_white]{AUDIO_CODEC}[/bright_white]")
        audio_table.add_row("Audio Bitrate", f"[bright_white]{AUDIO_BITRATE}[/bright_white]")
        audio_panel = Panel(
            Align.left(audio_table),
            title=f"[{config_title_style}]Audio Output[/{config_title_style}]",
            border_style=config_border_style,
            padding=(1,2),
            expand=True,
        )

        # System info panel
        cpu = platform.processor() or platform.machine() or "Unknown"
        core_count = os.cpu_count() or "Unknown"
        sys_table = Table.grid(padding=(0,1))
        sys_table.add_column(justify="right", style="bold cyan")
        sys_table.add_column(justify="left", style="white")
        sys_table.add_row("CPU", f"[bright_white]{cpu}[/bright_white]")
        sys_table.add_row("Cores", f"[bright_white]{core_count}[/bright_white]")
        sys_panel = Panel(
            Align.left(sys_table),
            title=f"[{config_title_style}]System Info[/{config_title_style}]",
            border_style=config_border_style,
            padding=(1,2),
            expand=True,
        )

        config_panels = [norm_panel, audio_panel, ext_panel, log_panel, sys_panel]
        config_group = Panel(
            Align.left(
                Columns(config_panels, align="left", expand=True, equal=True, width=None)
            ),
            title="[bold bright_blue]Configuration[/bold bright_blue]",
            border_style="bright_blue",
            padding=(1,2),
            expand=True,
        )

        menu_table = Table(
            box=box.ROUNDED,
            pad_edge=True,
            show_lines=True,
            header_style="bold magenta",
            style="bold white",
            expand=True,
            border_style="bright_cyan"
        )
        menu_table.add_column("[bold cyan]Option[/bold cyan]", justify="center", style="bold cyan", width=10)
        menu_table.add_column("[bold cyan]Description[/bold cyan]", justify="left", style="white")
        menu_table.add_row("[1]", "[white]Apply [bold green]Simple Audio Boost[/bold green] to a File or Directory[/white]")
        menu_table.add_row("[2]", "[white]Normalize [bold cyan]Audio Track(s)[/bold cyan] for a File or Directory[/white]")
        menu_table.add_row("[3]", "[white][bold red]Exit[/bold red][/white]")

        title_text = Text("🎵 Audio Normalization CLI 🎥", style="bold cornsilk1", justify="center")
        subtitle = Text.assemble(("by molex | ", "dim"), (f"v{VERSION}", "dim"))
        subtitle.justify = "center"

        layout = Layout()
        layout.split_column(
            Layout(Align.center(title_text), name="title", size=1),
            Layout(Align.center(subtitle), name="subtitle", size=1),
            Layout(name="main", ratio=1)
        )
        layout["main"].split_row(
            Layout(Panel(menu_table, title="[bold cyan]Menu[/bold cyan]", border_style="bright_cyan", padding=(1,2), expand=True), name="menu", size=48),
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
