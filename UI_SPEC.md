# UI and board specification: Upgrade 4 modelling

One Python package, one command, three parts: a live **board**, a **page per model**, and a **tracker** that every simulation reports to.

## 1. Technology

- **Streamlit** multipage app (open source), with **Plotly** for interactive plots. Pin versions in `pyproject.toml`.
- Install with `pip install -e .`, start with `streamlit run app/Home.py`. The board opens in the browser.
- Long simulations run outside the UI from the command line (`python -m u4 run <study>`), so closing the browser never stops a run. They report through the tracker, and the board shows them live.

## 2. Package layout

```
upgrade4-models/
  pyproject.toml
  params.yaml
  src/u4/
    models/            one module per model family (sphere_pa.py, chain.py, noise.py, ...)
    tracker.py         run status store (see section 3)
    cli.py             python -m u4 run <study>
  app/
    Home.py            the board
    pages/
      01_PA_sphere.py
      05_Laser_pulse.py
      08_Water_attenuation.py
      10_Transducer.py
      12_Noise_SNR.py
      M1_Chain_comparison.py
      ...              one page per model, added milestone by milestone
  runs/                status.sqlite, logs, results, figures (git-ignored)
  reports/             milestone reports
```

## 3. Tracker (how the board stays up to date)

A small module that every script and study uses:

```python
from u4.tracker import Run
with Run(model="1", study="sphere_gap_check", params=p) as run:
    for i, d in enumerate(diameters):
        ...
        run.progress(i / len(diameters), f"d = {d*1e6:.1f} um")
    run.check("gap_1 within 0.5 % of 1.43 c/d", passed=True, value=0.12)
    run.result(key="first_gap_MHz", value=184.7, tag="[C]")
    run.figure(fig, name="spectrum")
```

- Stores runs in `runs/status.sqlite`: run id, model number, milestone, study name, parameters, start and end time, status (queued, running, passed, failed, error), progress 0 to 1, current message, verification checks, key results, figure paths, log file.
- Safe for several runs at once; never blocks the simulation.

## 4. Board (Home page)

Auto-refreshes every 5 s while any run is active.

1. **Header:** project name, active milestone, overall progress bar (models passed / models in this milestone).
2. **Live runs:** each running study with progress bar, current message, elapsed time and estimated remaining time, last 10 log lines on expand, and a stop button that writes a stop flag the run checks.
3. **Milestone lanes M0 to M6:** each model as a card with:
   - number and name;
   - status chip: not started, building, verifying, passed, failed, blocked;
   - last run time;
   - verification checks (count passed / total);
   - one headline result, e.g. "first gap 184.7 MHz [C]";
   - a link to its page and to the milestone report.

   Future milestones are shown greyed out.
4. **Recent figures:** the last 6 figures from any run, each linking to its model page.
5. **Open values:** every TBD entry in `params.yaml`, with the placeholder value used and its tag.
6. **Status source:** the board reads only the tracker database and `params.yaml`, and never runs simulations itself.

## 5. Model pages (same layout for every model)

1. **What it models:** two or three sentences, the governing equation(s), assumptions, references (tags P1 to P6 or model refs).
2. **Inputs:** sliders and fields prefilled from `params.yaml`, each showing its unit and source tag; "reset to params.yaml".
3. **Run:** quick runs (under about 10 s) execute in the page; longer ones are started as a background study and appear on the board.
4. **Outputs:** interactive plots appropriate to the model (time domain, spectrum, maps, tables), with axis units.
5. **Verification:** the model's checks with expected value, obtained value, pass or fail.
6. **History:** previous runs of this model from the tracker, selectable to overlay or compare.
7. **Export:** download of figures (PNG, SVG) and data (CSV).
8. **Links:** source file of the model, its tests, the milestone report.

## 6. Pages needed in M1

| Page | Inputs | Outputs |
|---|---|---|
| 01 PA sphere | diameter, sound speed | ideal N-pulse; spectrum with gap markers; gap table vs 1.43 c/d, 2.46 c/d |
| 05 Laser pulse | pulse duration, shape | pulse in time; its spectrum as a filter; effect on the sphere spectrum |
| 08 Water attenuation | path length, temperature | loss in dB versus frequency |
| 10 Transducer | preset (today 20 MHz, P1 375 MHz) or custom centre and bandwidth | response curve; filtered pulse |
| 12 Noise and SNR | noise level, averages, digitiser bits | single-shot and averaged SNR; noisy example trace |
| M1 Chain comparison | cell diameter, chain preset | waveform and spectrum through today's chain and the Upgrade 1 chain side by side, SNR for each |

## 7. Look

Clean, technical, light and dark theme. Status colours: green passed, amber verifying or blocked, red failed, grey not started. Numbers in a monospaced font with units.
