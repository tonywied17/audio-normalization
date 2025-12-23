import sys
import os
from types import SimpleNamespace
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import shutil
import importlib
from cli import cli as cli_module
from cli.cli import AudioNormalizationCLI


def test_display_menu_terminal_size_bounds(monkeypatch):
    # very small terminal -> menu_width should hit minimum (40)
    monkeypatch.setattr(shutil, 'get_terminal_size', lambda fallback=(80,24): os.terminal_size((60, 24)))
    monkeypatch.setattr(shutil, 'which', lambda name: 'ffmpeg')
    cli = AudioNormalizationCLI(command_handler=None)
    cli.display_menu()

    # very large terminal -> menu_width should hit maximum (80)
    monkeypatch.setattr(shutil, 'get_terminal_size', lambda fallback=(80,24): os.terminal_size((500, 120)))
    cli2 = AudioNormalizationCLI(command_handler=None)
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    cli2.display_menu()


def test_display_menu_shutil_which_raises(monkeypatch):
    # shutil.which raising should be caught and treated as not found
    def bomb(name):
        raise RuntimeError("boom")
    monkeypatch.setattr(shutil, 'which', bomb)
    cli = AudioNormalizationCLI(command_handler=None)
    cli.display_menu()


def test_display_results_panel_nameerror_import(monkeypatch, capsys):
    # Force Panel NameError by removing it from the module then calling display_results
    # reload module to ensure it has Panel
    importlib.reload(cli_module)
    if hasattr(cli_module, 'Panel'):
        delattr(cli_module, 'Panel')
    # re-import class after deletion so function-level import is exercised
    cli = AudioNormalizationCLI(command_handler=None)
    results = [{"file": "/tmp/x.mp4", "task": "T", "status": "Success", "message": "m"}]
    cli.display_results(results)
    out = capsys.readouterr().out
    assert 'Processing Complete' in out


def test_wait_for_resume_or_exit_tty_termios_fallback(monkeypatch):
    cli = AudioNormalizationCLI(command_handler=None)
    # ensure msvcrt not present
    monkeypatch.delitem(sys.modules, 'msvcrt', raising=False)

    # fake termios and tty
    class FakeTermios:
        TCSADRAIN = 0
        def tcgetattr(self, fd):
            return [0]
        def tcsetattr(self, fd, when, old):
            return None

    class FakeTTY:
        def setraw(self, fd):
            return None

    monkeypatch.setitem(sys.modules, 'termios', FakeTermios())
    monkeypatch.setitem(sys.modules, 'tty', FakeTTY())

    # fake stdin object
    class FakeStdin:
        def fileno(self):
            return 0
        def read(self, n):
            return '\r'
    monkeypatch.setattr(sys, 'stdin', FakeStdin())

    assert cli._wait_for_resume_or_exit() == 'enter'
