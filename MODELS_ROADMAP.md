# Models roadmap: Upgrade 4

The work is split into milestones. Each ends with a report and a go / no-go decision by Yousef. Only one milestone is active at a time.

## Status

| Milestone | Status | Date | Report | Open issues |
|---|---|---|---|---|
| M0 Setup | done | 2026-10-30 | [M0 report](reports/M0_report.md) | Untagged CONTEXT.md values given assumed tags (water path [M], chamber depth [S], requirements [S]); confirm |
| M1 Analytical forward chain | done, awaiting review | 2026-10-30 | [M1 report](reports/M1_report.md) | 4 external checks fail: P1 water loss (6.9 vs 20 dB quoted), today's single-shot SNR -46/-51 dB vs -40 to -20 (placeholder µa, S), 7 µm loss 60.5 vs 50 dB; bead spectrum peak 17.8 vs 12 MHz; bead raw data not available; 47 TBD values |
| M2 Identifiability study | not started | | | |
| M3 Core-shell and echo library | not started | | | |
| M4 Joint inverse fit | not started | | | |
| M5 Synthetic populations and classifier | not started | | | |
| M6 Optical models (only if Upgrade 5 is selected) | not started | | | |

## Model list (numbering used in all reports)

| # | Model | Milestone |
|---|---|---|
| 1 | PA emission, uniform sphere (analytical) | M1 |
| 2 | PA emission, core-shell cell (1D radial solver; k-Wave-python check) | M3 |
| 3 | US scattering, sphere and concentric core-shell (layered Anderson partial-wave series) | M3 |
| 4 | Real cell shape: flattened, ellipsoidal | M4 |
| 5 | Laser pulse shape and duration | M1 |
| 6 | Beam profile at the cell, defocus | M4 |
| 7 | Absorbed energy and initial pressure | M1 (simple), M3 (per compartment) |
| 8 | Water path attenuation | M1 |
| 9 | Substrate, agar and reverberation | M3 |
| 10 | Transducer response and focal geometry | M1 |
| 11 | Electronics chain and LNA recovery | M1 (gain, noise), M3 (recovery) |
| 12 | Noise and averaging | M1 |
| 13 | Library generation and lookup | M3 |
| 14 | Joint PA + US fit with uncertainty | M4 |
| 15 | Sensitivity and identifiability | M2 |
| 16 | Photothermal response | M6 |
| 17 | Elastography response | M6 |
| 18 | Dose model | M6 |
| 19 | Synthetic Jurkat and T-cell datasets | M5 |
| 20 | Classifier | M5 |
| 21 | Batch-effect check | M5 |

## Milestones

### M0 Setup (small)
- Repository layout, `params.yaml` with every value from `CONTEXT.md` (unit and tag), test framework.
- Package skeleton, tracker, the board (Home page) and one demo page, as in `UI_SPEC.md`.
- **Done when:** the layout exists, `params.yaml` loads, one trivial test passes, and a demo run started from the command line shows live progress on the board.

### M1 Analytical forward chain (models 1, 5, 7 simple, 8, 10, 11, 12)
- Uniform-sphere PA pulse and spectrum, convolved with the laser pulse, through water, transducer and electronics, with noise and averaging.
- Two configurations: today's chain (20 MHz, 13 mm, 1.3 ns) and the Upgrade 1 chain (150 to 500 MHz, 0.3 mm, 0.5 ns).
- **Checks:** gap positions match 1.43 c/d and 2.46 c/d; the ideal pulse length matches d/c; today's chain reproduces the measured bead behaviour qualitatively (peak near 12 to 20 MHz, ringing of hundreds of ns); SNR estimates are consistent with the earlier -40 to -20 dB per shot.
- **Done when:** both chains produce waveforms, spectra and SNR for a 7 µm and a 12 µm sphere, all checks reported, and the six M1 pages from `UI_SPEC.md` work and show on the board.
- **From M2 on:** every milestone's "done" also requires a working page for each model it builds.

### M2 Identifiability study (model 15)
- Using M1: for each chain, pulse length and SNR, which parameters (d, c, gap positions, amplitude ratio) can be recovered, and with what error.
- **Key output:** the minimum bandwidth, pulse length and SNR needed to separate a 7 µm from a 12 µm cell, and to resolve nucleus versus cell size.
- **Gate:** decide whether the full core-shell fit (M3, M4) is justified or whether model-free features are enough at first.

### M3 Core-shell and echo library (models 2, 3, 7 per compartment, 9, 11 recovery, 13)
- Core-shell PA with a 1D radial wave solver in Python (finite differences or semi-analytical layered sphere); US scattering with the Anderson partial-wave series extended to concentric layers; library over the parameter grid.
- Floor and agar layer, and LNA recovery, with k-Wave-python (axisymmetric) as a check on how far the 1D library holds.
- **Checks:** the 1D core-shell solver reduces to the analytical uniform sphere when nucleus and cytoplasm are equal; the 1D solver and k-Wave-python agree for a free-standing sphere; reproduce P2's MCF7 and melanoma spectra and two-line results within their reported accuracy.

### M4 Joint inverse fit (models 4, 6, 14)
- Library lookup plus joint fit of PA (266 nm, 420 nm) and US to one cell, with error bars; effect of flattened shape and beam profile simulated with k-Wave-python (j-Wave if a gradient-based fit is chosen).
- **Checks:** recover known parameters from synthetic data with noise; report bias and spread.

### M5 Synthetic populations and classifier (models 19, 20, 21)
- Simulated Jurkat-like and T-cell-like populations with realistic spread; model-free and fitted features; logistic regression or random forest; split by day and dish; batch-effect injection.
- **Checks:** accuracy on held-out synthetic batches; feature importance makes physical sense.

### M6 Optical models (models 16, 17, 18), only if Upgrade 5 is selected
- Photothermal swelling and decay, elastography deformation, cumulative dose and temperature rise (FEniCSx or finite differences).
