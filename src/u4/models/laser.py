"""Model 5: laser pulse shape and duration.

The emitted pressure is the delta-heating response convolved with the normalised heating rate I(t)
(unit area). In frequency this is a multiplication by H_L(f) = FT{I}(f), a low-pass filter.
  gaussian:  I ~ exp(-4 ln2 t^2 / tau^2),  H_L = exp(-(pi f tau)^2 / (4 ln 2)),  -6 dB at 0.441 / tau
  sech2:     I ~ sech^2(t / T0), tau = 1.7627 T0, H_L = (pi^2 T0 f) / sinh(pi^2 T0 f)
  tophat:    I = 1/tau for |t| < tau/2,  H_L = sinc(f tau)
Zero-phase: the heating pulse is centred on tau = 0.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .common import Check, Grid

MODEL = "5"
SHAPES = ("gaussian", "sech2", "tophat")
_SECH_FWHM = 2 * np.arccosh(np.sqrt(2))  # 1.7627


def pulse(t: np.ndarray, fwhm: float, shape: str = "gaussian") -> np.ndarray:
    """Normalised heating rate (1/s), unit area."""
    if shape == "gaussian":
        s = fwhm / (2 * np.sqrt(2 * np.log(2)))
        return np.exp(-t ** 2 / (2 * s ** 2)) / (s * np.sqrt(2 * np.pi))
    if shape == "sech2":
        T0 = fwhm / _SECH_FWHM
        e = np.exp(-2 * np.abs(t / T0))
        return 4 * e / (1 + e) ** 2 / (2 * T0)
    if shape == "tophat":
        # edge samples weighted by their overlap with the pulse, so the discrete area is exactly 1
        dt = np.median(np.diff(t)) if np.size(t) > 1 else fwhm
        w = np.clip((fwhm / 2 - np.abs(t)) / dt + 0.5, 0.0, 1.0)
        return w / fwhm
    raise ValueError(f"unknown pulse shape {shape}")


def filter_response(f: np.ndarray, fwhm: float, shape: str = "gaussian") -> np.ndarray:
    f = np.asarray(f, dtype=float)
    if shape == "gaussian":
        return np.exp(-(np.pi * f * fwhm) ** 2 / (4 * np.log(2)))
    if shape == "sech2":
        x = np.pi ** 2 * (fwhm / _SECH_FWHM) * f
        xs = np.where(x < 1e-8, 1.0, x)
        return np.where(x < 1e-8, 1.0, xs / np.sinh(np.clip(xs, None, 700)))
    if shape == "tophat":
        return np.sinc(f * fwhm)
    raise ValueError(f"unknown pulse shape {shape}")


def cutoff(fwhm: float, shape: str = "gaussian", level: float = 0.5) -> float:
    """Frequency where |H_L| first falls to `level` (amplitude ratio; 0.5 = half amplitude, -6.02 dB)."""
    lvl = level
    return brentq(lambda f: abs(filter_response(np.array([f]), fwhm, shape)[0]) - lvl, 1.0, 1.0 / fwhm)


def checks(P) -> list[Check]:
    out = []
    tau = P.si("today.laser.pulse_fwhm")
    fc = cutoff(tau, "gaussian")
    k = P.value("physics.laser_cutoff_factor")
    out.append(Check(MODEL, "Gaussian half-amplitude (-6 dB) frequency equals 0.441 / FWHM", abs(fc * tau - 0.4413) < 1e-3,
                     "0.4413", f"{fc*tau:.4f}", note="analytical: 2 ln2 / pi"))
    ref = P.si("physics.laser_cutoff_1p3ns")
    out.append(Check(MODEL, "CONTEXT.md: cut-off about 340 MHz at 1.3 ns", abs(fc / ref - 1) < 0.02,
                     f"{ref/1e6:.0f} MHz (0.44 / tau)", f"{fc/1e6:.1f} MHz", kind="external"))
    g = Grid.from_params(P)
    for shape in SHAPES:
        I = pulse(g.t, tau, shape)
        area = np.trapezoid(I, g.t)
        Hnum = np.abs(g.to_freq(I))
        Han = np.abs(filter_response(g.f, tau, shape))
        sel = g.f < 2e9
        err = np.max(np.abs(Hnum[sel] - Han[sel]))
        out.append(Check(MODEL, f"{shape}: unit area and analytical spectrum equals FFT of pulse",
                         abs(area - 1) < 1e-3 and err < 2e-2, "area 1, |dH| < 0.02 below 2 GHz",
                         f"area {area:.4f}, |dH| {err:.1e}"))
    return out
