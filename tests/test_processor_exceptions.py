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


class FakeProc:
    def __init__(self, cmd, lines=None, returncode=0):
        self.command = cmd
        self.stderr = iter(lines or [])
        self.pid = 333
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


def test_boost_show_ui_failure_triggers_cleanup_and_logs(monkeypatch, tmp_path):
    media = tmp_path / "efail.mp4"
    media.write_text('x')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # popen returns a process that has returncode != 0
    def fake_popen(cmd):
        # create temp file expected by processor
        try:
            tmp = proc_module.create_temp_file(str(media))
            Path(tmp).write_text('tmp')
        except Exception:
            pass
        return FakeProc(cmd, lines=["err"], returncode=2)

    monkeypatch.setattr(proc_module, 'popen', fake_popen)

    # make unregister_temp_file raise to hit except branch
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_temp_file', staticmethod(lambda p: (_ for _ in ()).throw(Exception('uerr'))))

    # make os.remove raise to hit its except
    monkeypatch.setattr(os, 'remove', lambda p: (_ for _ in ()).throw(Exception('rmerr')))

    # capture logger.error calls
    captured = []
    ap = AudioProcessor()
    ap.logger.error = lambda msg: captured.append(msg)
    ap.logger.log_ffmpeg = lambda *a, **k: None

    res = ap.boost_audio(str(media), 5.0, show_ui=True)
    assert res is None
    assert any('Boost failed' in c or 'Boost failed for' in c for c in captured)

    # cleanup temp if still present
    try:
        tmp = proc_module.create_temp_file(str(media))
        if os.path.exists(tmp):
            # restore os.remove and remove
            monkeypatch.setattr(os, 'remove', os.remove)
            os.remove(tmp)
    except Exception:
        pass


def test_normalize_popen_final_nonzero_logs_and_cleans(monkeypatch, tmp_path):
    media = tmp_path / "nfail.mp4"
    media.write_text('y')

    # one audio stream
    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # analysis popen returns loudnorm json, final returns non-zero
    def fake_popen(cmd):
        cmd_str = ' '.join(cmd if isinstance(cmd, list) else cmd)
        if 'loudnorm' in cmd_str and '-filter_complex' not in cmd_str:
            return FakeProc(cmd, lines=[_make_loudnorm_json()], returncode=0)
        # create temp file and return non-zero
        try:
            tmp = proc_module.create_temp_file(str(media))
            Path(tmp).write_text('tmp')
        except Exception:
            pass
        return FakeProc(cmd, lines=["err"], returncode=3)

    monkeypatch.setattr(proc_module, 'popen', fake_popen)

    # cause SignalHandler.unregister_temp_file to raise then be caught
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_temp_file', staticmethod(lambda p: (_ for _ in ()).throw(Exception('uerr2'))))

    captured = []
    ap = AudioProcessor()
    ap.logger.error = lambda msg: captured.append(msg)
    ap.logger.log_ffmpeg = lambda *a, **k: None

    res = ap.normalize_audio(str(media), show_ui=False, progress_callback=lambda *a, **k: None)
    assert res is None
    assert any('Normalization failed' in c or 'Normalization failed for' in c or 'ffmpeg exit' in c for c in captured)

    # cleanup temp if still present
    try:
        tmp = proc_module.create_temp_file(str(media))
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass


def test_boost_outer_exception_cleans_temp_and_logs(monkeypatch, tmp_path):
    media = tmp_path / "outer.mp4"
    media.write_text('o')

    # valid audio streams so temp_output will be created
    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # force create_temp_file to a known path and create the file
    temp_path = tmp_path / "outer_temp.mp4"
    monkeypatch.setattr(proc_module, 'create_temp_file', lambda p: str(temp_path))
    temp_path.write_text('tmp')

    # make channels_to_layout raise to trigger outer exception after temp created
    monkeypatch.setattr(proc_module, 'channels_to_layout', lambda c: (_ for _ in ()).throw(Exception('boom')))

    # make unregister_temp_file raise to hit its except branch, and os.remove raise too
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_temp_file', staticmethod(lambda p: (_ for _ in ()).throw(Exception('uerr3'))))
    monkeypatch.setattr(os, 'remove', lambda p: (_ for _ in ()).throw(Exception('rmerr3')))

    captured = []
    ap = AudioProcessor()
    ap.logger.error = lambda msg: captured.append(msg)

    res = ap.boost_audio(str(media), 3.0, show_ui=False, dry_run=False)
    assert res is None
    assert any('Boost failed' in c for c in captured)

    # cleanup temp file if still present
    try:
        if temp_path.exists():
            # restore os.remove and remove
            monkeypatch.setattr(os, 'remove', os.remove)
            os.remove(str(temp_path))
    except Exception:
        pass


def test_boost_run_command_exception_path_cleans_and_logs(monkeypatch, tmp_path):
    media = tmp_path / "runerr.mp4"
    media.write_text('r')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # create temp and ensure it exists
    temp_path = tmp_path / "runerr_temp.mp4"
    monkeypatch.setattr(proc_module, 'create_temp_file', lambda p: str(temp_path))
    temp_path.write_text('tmp')

    # run_command raises
    def fake_run(cmd, capture_output=True):
        raise RuntimeError('runfail')

    monkeypatch.setattr(proc_module, 'run_command', fake_run)

    # make unregister_temp_file and os.remove raise to exercise except blocks
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_temp_file', staticmethod(lambda p: (_ for _ in ()).throw(Exception('uerr4'))))
    monkeypatch.setattr(os, 'remove', lambda p: (_ for _ in ()).throw(Exception('rmerr4')))

    captured = []
    ap = AudioProcessor()
    ap.logger.error = lambda msg: captured.append(msg)
    ap.logger.log_ffmpeg = lambda *a, **k: None

    res = ap.boost_audio(str(media), 7.0, show_ui=False, dry_run=False)
    assert res is None
    assert any('Boost failed' in c or 'Boost failed for' in c for c in captured)

    # cleanup temp file if still present
    try:
        if temp_path.exists():
            monkeypatch.setattr(os, 'remove', os.remove)
            os.remove(str(temp_path))
    except Exception:
        pass


