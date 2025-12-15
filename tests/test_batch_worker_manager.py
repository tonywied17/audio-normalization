import sys
from pathlib import Path
import threading


def test_worker_functions_and_manager(tmp_path, monkeypatch):
    """Test worker functions and BatchProcessor with dummy processor."""
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from processors.batch import worker as bp_worker
    from processors.batch.manager import BatchProcessor

    class DummyProcessor:
        def boost_audio(self, path, percent, show_ui=False, dry_run=False, progress_callback=None):
            return path

        def normalize_audio(self, path, show_ui=False, progress_callback=None):
            return path

    dp = DummyProcessor()
    r = bp_worker.boost_file(dp, "file.mp4", 5.0, dry_run=True)
    assert r.get("success")

    r2 = bp_worker.normalize_file(dp, "file.mp4", dry_run=True)
    assert r2.get("success")

    bp = BatchProcessor(max_workers=1)
    bp.audio_processor = dp

    f1 = str(tmp_path / "a.mp4")
    open(f1, "w").close()
    results = bp.process_files_with_progress([f1], dry_run=True, max_workers=1)
    assert isinstance(results, list)
    assert results[0]["status"] in ("Success", "Failed")
