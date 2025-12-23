import sys
from pathlib import Path
import os
import json

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from processors.audio import processor as proc_module
from processors.audio.processor import AudioProcessor
from core.signal_handler import SignalHandler


class DummyResult:
    def __init__(self, stdout='', stderr=''):
        self.stdout = stdout
        self.stderr = stderr


class FakeProc:
    def __init__(self, cmd, lines=None, returncode=0):
        self.command = cmd
        self.stderr = iter(lines or [])
        self.pid = 222
        self.returncode = returncode
    def wait(self):
        return self.returncode


def _make_loudnorm_json():
    return json.dumps({
        "input_i": -23.0,
        "input_tp": -1.0,
        "input_lra": 5,
        "input_thresh": -34,
        "target_offset": 0
    })


def test_normalize_no_audio_returns_none(monkeypatch, tmp_path):
    media = tmp_path / "noaudio.mp4"
    media.write_text('x')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [])
    ap = AudioProcessor()
    out = ap.normalize_audio(str(media))
    assert out is None


def test_normalize_global_codec_calls_run_command_with_global_codec(monkeypatch, tmp_path):
    media = tmp_path / "one.mp4"
    media.write_text('c')

    # one audio stream with a title
    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{"title":"T1"}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [{"index":0}])

    captured = {}

    def fake_run(cmd, capture_output=True):
        cmd_str = ' '.join(cmd if isinstance(cmd, list) else cmd)
        if 'loudnorm' in cmd_str and '-filter_complex' not in cmd_str:
            return DummyResult(stdout='', stderr=_make_loudnorm_json())
        # final ffmpeg invocation
        captured['cmd'] = cmd
        # create expected temp output so processor can rename it
        try:
            tmp = proc_module.create_temp_file(str(media))
            Path(tmp).write_text('temp')
        except Exception:
            pass
        return DummyResult(stdout='', stderr='')

    # enforce global codec branch
    monkeypatch.setattr(proc_module, 'AUDIO_CODEC', 'aac', raising=False)
    monkeypatch.setattr(proc_module, 'run_command', fake_run)
    monkeypatch.setattr(SignalHandler, 'unregister_temp_file', staticmethod(lambda p: None))

    ap = AudioProcessor()
    out = ap.normalize_audio(str(media), show_ui=False)
    assert out == str(media)
    final_cmd = captured.get('cmd')
    assert final_cmd is not None
    assert '-c:a' in final_cmd
    assert 'aac' in final_cmd
    assert '-c:s' in final_cmd and 'copy' in final_cmd


def test_boost_show_ui_max_channels_and_sample_rate_fallback(monkeypatch, tmp_path):
    media = tmp_path / "bshow.mp4"
    media.write_text('d')

    # audio stream with bad sample_rate and zero channels to trigger fallbacks
    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":0, "sample_rate":"bad", "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    captured = {}

    def fake_popen(cmd):
        # capture the ffmpeg command
        captured['cmd'] = cmd
        # create expected temp output so processor can rename it
        try:
            tmp = proc_module.create_temp_file(str(media))
            Path(tmp).write_text('temp')
        except Exception:
            pass
        # simulate ffmpeg stderr lines then success
        return FakeProc(cmd, lines=["info line", "done"], returncode=0)

    monkeypatch.setattr(proc_module, 'popen', fake_popen)
    monkeypatch.setattr(SignalHandler, 'register_child_pid', staticmethod(lambda pid: None))
    monkeypatch.setattr(SignalHandler, 'unregister_child_pid', staticmethod(lambda pid: None))
    monkeypatch.setattr(SignalHandler, 'unregister_temp_file', staticmethod(lambda p: None))

    ap = AudioProcessor()
    out = ap.boost_audio(str(media), 12.5, show_ui=True)
    assert out == str(media)
    cmd = captured.get('cmd')
    assert cmd is not None
    cmd_str = ' '.join(cmd)
    # max_channels fallback to 2 should result in -ac 2 or -ac 2 in args
    assert '-ac' in cmd_str or '-ac' in cmd
    # sample_rate fallback to 48000 appears in filter_complex
    assert 'sample_rates=48000' in cmd_str


def test_normalize_with_progress_callback_and_popen_success(monkeypatch, tmp_path):
    media = tmp_path / "np.mp4"
    media.write_text('z')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    captured = {}

    def fake_popen(cmd):
        cmd_str = ' '.join(cmd if isinstance(cmd, list) else cmd)
        # analysis call
        if 'loudnorm' in cmd_str and '-filter_complex' not in cmd_str:
            return FakeProc(cmd, lines=[_make_loudnorm_json()], returncode=0)
        # final ffmpeg: create temp output and return success
        captured['cmd'] = cmd
        try:
            tmp = proc_module.create_temp_file(str(media))
            Path(tmp).write_text('temp')
        except Exception:
            pass
        return FakeProc(cmd, lines=["final"], returncode=0)

    monkeypatch.setattr(proc_module, 'popen', fake_popen)
    monkeypatch.setattr(proc_module.SignalHandler, 'register_child_pid', staticmethod(lambda pid: None))
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_child_pid', staticmethod(lambda pid: None))
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_temp_file', staticmethod(lambda p: None))

    # simple progress callback that records calls
    progress_calls = []
    def progress_cb(stage, last_line=None, **kwargs):
        progress_calls.append((stage, last_line))

    ap = AudioProcessor()
    out = ap.normalize_audio(str(media), show_ui=False, progress_callback=progress_cb)
    assert out == str(media)
    assert any(c[0] == 'analyzing' for c in progress_calls)
    assert 'cmd' in captured
