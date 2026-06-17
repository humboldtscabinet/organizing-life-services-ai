"""Repo-local Python startup hooks.

This file is intentionally quiet for normal app/test processes. It only enables
the one-off data script mutation guard when Python is executing a target under
the repo's data/ directory, including `python -m data.some_script`.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _running_data_script() -> bool:
    if not sys.argv:
        return False

    target = Path(sys.argv[0])
    if not target.suffix == ".py":
        return False

    try:
        resolved = target.resolve()
    except OSError:
        return False

    repo_root = Path(__file__).resolve().parent
    data_dir = repo_root / "data"

    try:
        resolved.relative_to(data_dir)
    except ValueError:
        return False
    return True


if _running_data_script():
    from data._mutation_guard import activate

    activate()
