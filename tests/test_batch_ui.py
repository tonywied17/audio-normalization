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
