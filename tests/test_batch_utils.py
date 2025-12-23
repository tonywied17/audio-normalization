import sys
from pathlib import Path
import os

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from processors.batch import utils as utils_mod


def test_find_media_files_empty(tmp_path):
    out = utils_mod.find_media_files(str(tmp_path))
    assert out == []


def test_find_media_files_nested_and_extensions(tmp_path):
    # create files matching supported extensions and non-matching
    (tmp_path / 'a.mp4').write_text('x')
    (tmp_path / 'b.txt').write_text('y')
    nested = tmp_path / 'nested'
    nested.mkdir()
    (nested / 'c.MP3').write_text('z')
    deep = nested / 'deep'
    deep.mkdir()
    (deep / 'd.mkv').write_text('k')

    found = utils_mod.find_media_files(str(tmp_path))
    # should find mp4, MP3, mkv (case-insensitive) and ignore .txt
    assert any(p.endswith('a.mp4') for p in found)
    assert any(p.lower().endswith('c.mp3') for p in found)
    assert any(p.endswith('d.mkv') for p in found)
    assert all(not p.endswith('b.txt') for p in found)


def test_find_media_files_custom_extensions(tmp_path):
    (tmp_path / 'one.txt').write_text('1')
    (tmp_path / 'two.doc').write_text('2')
    out = utils_mod.find_media_files(str(tmp_path), supported_extensions=('.txt',))
    assert len(out) == 1 and out[0].endswith('one.txt')
