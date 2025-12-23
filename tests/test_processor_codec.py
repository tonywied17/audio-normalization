import sys
from pathlib import Path
import os
import json

# Ensure src is importable
repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from processors.audio import processor as proc_module
from processors.audio.processor import AudioProcessor
from processors.audio.utils import create_temp_file
from core.config import AUDIO_CODEC, FALLBACK_AUDIO_CODEC
from core.signal_handler import SignalHandler


def _make_loudnorm_json():
    return json.dumps({
        "input_i": -23.0,
        "input_tp": -1.0,
        "input_lra": 5,
        "input_thresh": -34,
        "target_offset": 0
    })


class DummyResult:
    def __init__(self, stdout='', stderr=''):
        self.stdout = stdout
        self.stderr = stderr


def test_normalize_uses_inherited_codec_and_writes_metadata(monkeypatch, tmp_path):
    media = tmp_path / "file.mp4"
    media.write_text("x")

    # prepare temp output so processor can rename
    temp = create_temp_file(str(media))
    Path(temp).write_text("out")

    # fake probe to return codec_name and tags
    monkeypatch.setattr(proc_module, "get_audio_streams", lambda path, logger=None: [{"channels": 2, "sample_rate": 48000, "tags": {"title": "OrigTitle"}, "codec_name": "aac"}])
    monkeypatch.setattr(proc_module, "get_video_streams", lambda path: [])

    recorded = {"cmds": []}

    def fake_run(cmd, capture_output=True):
        # analyze command: contains loudnorm -> return stderr with JSON
        cmd_str = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        # Distinguish the analyze probe (uses -af loudnorm ... -f null -)
        # from the final ffmpeg run (uses -filter_complex).
        if "loudnorm" in cmd_str and "-filter_complex" not in cmd_str:
            return DummyResult(stdout='', stderr=_make_loudnorm_json())
        # final ffmpeg call: record command
        recorded["cmds"].append(cmd)
        return DummyResult(stdout='', stderr='')

    monkeypatch.setattr(proc_module, "run_command", fake_run)
    # also capture popen-based invocations (if any)
    class DummyProc:
        def __init__(self, cmd):
            self.command = cmd
            self.stderr = iter([])
            self.pid = 1
            self.returncode = 0
        def wait(self):
            self.returncode = 0

    def fake_popen(cmd):
        recorded["cmds"].append(cmd)
        return DummyProc(cmd)

    monkeypatch.setattr(proc_module, "popen", fake_popen)
    monkeypatch.setattr(SignalHandler, "unregister_temp_file", staticmethod(lambda p: None))

    ap = AudioProcessor()
    result = ap.normalize_audio(str(media), show_ui=False)
    assert result is not None
    assert recorded["cmds"], "ffmpeg command not recorded"
    ffmpeg_cmd = recorded["cmds"][0]
    # when AUDIO_CODEC == 'inherit' we expect -c:a:0 <codec>
    assert any(arg.startswith("-c:a") for arg in ffmpeg_cmd), f"no -c:a in {ffmpeg_cmd}"
    # metadata: title and handler_name should be present
    joined = ' '.join(ffmpeg_cmd)
    assert "handler_name" in joined or "title=" in joined


def test_boost_uses_inherited_codec_and_includes_handlername(monkeypatch, tmp_path):
    media = tmp_path / "m.mp4"
    media.write_text("y")

    temp = create_temp_file(str(media))
    Path(temp).write_text("out")

    monkeypatch.setattr(proc_module, "get_audio_streams", lambda path, logger=None: [{"channels": 2, "sample_rate": 48000, "tags": {"title": "OrigTrack"}, "codec_name": "aac"}])
    monkeypatch.setattr(proc_module, "get_video_streams", lambda path: [])

    recorded = {"cmds": []}

    def fake_run(cmd, capture_output=True):
        cmd_str = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        # record final ffmpeg invocation
        recorded["cmds"].append(cmd)
        return DummyResult(stdout='', stderr='')

    monkeypatch.setattr(proc_module, "run_command", fake_run)
    # capture popen invocations as well
    class DummyProc2:
        def __init__(self, cmd):
            self.command = cmd
            self.stderr = iter(["frame= 0 fps=0.0 size=0kB time=00:00:00.00"])
            self.pid = 2
            self.returncode = 0
        def wait(self):
            self.returncode = 0

    def fake_popen2(cmd):
        recorded["cmds"].append(cmd)
        return DummyProc2(cmd)

    monkeypatch.setattr(proc_module, "popen", fake_popen2)
    monkeypatch.setattr(SignalHandler, "unregister_temp_file", staticmethod(lambda p: None))

    ap = AudioProcessor()
    out = ap.boost_audio(str(media), 5.0, show_ui=False, dry_run=False)
    assert out is not None
    assert recorded["cmds"]
    ffmpeg_cmd = recorded["cmds"][0]
    joined = ' '.join(ffmpeg_cmd)
    assert "handler_name" in joined or "title=" in joined
    assert any(arg.startswith("-c:a") for arg in ffmpeg_cmd), "expected per-stream -c:a in ffmpeg args"
