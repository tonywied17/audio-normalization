import sys
from pathlib import Path
import os


def test_update_track_title_and_channels(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio.utils import update_track_title, channels_to_layout
    t = "[molexAudio Normalized] My Track"
    out = update_track_title(t, "Boosted", "5%")
    assert "Boosted" in out
    assert "My Track" in out

    assert channels_to_layout(1) == 'mono'
    assert channels_to_layout(2) == 'stereo'
    assert channels_to_layout(6) == '5.1'


def test_create_temp_file_registers(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio.utils import create_temp_file
    from core.signal_handler import SignalHandler

    sh = SignalHandler([])
    try:
        orig = str(tmp_path / "media.mp4")
        temp = create_temp_file(orig)
        assert temp in SignalHandler._global_instance.temp_files
    finally:
        try:
            SignalHandler.unregister_temp_file(temp)
        except Exception:
            pass
