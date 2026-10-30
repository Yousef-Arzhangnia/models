"""Repository paths. U4_ROOT overrides the detected repository root."""
from __future__ import annotations

import os
from pathlib import Path


def _find_root() -> Path:
    env = os.environ.get("U4_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in [Path.cwd(), *here.parents]:
        if (parent / "params.yaml").exists() and (parent / "src" / "u4").exists():
            return parent
    return here.parents[2]


ROOT = _find_root()
PARAMS_FILE = ROOT / "params.yaml"
RUNS_DIR = Path(os.environ["U4_RUNS_DIR"]).resolve() if os.environ.get("U4_RUNS_DIR") else ROOT / "runs"
DB_FILE = RUNS_DIR / "status.sqlite"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
