import sys
from pathlib import Path
import importlib

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest


def reload_module():
    # ensure a fresh module import for each test
    if 'cli.argparse_config' in sys.modules:
        del sys.modules['cli.argparse_config']
    return importlib.import_module('cli.argparse_config')


def test_boost_with_normalization_flags_exits(capsys):
    mod = reload_module()
    sys_argv = ['prog', '--boost', 'file.mp4', '10', '--I', '-23']
    sys.argv = sys_argv
    with pytest.raises(SystemExit) as exc:
        mod.parse_args()
    captured = capsys.readouterr()
    assert 'Error: Normalization parameters cannot be used with --boost' in captured.out
    assert exc.value.code == 1


def test_normalization_flags_require_normalize(capsys):
    mod = reload_module()
    sys.argv = ['prog', '--I', '-16']
    with pytest.raises(SystemExit) as exc:
        mod.parse_args()
    out = capsys.readouterr().out
    assert 'Error: Normalization parameters require --normalize' in out
    assert exc.value.code == 1


def test_boost_percentage_must_be_number(capsys):
    mod = reload_module()
    sys.argv = ['prog', '--boost', 'file.mp4', 'notanumber']
    with pytest.raises(SystemExit) as exc:
        mod.parse_args()
    out = capsys.readouterr().out
    assert 'Error: Boost percentage must be a number.' in out
    assert exc.value.code == 1
