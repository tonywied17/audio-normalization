import sys
from pathlib import Path
import os


class FakeProc:
    def __init__(self, command, lines=None, returncode=0):
        self.command = command
        self._lines = list(lines or [])
        self.stderr = iter(self._lines)
        self.pid = 99999
        self.returncode = None
        self._rc = returncode

    def wait(self):
        try:
            last = self.command[-1]
            if isinstance(last, str) and os.path.splitext(last)[1]:
                with open(last, "w", encoding="utf-8"):
                    pass
        except Exception:
            pass
        self.returncode = self._rc


def test_boost_streaming(monkeypatch, tmp_path):
    """Boosting pipeline emits progress and completes without error."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio import processor as proc_module
    from core.signal_handler import SignalHandler

    media = tmp_path / "m.mp4"
    media.write_text("x")

    monkeypatch.setattr(proc_module, "get_audio_streams", lambda path, logger=None: [{"channels": 2, "sample_rate": 48000, "tags": {}}])
    monkeypatch.setattr(proc_module, "get_video_streams", lambda path: [])

    def fake_popen(cmd):
        cmd_str = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        if "volume" in cmd_str or "aformat" in cmd_str:
            return FakeProc(cmd, lines=["frame= 0 fps=0.0 size=0kB time=00:00:00.00"], returncode=0)
        return FakeProc(cmd, lines=["frame= 100 fps=25 ..."], returncode=0)

    monkeypatch.setattr('processors.audio.processor.popen', fake_popen)
    monkeypatch.setattr(SignalHandler, "register_child_pid", staticmethod(lambda pid: None))
    monkeypatch.setattr(SignalHandler, "unregister_child_pid", staticmethod(lambda pid: None))

    seen = []

    def cb(stage, last_line=None, **kwargs):
        seen.append((stage, last_line))

    from processors.audio.processor import AudioProcessor
    ap = AudioProcessor()
    out = ap.boost_audio(str(media), 5.0, show_ui=False, dry_run=False, progress_callback=cb)
    assert out is not None
    assert any(s for s in seen if s[0] == "boosting")
