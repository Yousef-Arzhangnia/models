# Milestone M0 report: Setup
Date 2026-10-30, version 1.0

## 1. Goal

Create the repository layout, a single parameter file holding every value from `CONTEXT.md` with unit and source tag, a test framework, the tracker that every study reports to, the board (Home page) and one demo page, and show that a run started from the command line updates the board live.

## 2. What was built

- `pyproject.toml`: package `u4` with pinned dependencies (numpy 2.1.3, scipy 1.14.1, matplotlib 3.9.2, pandas 2.2.3, pyyaml 6.0.2, streamlit 1.41.1, plotly 5.24.1, pillow 11.0.0; pytest 8.3.3 as dev extra). Python 3.10 to 3.13.
- `params.yaml`: every value of `CONTEXT.md` sections 1 to 7, the M1 prompt values and the M1 modelling placeholders. Each leaf has `value`, `unit`, `tag` and optionally `note` and `tbd`. Values are stored in lab units; `src/u4/params.py` converts to SI and rejects unknown units or missing tags. 47 entries are marked `tbd: true`.
- `src/u4/tracker.py`: SQLite store (`runs/status.sqlite`, WAL mode) with tables for runs, checks, results and artefacts (figures PNG and SVG, CSV data). `Run` is a context manager; every write is retried and wrapped so a tracker problem never stops a simulation. Progress writes are throttled to one per 0.2 s. A stop flag written by the board is checked on every `progress()` call. Runs end as passed, failed (an internal check failed), error or stopped.
- `src/u4/cli.py`: `python -m u4 list`, `python -m u4 run <study>`, `python -m u4 run m1`.
- `app/Home.py` (board) and `app/pages/00_Demo.py` (demo page), following `UI_SPEC.md` sections 4, 5 and 7. The board reads only the tracker database and `params.yaml`.
- `tests/test_m0.py`: params load and unit conversion, tracker round trip, stop flag.

Layout note: the repository root is `D:\personal\Oncoptic\models` (the existing git repository), used directly as `upgrade4-models/`.

## 3. Verification

| Check | Expected | Obtained | Result |
|---|---|---|---|
| `params.yaml` loads, every leaf has unit and tag | all valid | 160+ parameters, 47 TBD | pass |
| Unit conversion (1.3 ns, 8.4 J/cm², 0.2 /cm) | 1.3e-9 s, 8.4e4 J/m², 20 /m | same | pass |
| Tracker round trip (run, check, result) | status passed, values stored | same | pass |
| Stop flag from the board ends a run as "stopped" | stopped | stopped | pass |
| Demo run from the command line shows live progress on the board without reloading | progress advances | board showed "step 1", "step 6", "step 16", "step 21 of 30" at 6 s intervals (headless browser), run finished "passed" after 30.5 s | pass |

## 4. Key results

The infrastructure works end to end: a 30 s demo run started with `python -m u4 run demo` appeared on the board within one refresh and its progress bar advanced every 5 s without a page reload.

## 5. Assumptions and placeholders

- Values in `CONTEXT.md` without a tag were given the most likely tag and a note saying so: water path 12.8 to 13.5 mm ([M], also marked TBD because the reference point, apex or rim, is not stated), chamber depth 100 µm ([S]), requirements such as the 42.8 dB target ([S]).
- The full TBD list is in the M1 report, section 5, and live on the board under "Open values".

## 6. Limits of validity

The board refreshes by polling every 5 s. Runs killed without a clean exit stay "running" until they are 6 h old and are then marked as error.

## 7. Recommendation

M0 is complete. M1 was started in the same session as instructed in the kickoff prompt.
