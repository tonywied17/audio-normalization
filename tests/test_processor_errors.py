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


class FakeProc:
    def __init__(self, cmd, lines=None, returncode=0):
        self.command = cmd
        self.stderr = iter(lines or [])
        self.pid = 111
        self.returncode = returncode
    def wait(self):
        self.returncode = self.returncode


def test_normalize_final_run_failure_cleans_temp(monkeypatch, tmp_path):
    media = tmp_path / "video.mp4"
    media.write_text("x")

    # temp file path
    temp = create_temp_file(str(media))
    Path(temp).write_text("out")

    # audio and video streams
    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [{"index":0}])

    # analyze returns loudnorm JSON
    def fake_run(cmd, capture_output=True):
        cmd_str = ' '.join(cmd)
        if 'loudnorm' in cmd_str and '-filter_complex' not in cmd_str:
            return DummyResult(stdout='', stderr=_make_loudnorm_json())
        # simulate failure on final ffmpeg
        raise RuntimeError('ffmpeg failed')

    monkeypatch.setattr(proc_module, 'run_command', fake_run)
    monkeypatch.setattr(SignalHandler, 'unregister_temp_file', staticmethod(lambda p: None))

    ap = AudioProcessor()
    res = ap.normalize_audio(str(media), show_ui=False)
    assert res is None
    assert not os.path.exists(temp)


def test_normalize_progress_popen_nonzero_cleanup(monkeypatch, tmp_path):
    media = tmp_path / "video2.mp4"
    media.write_text('x')

    temp = create_temp_file(str(media))
    Path(temp).write_text('out')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # popen for analyze should return lines containing loudnorm JSON
    def fake_popen(cmd):
        cmd_str = ' '.join(cmd)
        if 'loudnorm' in cmd_str and '-filter_complex' not in cmd_str:
            return FakeProc(cmd, lines=["info", _make_loudnorm_json()], returncode=0)
        # final ffmpeg returns non-zero
        return FakeProc(cmd, lines=["err"], returncode=1)

    monkeypatch.setattr(proc_module, 'popen', fake_popen)
    monkeypatch.setattr(SignalHandler, 'register_child_pid', staticmethod(lambda pid: None))
    monkeypatch.setattr(SignalHandler, 'unregister_child_pid', staticmethod(lambda pid: None))
    monkeypatch.setattr(SignalHandler, 'unregister_temp_file', staticmethod(lambda p: None))

    ap = AudioProcessor()
    res = ap.normalize_audio(str(media), show_ui=False, progress_callback=lambda *a, **k: None)
    assert res is None
    assert not os.path.exists(temp)


def test_boost_dry_run_with_progress_returns_path(monkeypatch, tmp_path):
    media = tmp_path / "m.mp4"
    media.write_text('y')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    ap = AudioProcessor()
    out = ap.boost_audio(str(media), 10.0, show_ui=False, dry_run=True, progress_callback=lambda *a, **k: None)
    assert out == str(media)


def test_boost_run_command_exception_cleans_temp(monkeypatch, tmp_path):
    media = tmp_path / 'b.mp4'
    media.write_text('z')

    temp = create_temp_file(str(media))
    Path(temp).write_text('tmp')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    def fake_run(cmd, capture_output=True):
        # simulate exception in run_command
        raise RuntimeError('boom')

    monkeypatch.setattr(proc_module, 'run_command', fake_run)
    monkeypatch.setattr(SignalHandler, 'unregister_temp_file', staticmethod(lambda p: None))

    ap = AudioProcessor()
    res = ap.boost_audio(str(media), 5.0, show_ui=False, dry_run=False)
    assert res is None
    assert not os.path.exists(temp)
