import sys
import os
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import signal
from core.signal_handler import SignalHandler


def test_register_and_unregister_temp_and_child(monkeypatch):
    # prevent installing real signal handlers
    monkeypatch.setattr(signal, 'signal', lambda *a, **k: None)
    # ensure clean global
    SignalHandler._global_instance = None

    sh = SignalHandler([])
    assert SignalHandler._global_instance is sh

    # temp file registration
    SignalHandler.register_temp_file('t1')
    assert 't1' in sh.temp_files
    SignalHandler.unregister_temp_file('t1')
    assert 't1' not in sh.temp_files

    # child pid registration
    SignalHandler.register_child_pid(12345)
    assert 12345 in sh.child_pids
    SignalHandler.unregister_child_pid(12345)
    assert 12345 not in sh.child_pids


def test_cleanup_temp_files_removes_and_handles_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(signal, 'signal', lambda *a, **k: None)
    SignalHandler._global_instance = None

    good = tmp_path / 'good.tmp'
    bad = tmp_path / 'bad.tmp'
    good.write_text('x')
    bad.write_text('y')

    sh = SignalHandler([str(good), str(bad)])

    # make os.remove raise for bad file only
    orig_remove = os.remove

    def fake_remove(p):
        if os.path.basename(p) == bad.name:
            raise RuntimeError('rm fail')
        return orig_remove(p)

    monkeypatch.setattr(os, 'remove', fake_remove)

    # run cleanup: should remove good, and swallow exception for bad
    sh.cleanup_temp_files()
    assert not good.exists()


def test_signal_handler_kills_child_and_exits(monkeypatch):
    monkeypatch.setattr(signal, 'signal', lambda *a, **k: None)
    SignalHandler._global_instance = None

    sh = SignalHandler([])
    # add child pid
    sh.child_pids.append(99999)

    called = {}

    def fake_kill(pid, sig):
        called['pid'] = pid
        called['sig'] = sig

    monkeypatch.setattr(os, 'kill', fake_kill)

    # intercept sys.exit to raise SystemExit so we can assert
    def fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(sys, 'exit', fake_exit)

    try:
        sh._signal_handler(signal.SIGINT, None)
    except SystemExit as e:
        assert e.code == 0
    assert called.get('pid') == 99999
    assert called.get('sig') == signal.SIGTERM


def test_signal_handler_kill_raises_is_handled(monkeypatch):
    monkeypatch.setattr(signal, 'signal', lambda *a, **k: None)
    SignalHandler._global_instance = None

    sh = SignalHandler([])
    sh.child_pids.append(11111)

    def bad_kill(pid, sig):
        raise RuntimeError('nope')

    monkeypatch.setattr(os, 'kill', bad_kill)
    monkeypatch.setattr(sys, 'exit', lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    try:
        sh._signal_handler(signal.SIGTERM, None)
    except SystemExit:
        pass
