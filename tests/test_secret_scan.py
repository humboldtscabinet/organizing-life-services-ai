import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tracked_files_do_not_contain_high_confidence_secrets():
    result = subprocess.run(
        [sys.executable, "scripts/scan_secrets.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
