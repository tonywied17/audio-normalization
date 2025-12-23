import subprocess
from pathlib import Path
import sys

# Ensure src is on path during tests
repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from processors.audio.runner import run_command, popen


def test_run_command_success(monkeypatch):
    called = {}

    class DummyCompleted:
        def __init__(self):
            self.returncode = 0
            self.stdout = 'ok'
            self.stderr = ''

    def fake_run(cmd, stdout, stderr, text, encoding, check):
        called['cmd'] = cmd
        return DummyCompleted()

    # pretend we have a bundled executable
    monkeypatch.setattr('processors.audio.runner.get_bundled_executable', lambda name: '/bundled/ffmpeg' if 'ffmpeg' in name else None)
    monkeypatch.setattr(subprocess, 'run', fake_run)

    res = run_command(['ffmpeg', '-version'], capture_output=True)
    assert res.stdout == 'ok'
    assert called['cmd'][0] == '/bundled/ffmpeg'


def test_run_command_failure(monkeypatch):
    def raise_called(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0], stderr='broken')

    monkeypatch.setattr(subprocess, 'run', raise_called)

    try:
        run_command(['echo', 'hi'], capture_output=True)
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert 'Command failed' in str(e)


def test_popen_uses_bundled(monkeypatch):
    class DummyPopen:
        def __init__(self, *args, **kwargs):
            self.args = args

    monkeypatch.setattr('processors.audio.runner.get_bundled_executable', lambda name: '/bundled/ffprobe' if 'ffprobe' in name else None)
    monkeypatch.setattr(subprocess, 'Popen', lambda cmd, stderr, text, encoding: DummyPopen(cmd))

    p = popen(['ffprobe', '-v', 'quiet'])
    assert hasattr(p, 'args')
    assert p.args[0][0] == '/bundled/ffprobe'
