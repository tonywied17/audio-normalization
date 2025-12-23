import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from rich.spinner import Spinner
from rich.text import Text
from rich.panel import Panel

from processors.batch import ui as ui_mod


def test_render_group_filters_none():
    p1 = Panel(Text("a"), title="a")
    p2 = None
    p3 = Panel(Text("b"), title="b")
    g = ui_mod.render_group([p1, p2, p3])
    assert g is not None


def test_update_panel_boosting_and_live_update(monkeypatch):
    sp = Spinner("dots", "init")
    panels = [None]
    spinners = [sp]
    called = {"updated": False}

    class Live:
        def update(self, grp):
            called["updated"] = True

    live_ref = {"live": Live(), "other": 1}
    upd = ui_mod.make_update_panel(0, spinners, panels, live_ref, "file.mp4", boost_percent=12.5, audio_tracks=2)

    # boosting with last_line and error True should set red border
    upd("boosting", last_line="line", error=True)
    assert isinstance(panels[0], Panel)
    assert panels[0].border_style == "red"
    assert called["updated"] is True

    # finalizing sets magenta
    called["updated"] = False
    upd("finalizing")
    assert panels[0].border_style == "magenta"

    # success sets green
    called["updated"] = False
    upd("success")
    assert panels[0].border_style == "green"


def test_update_panel_analyzing_and_show_params_and_live_exception(monkeypatch):
    sp = Spinner("dots", "init")
    panels = [None]
    spinners = [sp]

    class LiveX:
        def update(self, grp):
            raise RuntimeError("ui fail")

    live_ref = {"live": LiveX()}
    upd = ui_mod.make_update_panel(0, spinners, panels, live_ref, "f.mp4", boost_percent=None, audio_tracks=1)

    # analyzing with last_line
    upd("analyzing", last_line="ok")
    assert panels[0].border_style == "bright_blue"

    # show_params
    upd("show_params")
    assert panels[0].border_style == "cyan"

    # normalizing
    upd("normalizing", last_line="ln")
    assert panels[0].border_style == "bright_blue"

    # finalizing and success (both set magenta)
    upd("finalizing")
    assert panels[0].border_style == "magenta"
    upd("success")
    assert panels[0].border_style == "magenta"


def test_update_panel_info_panel_exception(monkeypatch):
    sp = Spinner("dots", "init")
    panels = [None]
    spinners = [sp]
    live_ref = {}
    upd = ui_mod.make_update_panel(0, spinners, panels, live_ref, "x.mp4", boost_percent=None, audio_tracks=0)

    # monkeypatch module Panel to raise only when called with our sentinel to exercise except path
    orig_panel = ui_mod.Panel
    sentinel = object()
    def panel_wrapper(*a, **k):
        if a and a[0] is sentinel:
            raise RuntimeError("panel err")
        return orig_panel(*a, **k)
    monkeypatch.setattr(ui_mod, 'Panel', panel_wrapper)
    # calling with normal usage should work
    upd("analyzing")
    # calling with info_panel that triggers the sentinel should be caught and not raise
    upd("analyzing", info_panel=sentinel)
import sys
from pathlib import Path
from rich.spinner import Spinner
from rich.panel import Panel


def test_make_update_panel_updates_text(tmp_path):
    """Ensure update panel modifies spinner text during stages."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.batch.ui import make_update_panel, render_group

    panels = [None]
    spinners = [Spinner("dots", "pending")]
    live_ref = {}

    class DummyLive:
        def __init__(self):
            self.updated = None

        def update(self, group):
            self.updated = group

    live = DummyLive()
    live_ref["live"] = live

    update = make_update_panel(0, spinners, panels, live_ref, "file.mp4", audio_tracks=1)
    update("analyzing", last_line="Stream 1...")
    assert "Stream 1" in spinners[0].text.plain
    update("success")
    assert "Finalizing" in spinners[0].text.plain
