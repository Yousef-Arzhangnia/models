# Upgrade 4 models (OR-PAM)

Read `PROJECT_INSTRUCTIONS.md`, `CONTEXT.md`, `MODELS_ROADMAP.md` and `UI_SPEC.md` first.

## Install (once)

```
cd D:\personal\Oncoptic\models
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Start the board

```
streamlit run app/Home.py
```

## Run studies (from a second terminal, with the venv active)

```
python -m u4 list            # all studies
python -m u4 run demo        # 30 s demo run: watch it on the board
python -m u4 run m1          # all M1 studies (about 20 s)
python scripts/m1_report_figures.py   # M1 studies + copy figures to reports/figures
pytest                       # verification checks
```

Runs, logs and figures go to `runs/` (not in git). Reports are in `reports/`.

If `runs/` sits on a network drive where SQLite cannot lock files, set `U4_RUNS_DIR` to a local folder
before starting both the board and the studies (for example `set U4_RUNS_DIR=C:\u4runs`).
