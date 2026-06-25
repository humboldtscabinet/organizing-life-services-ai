import json
import subprocess
import sys
from pathlib import Path


def test_build_filter_repo_replace_text_script(tmp_path):
    manifest = tmp_path / "replacements.tsv"
    manifest.write_text(
        "\n".join(
            [
                "label\tmatch_type\tfind\treplace",
                "ols_api_key\tliteral\tOLD_OLS_KEY\tNEW_OLS_KEY",
                "bearer\tregex\tBearer\\s+OLDTOKEN\tBearer ***REMOVED***",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "replace-text.txt"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_filter_repo_replace_text.py",
            "--input",
            str(manifest),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    lines = output.read_text(encoding="utf-8").splitlines()
    assert "OLD_OLS_KEY==>NEW_OLS_KEY" in lines
    assert r"regex:Bearer\s+OLDTOKEN==>Bearer ***REMOVED***" in lines


def test_history_scrub_inventory_script_hashes_matches(tmp_path):
    sample = tmp_path / "notes.txt"
    sample.write_text(
        "OPENAI_API_KEY=sk-test-abcdefghijklmnopqrstuvwxyz123456\n"
        "-----BEGIN PRIVATE KEY-----\nabc123\n",
        encoding="utf-8",
    )
    output = tmp_path / "history-scan.local.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/history_scrub_inventory.py",
            str(tmp_path),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["counts_by_rule"]["api_key_assignment"] >= 1
    assert payload["counts_by_rule"]["private_key_block"] >= 1
    assert payload["total_findings"] >= 2

    raw_report = output.read_text(encoding="utf-8")
    assert "sk-test-abcdefghijklmnopqrstuvwxyz123456" not in raw_report
    assert "abc123" not in raw_report
