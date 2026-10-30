"""Run all M1 studies through the tracker and copy their figures into reports/figures/.

Usage: python scripts/m1_report_figures.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from u4 import tracker  # noqa: E402
from u4.studies.m1 import M1_STUDIES  # noqa: E402

subprocess.run([sys.executable, "-m", "u4", "run", "m1"], cwd=ROOT, check=False)
out = ROOT / "reports" / "figures"
out.mkdir(parents=True, exist_ok=True)
for study in M1_STUDIES:
    rows = tracker.query("SELECT id FROM runs WHERE study=? ORDER BY started DESC LIMIT 1", (study,))
    if not rows:
        continue
    for a in tracker.run_artefacts(rows[0]["id"], "figure"):
        for p in (a["path"], a["path2"]):
            if p and Path(p).exists():
                shutil.copy(p, out / f"M1_{Path(p).name}")
                print("copied", Path(p).name)
