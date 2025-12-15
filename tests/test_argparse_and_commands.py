import sys
from pathlib import Path
import os


def test_parse_args_normalize(monkeypatch):
    """Parse args for normalize and handle missing args."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    import cli.argparse_config as ac
    monkeypatch.setattr(sys, 'argv', ['prog', '--normalize', 'file.mp4'])
    args = ac.parse_args()
    assert args is not None

    monkeypatch.setattr(sys, 'argv', ['prog'])
    args2 = ac.parse_args()
    assert args2 is None


def test_commands_handle(monkeypatch, tmp_path):
    """Verify CommandHandler handles boost/normalize and ffmpeg setup."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from cli.commands import CommandHandler
    from core.logger import Logger

    ch = CommandHandler(max_workers=1)
    f = tmp_path / "f.mp4"
    f.write_text("x")

    monkeypatch.setattr(ch, 'process_file', lambda file_path, operation, **k: True)
    res = ch.handle_boost(str(f), '5', dry_run=True)
    assert isinstance(res, list)

    res2 = ch.handle_normalize(str(f), dry_run=True)
    assert isinstance(res2, list)

    class P:
        def __init__(self, rc, out='', err=''):
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    def fake_run(cmd, cwd, capture_output, text):
        return P(0, 'ok', '')

    monkeypatch.setattr('subprocess.run', fake_run)
    r = ch.setup_ffmpeg()
    assert isinstance(r, list)
