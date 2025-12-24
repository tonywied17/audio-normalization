import sys
from pathlib import Path
import os

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import subprocess
from cli.commands import CommandHandler


def test_process_file_boost_success_and_failure_and_exception(monkeypatch):
    handler = CommandHandler(max_workers=1)

    # success: boost_audio returns non-None
    def ok_boost(self, file_path, boost_percent, show_ui=True, dry_run=False, progress_callback=None):
        return file_path
    monkeypatch.setattr('processors.audio.AudioProcessor.boost_audio', ok_boost)
    assert handler.process_file('x.mp4', 'boost', boost_percent=5) is True

    # failure: returns None
    def none_boost(self, file_path, boost_percent, show_ui=True, dry_run=False, progress_callback=None):
        return None
    monkeypatch.setattr('processors.audio.AudioProcessor.boost_audio', none_boost)
    assert handler.process_file('x.mp4', 'boost', boost_percent=5) is False

    # exception: should log error and return False
    def exc_boost(self, *a, **k):
        raise RuntimeError('boom')
    monkeypatch.setattr('processors.audio.AudioProcessor.boost_audio', exc_boost)
    called = {}
    def fake_error(msg):
        called['err'] = msg
    monkeypatch.setattr(handler.logger, 'error', fake_error)
    assert handler.process_file('x.mp4', 'boost', boost_percent=5) is False
    assert 'Failed to process' in called.get('err', '')


def test_handle_boost_directory_and_file_and_invalid(monkeypatch, tmp_path):
    handler = CommandHandler(max_workers=1)

    # simulate directory path -> call batch_processor.boost_files_with_progress
    results = [{'file':'a','status':'Success'}]
    class BP:
        def boost_files_with_progress(self, d, p, dry_run=False, max_workers=None):
            return results
    handler.batch_processor = BP()
    monkeypatch.setattr(os.path, 'isdir', lambda p: True)
    out = handler.handle_boost('somedir', '12.5', dry_run=True, max_workers=1)
    assert out is results

    # invalid percentage
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(os.path, 'isfile', lambda p: False)
    errs = {}
    monkeypatch.setattr(handler.logger, 'error', lambda m: errs.setdefault('msg', m))
    assert handler.handle_boost('x', 'notnum') == []
    assert 'Invalid boost percentage' in errs.get('msg')

    # file path case
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(handler, 'process_file', lambda path, op, **k: True)
    res = handler.handle_boost('afile.mp4', '5', dry_run=False)
    assert isinstance(res, list) and res[0]['status'] == 'Success'


def test_setup_ffmpeg_success_failure_and_exception(monkeypatch, tmp_path):
    handler = CommandHandler(max_workers=1)
    # success case: subprocess.run returns returncode 0
    class Proc:
        def __init__(self, ret=0, out='', err=''):
            self.returncode = ret
            self.stdout = out
            self.stderr = err

    def ok_run(cmd, cwd=None, capture_output=None, text=None):
        return Proc(0, out='ok', err='')

    monkeypatch.setattr(subprocess, 'run', ok_run)
    res = handler.setup_ffmpeg()
    assert all(isinstance(r, dict) for r in res)
    assert any(r['success'] for r in res)

    # failure case: returncode != 0 -> logger.error called
    def bad_run(cmd, cwd=None, capture_output=None, text=None):
        return Proc(1, out='', err='fail')
    logs = []
    monkeypatch.setattr(subprocess, 'run', bad_run)
    monkeypatch.setattr(handler.logger, 'error', lambda m: logs.append(m))
    res2 = handler.setup_ffmpeg()
    assert any(not r['success'] for r in res2)
    assert any('Setup step failed' in m for m in logs)

    # exception path: subprocess.run raises
    def raise_run(*a, **k):
        raise RuntimeError('boom')
    monkeypatch.setattr(subprocess, 'run', raise_run)
    logs2 = []
    monkeypatch.setattr(handler.logger, 'error', lambda m: logs2.append(m))
    res3 = handler.setup_ffmpeg()
    assert any(not r['success'] for r in res3)
    assert any('Exception running setup step' in m for m in logs2)


def test_process_file_unknown_operation_logs_and_returns_false(monkeypatch):
    handler = CommandHandler(max_workers=1)
    called = {}
    monkeypatch.setattr(handler.logger, 'error', lambda m: called.setdefault('err', m))
    res = handler.process_file('x.mp4', 'unknown_op')
    assert res is False
    assert 'Failed to process' in called.get('err', '')


def test_handle_normalize_directory_file_and_invalid(monkeypatch, tmp_path):
    handler = CommandHandler(max_workers=1)

    # directory path case
    d = tmp_path / 'dd'
    d.mkdir()
    monkeypatch.setattr(os.path, 'isdir', lambda p: True)
    monkeypatch.setattr(os.path, 'isfile', lambda p: False)
    monkeypatch.setattr(handler.batch_processor, 'process_directory', lambda p, dry_run=False, max_workers=None: [{'file': p, 'status': 'Success'}])
    out = handler.handle_normalize(str(d), dry_run=True, max_workers=1)
    assert isinstance(out, list) and out[0]['status'] == 'Success'

    # file path case
    f = tmp_path / 'f.mp4'
    f.write_text('x')
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(os.path, 'isfile', lambda p: True)
    monkeypatch.setattr(handler.batch_processor, 'process_single_file_with_progress', lambda p, dry_run=False: {'file': p, 'status': 'Success'})
    out2 = handler.handle_normalize(str(f), dry_run=False)
    assert isinstance(out2, list) and out2[0]['status'] == 'Success'

    # invalid path
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(os.path, 'isfile', lambda p: False)
    logs = {}
    monkeypatch.setattr(handler.logger, 'error', lambda m: logs.setdefault('msg', m))
    out3 = handler.handle_normalize('nope', dry_run=False)
    assert out3 == []
    assert 'Invalid path provided' in logs.get('msg', '')


def test_handle_boost_invalid_path_logs_and_returns_empty(monkeypatch):
    handler = CommandHandler(max_workers=1)
    monkeypatch.setattr(os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(os.path, 'isfile', lambda p: False)
    logs = {}
    monkeypatch.setattr(handler.logger, 'error', lambda m: logs.setdefault('msg', m))
    res = handler.handle_boost('nope', '5')
    assert res == []
    assert 'Invalid file or directory path' in logs.get('msg', '')
