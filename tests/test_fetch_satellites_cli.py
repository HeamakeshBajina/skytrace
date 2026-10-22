import subprocess
import sys
from pathlib import Path


def test_fetch_cli_help_exits_without_creating_data_or_fetching(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    script = project_root / "scripts" / "fetch_satellites.py"

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "usage:" in result.stdout.lower()
    assert "--help" in result.stdout
    assert not (tmp_path / "data" / "raw").exists()
