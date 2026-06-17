import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_operational_shell_scripts_parse():
    scripts = [
        ROOT / "infra" / "backup" / "backup_postgres.sh",
        ROOT / "infra" / "backup" / "verify_postgres_backup.sh",
        ROOT / "infra" / "backup" / "backup_n8n.sh",
        ROOT / "infra" / "backup" / "verify_n8n_backup.sh",
        ROOT / "infra" / "backup" / "run_all_backups.sh",
        ROOT / "infra" / "backup" / "install_launchd_backups.sh",
        ROOT / "infra" / "postgres" / "apply_migrations.sh",
        ROOT / "infra" / "server" / "deploy_server.sh",
        ROOT / "infra" / "server" / "preflight.sh",
        ROOT / "infra" / "server" / "verify_local_llm.sh",
        ROOT / "infra" / "server" / "verify_stack.sh",
    ]

    for script in scripts:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
