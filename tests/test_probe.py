import sys
from pathlib import Path
import json


def test_get_audio_streams_various(monkeypatch, tmp_path):
    """Probe returns audio streams under various ffprobe outputs."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio import probe
    from core.logger import Logger

    logger = Logger()
    media = str(tmp_path / "m.mp4")

    class R:
        def __init__(self, stdout):
            self.stdout = stdout

    out = json.dumps({"streams": [{"index": 0, "tags": {}}]})
    monkeypatch.setattr(probe, 'run_command', lambda cmd: R(out))
    s = probe.get_audio_streams(media, logger)
    assert isinstance(s, list) and len(s) == 1

    monkeypatch.setattr(probe, 'run_command', lambda cmd: R(json.dumps({})) )
    calls = {'i':0}
    def run_cmd_fallback(cmd):
        calls['i'] += 1
        if calls['i'] == 1:
            return R(json.dumps({}))
        return R(json.dumps({"streams": [{"index":1}] }))
    monkeypatch.setattr(probe, 'run_command', run_cmd_fallback)
    s2 = probe.get_audio_streams(media, logger)
    assert isinstance(s2, list)

    def run_cmd_probe_count(cmd):
        cmd_str = ' '.join(cmd)
        if '-show_streams' in cmd_str:
            return R(json.dumps({}))
        if 'csv=p=0' in cmd_str:
            return R("0\n1\n")
        return R(json.dumps({}))
    monkeypatch.setattr(probe, 'run_command', run_cmd_probe_count)
    s3 = probe.get_audio_streams(media, logger)
    assert isinstance(s3, list)

    def raise_err(cmd):
        raise RuntimeError("fail")
    monkeypatch.setattr(probe, 'run_command', raise_err)
    s4 = probe.get_audio_streams(media, logger)
    assert s4 == []


def test_get_video_streams(monkeypatch, tmp_path):
    """Probe returns video streams list."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.audio import probe

    class R:
        def __init__(self, stdout):
            self.stdout = stdout

    monkeypatch.setattr(probe, 'run_command', lambda cmd: R(json.dumps({"streams": [{"index":0}]})))
    s = probe.get_video_streams("x")
    assert isinstance(s, list) and len(s) == 1
