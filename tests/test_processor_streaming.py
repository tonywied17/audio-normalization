import sys
from pathlib import Path
import os
import json


class FakeProc:
    def __init__(self, command, lines=None, returncode=0):
        self.command = command
        self._lines = list(lines or [])
        self.stderr = iter(self._lines)
        self.pid = 12345
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


def test_normalize_streaming(tmp_path, monkeypatch):
    """Normalization pipeline analyzes then encodes, reporting progress."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio import processor as proc_module
    from processors.audio.processor import AudioProcessor
    from core.signal_handler import SignalHandler

    media_file = tmp_path / "sample.mp4"
    media_file.write_text("dummy")

    monkeypatch.setattr(proc_module, "get_audio_streams", lambda path, logger=None: [{"channels": 2, "sample_rate": 48000, "tags": {}}])
    monkeypatch.setattr(proc_module, "get_video_streams", lambda path: [])

    loudnorm_json = json.dumps({"input_i": -23.0, "input_tp": -1.0, "input_lra": 5, "input_thresh": -34, "target_offset": 0})
    analyze_lines = ["ffmpeg version ...", "[Parsed_loudnorm_0 @ 0x...] some info", loudnorm_json]

    def fake_popen(cmd):
        cmd_str = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        if "loudnorm" in cmd_str:
            return FakeProc(cmd, lines=analyze_lines, returncode=0)
        else:
            return FakeProc(cmd, lines=["frame= 100 fps=25 ..."], returncode=0)

    monkeypatch.setattr('processors.audio.processor.popen', fake_popen)
    monkeypatch.setattr(SignalHandler, "register_child_pid", staticmethod(lambda pid: None))
    monkeypatch.setattr(SignalHandler, "unregister_child_pid", staticmethod(lambda pid: None))

    seen = []

    def progress_cb(stage, last_line=None, **kwargs):
        seen.append((stage, last_line))

    ap = AudioProcessor()

    result = ap.normalize_audio(str(media_file), show_ui=False, progress_callback=progress_cb)
    assert result is not None
    assert any(s for s in seen if s[0] == "analyzing")
    assert any(s for s in seen if s[0] in ("normalizing", "analyzing"))
