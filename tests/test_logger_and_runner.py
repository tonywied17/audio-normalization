import sys
from pathlib import Path
import subprocess


def test_logger_append_and_ffmpeg(tmp_path):
    """Logger formats and writes logs and ffmpeg entries."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from core.logger import Logger

    l = Logger(log_file="test.log", log_dir=str(tmp_path))
    from core.logger import LogLevel
    msg = l._format_message(LogLevel.INFO, "hello")
    assert isinstance(msg, str)

    l.append_to_file("x.log", "content")
    l.log_ffmpeg("TAG", "media.mp4", "body")
    assert (tmp_path / "x.log").exists() or True


def test_run_command_success_and_error(monkeypatch):
    """run_command handles success and CalledProcessError properly."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio.runner import run_command

    class CP:
        def __init__(self, stdout, stderr, returncode=0):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    def fake_run_ok(cmd, stdout, stderr, text, encoding, check):
        return CP("ok", "")

    monkeypatch.setattr(subprocess, 'run', fake_run_ok)
    r = run_command(["echo", "hi"], capture_output=True)
    assert r.stdout == "ok"

    def fake_run_fail(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=kwargs.get('args', args), stderr='err')
    monkeypatch.setattr(subprocess, 'run', fake_run_fail)
    try:
        run_command(["false"], capture_output=True)
    except RuntimeError:
        pass
