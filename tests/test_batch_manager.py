import sys
import os
from pathlib import Path
import threading

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import time
from processors.batch import manager as mgr


def _make_dummy_live():
    class DummyLive:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def update(self, grp):
            # no-op
            return None
    return DummyLive


def test_process_directory_no_files(monkeypatch, tmp_path):
    monkeypatch.setattr(mgr, 'find_media_files', lambda d, exts: [])
    bp = mgr.BatchProcessor(max_workers=1)
    out = bp.process_directory(str(tmp_path))
    assert out == []


def test_process_files_with_progress_probe_exception_and_success(monkeypatch, tmp_path):
    # create temp file
    f = tmp_path / 'a.mp4'
    f.write_text('x')
    files = [str(f)]

    # ensure Live is our dummy context manager
    monkeypatch.setattr(mgr, 'Live', _make_dummy_live())

    bp = mgr.BatchProcessor(max_workers=1)

    # audio processor where _get_audio_streams raises
    class AP:
        def _get_audio_streams(self, p):
            raise RuntimeError('probe fail')
        def normalize_audio(self, p, show_ui=False, progress_callback=None):
            return {"success": True}

    bp.audio_processor = AP()

    res = bp.process_files_with_progress(files, dry_run=False, max_workers=1)
    assert isinstance(res, list)
    assert res[0]['status'] == 'Success'


def test_process_files_with_progress_invalid_worker_count(monkeypatch, tmp_path):
    f = tmp_path / 'b.mp4'
    f.write_text('y')
    files = [str(f)]
    monkeypatch.setattr(mgr, 'Live', _make_dummy_live())

    bp = mgr.BatchProcessor(max_workers=2)
    class AP:
        def _get_audio_streams(self, p):
            return []
        def normalize_audio(self, p, show_ui=False, progress_callback=None):
            return {"success": True}
    bp.audio_processor = AP()

    # pass invalid max_workers to hit exception path
    out = bp.process_files_with_progress(files, dry_run=False, max_workers='bad')
    assert isinstance(out, list) and out[0]['status'] == 'Success'


def test_boost_files_with_progress_success_and_failure_and_callbacks(monkeypatch, tmp_path):
    # create two files
    f1 = tmp_path / 'one.mp4'
    f2 = tmp_path / 'two.mp4'
    f1.write_text('1')
    f2.write_text('2')
    files = [str(f1), str(f2)]

    monkeypatch.setattr(mgr, 'find_media_files', lambda d, exts: files)
    monkeypatch.setattr(mgr, 'Live', _make_dummy_live())

    bp = mgr.BatchProcessor(max_workers=2)

    class AP:
        def _get_audio_streams(self, p):
            return [1]
    bp.audio_processor = AP()

    # make bp_ui.make_update_panel return a callback that raises on first call to exercise try/except
    def make_cb(idx, spinners, panels, live_ref, file, boost_percent=None, audio_tracks=0):
        called = {"n":0}
        def cb(stage, last_line=None, error=False, info_panel=None):
            called['n'] += 1
            if called['n'] == 1:
                raise RuntimeError('cb fail')
            return None
        return cb

    monkeypatch.setattr(mgr.bp_ui, 'make_update_panel', make_cb)

    # bp_worker.boost_file: first returns success, second returns failure
    def fake_boost(ap, path, boost_percent, dry_run=False, show_ui=False, progress_callback=None):
        if 'one.mp4' in path:
            return {"success": True}
        return {"success": False, "message": "oops"}

    monkeypatch.setattr(mgr.bp_worker, 'boost_file', fake_boost)
    res = bp.boost_files_with_progress(str(tmp_path), 12.5, dry_run=False, max_workers=2)
    assert any(r['status'] == 'Success' for r in res)
    assert any(r['status'] == 'Failed' for r in res)
