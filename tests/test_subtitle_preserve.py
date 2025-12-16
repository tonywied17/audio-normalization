import os
import json
from processors.audio import AudioProcessor
from unittest.mock import patch, MagicMock


def test_normalize_and_boost_preserve_subtitles(tmp_path, monkeypatch):
    media = str(tmp_path / "video_with_subs.mkv")
    open(media, "wb").close()

    audio_streams = [{"index": 1, "channels": 2, "tags": {"title": "Track 1"}}]
    video_streams = [{"index": 0}]
    subtitle_streams = [{"index": 2, "codec_name": "srt"}]

    monkeypatch.setattr("processors.audio.processor.get_audio_streams", lambda path, logger=None: audio_streams)
    monkeypatch.setattr("processors.audio.processor.get_video_streams", lambda path: video_streams)

    tmp_out = str(tmp_path / "out_temp.mkv")
    monkeypatch.setattr("processors.audio.processor.create_temp_file", lambda p: tmp_out)

    captured = {"cmds": []}

    def fake_run_command(cmd, capture_output=False):
        """Fake run_command to capture ffmpeg commands."""
        captured["cmds"].append(cmd)
        class R:
            returncode = 0
            stderr = ""
        return R()

    def fake_popen(cmd):
        """Fake popen to capture ffmpeg commands."""
        captured["cmds"].append(cmd)
        proc = MagicMock()
        proc.stderr = []
        proc.pid = 12345
        proc.returncode = 0
        def wait():
            return 0
        proc.wait = wait
        return proc

    monkeypatch.setattr("processors.audio.processor.run_command", fake_run_command)
    monkeypatch.setattr("processors.audio.processor.popen", fake_popen)

    ap = AudioProcessor()

    ap.normalize_audio(media, show_ui=False)
    ap.boost_audio(media, 5.0, show_ui=False, dry_run=False)

    found_map = any(("-map" in cmd and any(x == "0:s?" for x in cmd)) or ("-c:s" in cmd and "copy" in cmd) for cmd in captured["cmds"])
    assert found_map, f"Expected subtitle mapping/copy in ffmpeg commands, captured: {captured['cmds']}"
