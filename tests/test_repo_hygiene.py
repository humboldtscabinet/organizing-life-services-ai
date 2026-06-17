import subprocess


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_conversation_payloads_are_not_tracked():
    result = _git("ls-files", "conversations/raw", "conversations/markdown", "conversations/INDEX.md")

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_private_artifact_patterns_are_ignored():
    private_paths = [
        "conversations/raw/example.jsonl.gz",
        "conversations/markdown/example.md",
        "conversations/scripts/example.log",
        "conversations/.trigger",
        "data/audit_output/indexnow_key.txt",
        "data/audit_output/example_token.txt",
        "data/audit_output/example_secret.txt",
    ]

    for path in private_paths:
        result = _git("check-ignore", "-q", path)
        assert result.returncode == 0, f"{path} is not ignored"
