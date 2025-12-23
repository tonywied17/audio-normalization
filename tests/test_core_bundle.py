import sys
import os
from pathlib import Path

from pathlib import Path

def test_get_bundled_executable_not_frozen(monkeypatch):
    # ensure not frozen returns None
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    from core.bundle import get_bundled_executable
    assert get_bundled_executable('whatever') is None


def test_get_bundled_executable_candidate_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    base = tmp_path / 'meipass'
    base.mkdir()
    # create candidate file
    exe = 'tool.exe'
    p = base / exe
    p.write_text('x')
    monkeypatch.setattr(sys, '_MEIPASS', str(base), raising=False)
    from core.bundle import get_bundled_executable
    out = get_bundled_executable(exe)
    assert out is not None and out.endswith('tool.exe')


def test_get_bundled_executable_candidate_exe_added(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    base = tmp_path / 'meipass2'
    base.mkdir()
    # create only tool.exe while requesting 'tool' (no .exe)
    p = base / 'tool.exe'
    p.write_text('y')
    monkeypatch.setattr(sys, '_MEIPASS', str(base), raising=False)
    from core.bundle import get_bundled_executable
    out = get_bundled_executable('tool')
    assert out is not None and out.endswith('tool.exe')


def test_get_bundled_executable_uses_sys_executable_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    # no _MEIPASS -> use dirname(sys.executable)
    fake_exec = tmp_path / 'bin' / 'python.exe'
    fake_exec.parent.mkdir(parents=True)
    fake_exec.write_text('e')
    monkeypatch.setattr(sys, 'executable', str(fake_exec), raising=False)
    # create file in that dir
    target = fake_exec.parent / 'helper.exe'
    target.write_text('z')
    from core.bundle import get_bundled_executable
    out = get_bundled_executable('helper.exe')
    assert out is not None and out.endswith('helper.exe')


def test_get_bundled_executable_handles_existence_errors(monkeypatch):
    # simulate os.path.exists raising to hit the except path and return None
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', '/nonexistent', raising=False)
    import os as _os
    orig_exists = _os.path.exists
    def bad_exists(p):
        raise RuntimeError('boom')
    monkeypatch.setattr(_os.path, 'exists', bad_exists)
    from core.bundle import get_bundled_executable
    try:
        assert get_bundled_executable('x') is None
    finally:
        monkeypatch.setattr(_os.path, 'exists', orig_exists)
