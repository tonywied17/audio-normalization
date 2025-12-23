import sys
import os
from pathlib import Path
from rich.console import Console


def test_display_results_basic(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from cli.cli import AudioNormalizationCLI

    cli = AudioNormalizationCLI(command_handler=None)
    cli.console = Console(record=True)

    results = [
        {"file": str(tmp_path / "file1.mp4"), "task": "normalize", "status": "Success"},
        {"file": str(tmp_path / "file2.mp4"), "task": "Boost 5% Audio", "status": "Failed", "message": "Error writing file"},
    ]

    cli.display_results(results)

    out = cli.console.export_text()
    assert "Processing Complete" in out or "Processing Complete" in out
    assert "file1.mp4" in out
    assert "file2.mp4" in out
    assert "Success" in out
    assert "Failed" in out