def test_boost_non_ui_logger_log_ffmpeg_raises(monkeypatch, tmp_path):
    media = tmp_path / "logerr.mp4"
    media.write_text('l')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # prepare temp
    temp_path = tmp_path / "logerr_temp.mp4"
    monkeypatch.setattr(proc_module, 'create_temp_file', lambda p: str(temp_path))
    temp_path.write_text('tmp')

    # simulate run_command returning result with stderr
    class R:
        stderr = 'ffmpeg stderr'

    monkeypatch.setattr(proc_module, 'run_command', lambda cmd, capture_output=True: R())

    # make logger.log_ffmpeg raise to hit except: pass
    ap = AudioProcessor()
    ap.logger.log_ffmpeg = lambda *a, **k: (_ for _ in ()).throw(Exception('logboom'))
    # capture error
    captured = []
    ap.logger.error = lambda msg: captured.append(msg)

    res = ap.boost_audio(str(media), 2.0, show_ui=False, dry_run=False)
    # log_ffmpeg raised but should be caught; boost should complete
    assert res == str(media)

    try:
        if temp_path.exists():
            os.remove(str(temp_path))
    except Exception:
        pass


def test_boost_show_ui_logger_log_ffmpeg_raises(monkeypatch, tmp_path):
    media = tmp_path / "logui.mp4"
    media.write_text('u')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # fake popen returns ffmpeg_log lines
    class FP:
        def __init__(self, cmd):
            self.command = cmd
            self.stderr = iter(["line1", "line2"])
            self.pid = 444
            self.returncode = 0
        def wait(self):
            return 0

    monkeypatch.setattr(proc_module, 'popen', lambda cmd: FP(cmd))

    # create temp in create_temp_file
    tmp_called = []
    def fake_create(p):
        t = str(tmp_path / "logui_temp.mp4")
        Path(t).write_text('tmp')
        tmp_called.append(t)
        return t

    monkeypatch.setattr(proc_module, 'create_temp_file', fake_create)

    ap = AudioProcessor()
    # make logger.log_ffmpeg raise to exercise the except pass
    ap.logger.log_ffmpeg = lambda *a, **k: (_ for _ in ()).throw(Exception('loguierr'))
    captured = []
    ap.logger.error = lambda msg: captured.append(msg)

    res = ap.boost_audio(str(media), 1.0, show_ui=True)
    # log_ffmpeg raised but was caught; boost should complete
    assert res == str(media)

    try:
        for t in tmp_called:
            if os.path.exists(t):
                os.remove(t)
    except Exception:
        pass


def test_boost_progress_popen_nonzero_with_exceptional_handlers(monkeypatch, tmp_path):
    media = tmp_path / "progfail.mp4"
    media.write_text('p')

    monkeypatch.setattr(proc_module, 'get_audio_streams', lambda path, logger=None: [{"channels":2, "sample_rate":48000, "tags":{}}])
    monkeypatch.setattr(proc_module, 'get_video_streams', lambda path: [])

    # ensure temp output exists
    temp_path = tmp_path / "progfail_temp.mp4"
    monkeypatch.setattr(proc_module, 'create_temp_file', lambda p: str(temp_path))
    temp_path.write_text('tmp')

    # fake popen: yields stderr lines then non-zero returncode
    class FP2:
        def __init__(self, cmd):
            self.command = cmd
            self.stderr = iter(["lineA", "lineB"])
            self.pid = 555
            self.returncode = 2
        def wait(self):
            return self.returncode

    monkeypatch.setattr(proc_module, 'popen', lambda cmd: FP2(cmd))

    # make register_child_pid raise to hit except: pass
    monkeypatch.setattr(proc_module.SignalHandler, 'register_child_pid', staticmethod(lambda pid: (_ for _ in ()).throw(Exception('regerr'))))
    # make progress_callback raise to hit inner except
    def bad_progress(stage, last_line=None, **kwargs):
        raise RuntimeError('pc')

    # make unregister_child_pid raise
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_child_pid', staticmethod(lambda pid: (_ for _ in ()).throw(Exception('unregerr'))))

    # make logger.log_ffmpeg raise to hit except
    ap = AudioProcessor()
    ap.logger.log_ffmpeg = lambda *a, **k: (_ for _ in ()).throw(Exception('logerr'))

    # make unregister_temp_file and os.remove raise to exercise cleanup excepts
    monkeypatch.setattr(proc_module.SignalHandler, 'unregister_temp_file', staticmethod(lambda p: (_ for _ in ()).throw(Exception('uerrx'))))
    monkeypatch.setattr(os, 'remove', lambda p: (_ for _ in ()).throw(Exception('rmx')))

    captured = []
    ap.logger.error = lambda msg: captured.append(msg)

    res = ap.boost_audio(str(media), 4.0, show_ui=False, progress_callback=bad_progress)
    assert res is None
    assert any('Boost failed' in c or 'ffmpeg exit' in c for c in captured)

    # cleanup temp file if still present
    try:
        if temp_path.exists():
            # restore os.remove for removal
            monkeypatch.setattr(os, 'remove', os.remove)
            os.remove(str(temp_path))
    except Exception:
        pass
