"""M0 demo: a 30 s run that shows live progress on the board. Usage: python scripts/demo_run.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "u4", "run", "demo"], cwd=ROOT, check=False)
