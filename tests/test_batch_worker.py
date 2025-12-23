import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_path = str(repo_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from processors.batch import worker


class DummyProcessor:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc

    def boost_audio(self, file_path, boost_percent, show_ui=False, dry_run=False, progress_callback=None):
        if self._exc:
            raise self._exc
        return self._result

    def normalize_audio(self, file_path, show_ui=False, progress_callback=None):
        if self._exc:
            raise self._exc
        return self._result


def test_boost_file_dry_run():
    proc = DummyProcessor(result=True)
    out = worker.boost_file(proc, "x.mp4", 10.0, dry_run=True)
    assert out["success"] is True
    assert out["message"] == "Dry Run"


def test_boost_file_success_and_failure_and_exception():
    # success
    proc = DummyProcessor(result=True)
    out = worker.boost_file(proc, "x.mp4", 5.0, dry_run=False)
    assert out == {"success": True}

    # failure (processor returns falsy)
    proc2 = DummyProcessor(result=False)
    out2 = worker.boost_file(proc2, "x.mp4", 5.0)
    assert out2["success"] is False and "Boost failed" in out2["message"]

    # exception
    proc3 = DummyProcessor(exc=RuntimeError("boom"))
    out3 = worker.boost_file(proc3, "x.mp4", 5.0)
    assert out3["success"] is False and "boom" in out3["message"]


def test_normalize_file_dry_run():
    proc = DummyProcessor(result=True)
    out = worker.normalize_file(proc, "y.mp4", dry_run=True)
    assert out["success"] is True
    assert out["message"] == "Dry Run"


def test_normalize_file_success_and_failure_and_exception():
    proc = DummyProcessor(result=True)
    out = worker.normalize_file(proc, "y.mp4")
    assert out == {"success": True}

    proc2 = DummyProcessor(result=False)
    out2 = worker.normalize_file(proc2, "y.mp4")
    assert out2["success"] is False and "Normalization failed" in out2["message"]

    proc3 = DummyProcessor(exc=ValueError("nope"))
    out3 = worker.normalize_file(proc3, "y.mp4")
    assert out3["success"] is False and "nope" in out3["message"]
