import sys
from pathlib import Path
from rich.console import Console


def test_display_results_panel_fallback(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    import importlib
    cli_mod = importlib.import_module('cli.cli')

    had_panel = hasattr(cli_mod, 'Panel')
    original_panel = getattr(cli_mod, 'Panel', None)

    try:
        if had_panel:
            delattr(cli_mod, 'Panel')

        AudioNormalizationCLI = getattr(cli_mod, 'AudioNormalizationCLI')
        cli = AudioNormalizationCLI(command_handler=None)
        cli.console = Console(record=True)

        results = [{"file": "a.mp4", "task": "normalize", "status": "Success"}]
        cli.display_results(results)

        out = cli.console.export_text()
        assert "Processing Complete" in out
        assert "a.mp4" in out

    finally:
        if had_panel:
            setattr(cli_mod, 'Panel', original_panel)
        else:
            if hasattr(cli_mod, 'Panel'):
                delattr(cli_mod, 'Panel')
