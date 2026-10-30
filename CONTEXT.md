# Context: OR-PAM platform and Upgrade 4

## 1. The goal

The OR-PAM platform (optical-resolution photoacoustic microscope, Oss lab) must measure single cells label-free and separate **Jurkat cells** (T-cell leukaemia line) from **healthy T lymphocytes**. The later goal is real-time drug-response assessment. Budget per cell: about 30 s. Acceptance SNR target: 42.8 dB per cell. Single-pulse damage threshold (ED50): 42 J/cm² for white blood cells, 90 J/cm² for K562 [L, project tolerance summary].

## 2. Today's instrument (as built)

| Item | Value |
|---|---|
| Laser | CryLaS FDSS532-Q3-IT, 532 nm, pulse < 1.3 ns, 1 to 2.5 kHz, 20 to 35 µJ, beam 0.4 mm, divergence < 5 mrad [S] |
| Objective | Thorlabs MY5X-802B, 5x, NA 0.14, f 40 mm; spot about 2.0 µm FWHM, DOF about ±13.6 µm [C] |
| Pulse energy at sample | 380 nJ, about 8.4 J/cm² peak [C] |
| Sample | Countess C10228 PMMA slide, chambers 100 µm deep; cells sit on the floor |
| Acoustic path | PMMA bottom wall about 0.7 mm [M], then 12.8 to 13.5 mm of water |
| Transducer | Precision Acoustics TXZ_1075B (PA3421), PVDF, 6 mm element, focused, ROC 12 mm; centre 20.0 MHz, -6 dB band 15.9 to 26.2 MHz [M, certificate] |
| Amplifiers | HP preamp 13.6 dB [M] + HA booster 27 dB [S] |
| Digitiser | AlazarTech ATS9352, 12-bit, 500 MS/s, 250 MHz bandwidth [S] |
| Trigger | Optical pickoff at the last fold mirror |
| Stage | Thorlabs NanoMax 300, XYZ |

**Status.** The system detects 10 µm absorbing beads (25 dB SNR with 1000 averages, arrival near 9.5 µs, spectrum peak near 12 MHz, band 10 to 13 MHz [M]). Cells are detected but Jurkat and T cells give the same featureless signal. Bead data from the first test (2026-09-05) is in the Oncoptic project folder under `reza/points` (manifest.json per run, 10,000 samples at 500 MS/s, 1000 shots per acquisition).

## 3. Why the cells look the same (root causes)

1. **Wrong colour.** Cells barely absorb 532 nm. DNA absorbs near 260 nm, cytochromes near 420 nm.
2. **Wrong pitch.** A 7 to 14 µm cell emits its size and structure information at roughly 100 to 500 MHz. The 20 MHz receiver behind 13 mm of water hears only the smooth low-frequency tail. Modelled loss from this mismatch: about 50 dB [C]. Single-shot SNR for an unstained cell: about -40 to -20 dB [C].

## 4. The upgrade programme (context for the models)

| Upgrade | What it adds | Relevance to modelling |
|---|---|---|
| 1 | Broadband 150 to 500 MHz transducer, open-top glass or quartz dish, agar layer, transducer 40 to 500 µm from the cell, digitiser of at least 4 GS/s, gold-film calibration | Defines the target receive chain and geometry |
| 2 | Sub-ns light source at 266 nm (nucleus), 420 nm (mitochondria), 532 nm (baseline); two colours per shot | Defines which compartment absorbs at each wavelength |
| 3 | Pulse-echo on the same transducer | Adds the US scattering model and the two-line (size, sound speed) fit |
| 4 | This project: spectral fitting and classification | All models below |
| 5 | Optical channels, functional OCT, dose control | Adds photothermal, elastography and dose models (optional, last) |

## 5. Physics that the models rest on

- **Ideal click.** A uniformly heated sphere emits an N-shaped pressure pulse of length T = d / c (12 µm at 1550 m/s gives 7.7 ns).
- **Spectral gaps.** Its spectrum is zero where tan x = x, at f = 1.43 c/d, 2.46 c/d, 3.47 c/d. The gaps are set by c/d only and are not moved by the instrument response (a zero stays a zero), which is why gap positions, not peaks, read out size.
- **Ambiguity.** PA gaps give c/d only. The US echo depends also on the size relative to the wavelength in the surrounding water, so it gives a second, different relation; the crossing of both gives d and c (P2: MCF7 17.5 µm, 1573 m/s, optical 16 µm).
- **Pulse length.** The laser pulse acts as a low-pass filter on the emitted spectrum, cut-off roughly 0.44 / pulse duration (about 340 MHz at 1.3 ns) [C].
- **Water attenuation.** Rises with f². P1 reports about 20 dB over 50 µm of water at 1 GHz and 37 °C [L, P1]. Use a literature coefficient with temperature dependence and tag it.
- **Calibration.** A 200 nm gold film emits a near-flat spectrum; dividing a cell spectrum by it removes the system response [L, P1].

## 6. Literature

| Tag | Reference | Used for |
|---|---|---|
| P1 | Strohm, Berndl, Kolios. High frequency label-free photoacoustic microscopy of single cells. Photoacoustics 1 (2013) 49 to 53 | UHF transducers (200, 375, 1200 MHz), inverted geometry, gold-film calibration, attenuation |
| P2 | Strohm, Berndl, Kolios. A photoacoustic technique to measure the properties of single cells. Proc. SPIE 8581 (2013) | PA plus US two-line method, core-shell FEM, MCF7 and melanoma values, agar layer |
| P3 | He et al. Sci. Rep. 6:39616 (2016) | Two wavelengths per shot, time-gating |
| P4 | Fukuzaki et al. PLOS ONE 10(4): e0123833 (2015) | Light-dose caution |
| P5 | Yao et al. Opt. Lett. 35(24) 4139 (2010) | DNA contrast at 266 nm |
| P6 | Zhang et al. J. Biomed. Opt. 18(2) 020504 (2013) | Cytochrome contrast near 420 nm |
| Model refs | Diebold, Khan, Park. Science 250 (1990) 101 (PA sphere); Anderson. J. Acoust. Soc. Am. 22 (1950) 426 (fluid sphere scattering) | Analytical forward models (both cited in P2) |

## 7. Values still open (use as placeholders, tag as TBD)

- Jurkat and resting T-cell diameters (literature suggests about 11 to 12 µm and about 7 µm; verify).
- Nucleus-to-cell ratio and mitochondrial load for both types.
- Sound speed and density of nucleus, cytoplasm and medium (cells about 1560 to 1575 m/s [L, P2]).
- Absorption coefficients per compartment at 266, 420 and 532 nm.
- Final UHF transducer model, centre frequency and focal length.
- Final laser pulse durations at 266 and 420 nm.
