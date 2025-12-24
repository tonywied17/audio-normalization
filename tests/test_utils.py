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


def test_create_temp_file_handles_register_exception(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio.utils import create_temp_file
    import processors.audio.utils as utils_mod
    from core.config import TEMP_SUFFIX

    orig = str(tmp_path / "video.mp4")
    # make the SignalHandler.register_temp_file raise when called
    def bad_register(path):
        raise Exception("register failed")

    monkeypatch.setattr(utils_mod.SignalHandler, 'register_temp_file', bad_register)

    # Should not raise despite register_temp_file raising
    temp = create_temp_file(orig)
    base, ext = os.path.splitext(orig)
    assert temp.startswith(base)
    assert ext == ".mp4"
    assert temp.endswith(ext)
    assert temp != orig
