"""UI helper utilities for batch processing (panels, spinners, update closures)."""
from typing import Callable, List, Any
from rich.text import Text
from rich.panel import Panel
from rich.spinner import Spinner
from rich.console import Group


def render_group(panels: List[Panel]) -> Group:
    return Group(*(p for p in panels if p is not None))


def make_update_panel(idx: int, spinners: List[Spinner], panels: List[Panel], live_ref: dict, file: str, *, boost_percent: float = None, audio_tracks: int = 0) -> Callable:
    """Return an `update_panel(stage, last_line=None, error=False, info_panel=None)` function for the given index."""
    def update_panel(stage: str, last_line: str = None, error: bool = False, info_panel: Any = None):
        if boost_percent is not None:
            # boost UI
            if stage == "boosting":
                text = f"[bold green]Boosting {audio_tracks} audio track{'s' if audio_tracks != 1 else ''} by {boost_percent}%...[/bold green]"
                if last_line:
                    text += f"\n{last_line}"
                spinners[idx].text = Text.from_markup(text)
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="red" if error else "green")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
            elif stage == "finalizing":
                spinners[idx].text = Text.from_markup("[green]Finalizing...[/green]")
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="magenta")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
            elif stage == "success":
                spinners[idx].text = Text.from_markup("[bold green]Boost complete[/bold green]")
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="green")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
        else:
            # normalize UI
            if stage == "analyzing":
                text = f"[bold bright_blue]Analyzing {audio_tracks} audio track{'s' if audio_tracks != 1 else ''}...[/bold bright_blue]"
                if last_line:
                    text += f"\n{last_line}"
                spinners[idx].text = Text.from_markup(text)
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="bright_blue")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
            elif stage == "show_params":
                spinners[idx].text = Text.from_markup("[bold cyan]Analysis complete![/bold cyan]")
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="cyan")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
            elif stage == "normalizing":
                text = "[bold bright_blue]Normalizing...[/bold bright_blue]"
                if last_line:
                    text += f"\n{last_line}"
                spinners[idx].text = Text.from_markup(text)
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="bright_blue")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
            elif stage == "finalizing":
                spinners[idx].text = Text.from_markup("[green]Finalizing...[/green]")
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="magenta")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
            elif stage == "success":
                spinners[idx].text = Text.from_markup("[green]Finalizing...[/green]")
                panels[idx] = Panel(spinners[idx], title=f"{file}", border_style="magenta")
                if live_ref.get("live"):
                    try:
                        live_ref["live"].update(render_group(panels))
                    except Exception:
                        pass
        # info_panel handling for normalize path
        if info_panel is not None:
            try:
                panels[idx] = Panel(info_panel, title=f"{file}")
            except Exception:
                pass

    return update_panel
