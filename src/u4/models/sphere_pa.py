"""Model 1: PA emission of a uniformly heated sphere (analytical).

Diebold, Khan, Park, Science 250 (1990) 101; Diebold, Sun, Khan, PRL 67 (1991) 3384.
Instantaneous (delta) heating, fluid sphere of radius a in a fluid. Frequency domain, numpy
sign convention (x(t) = integral X(f) exp(+i 2 pi f t) df), retarded time tau = t - r / c_f:

    P(w) = -i C N(q) exp(+i w a / c_f) / (q^2 D(q)),   C = p0 a^2 / (r c_s)
    N(q) = sin q - q cos q,   q = w a / c_s
    D(q) = (1 - rho_hat) sin q / q - cos q - i rho_hat c_hat sin q
    rho_hat = rho_s / rho_f, c_hat = c_s / c_f

In the matched case (rho_hat = c_hat = 1) this is the N-shaped pulse
    p(r, tau) = p0 / (2 r) * (-c tau)   for |tau| < a / c,
of length T = d / c, with spectral zeros where tan q = q, i.e. f = 1.4303 c/d, 2.4590 c/d, ...
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .common import Check, Grid

MODEL = "1"


def tanx_roots(n: int = 3) -> np.ndarray:
    """First n positive roots of tan x = x (excluding 0)."""
    out = []
    for k in range(1, n + 1):
        lo, hi = k * np.pi + 1e-9, (k + 0.5) * np.pi - 1e-9
        out.append(brentq(lambda x: np.sin(x) - x * np.cos(x), lo, hi, xtol=1e-14))
    return np.array(out)


def gap_constants(n: int = 3) -> np.ndarray:
    """k_n such that the n-th spectral zero is at f = k_n c / d."""
    return tanx_roots(n) / np.pi


def gap_frequencies(d: float, c_s: float, n: int = 3) -> np.ndarray:
    return gap_constants(n) * c_s / d


def spectrum(f: np.ndarray, d: float, c_s: float, p0: float, r: float,
             c_f: float | None = None, rho_s: float | None = None, rho_f: float | None = None) -> np.ndarray:
    """Pressure spectrum (Pa/Hz) at distance r, retarded time reference r / c_f."""
    a = d / 2
    c_f = c_s if c_f is None else c_f
    rho_hat = 1.0 if (rho_s is None or rho_f is None) else rho_s / rho_f
    c_hat = c_s / c_f
    w = 2 * np.pi * np.asarray(f, dtype=float)
    q = w * a / c_s
    small = q < 1e-4
    qs = np.where(small, 1.0, q)
    n_over_q2 = np.where(small, q / 3 - q ** 3 / 30, (np.sin(qs) - qs * np.cos(qs)) / qs ** 2)
    sinc = np.where(small, 1 - q ** 2 / 6, np.sin(qs) / qs)
    D = (1 - rho_hat) * sinc - np.cos(q) - 1j * rho_hat * c_hat * np.sin(q)
    C = p0 * a ** 2 / (r * c_s)
    return -1j * C * n_over_q2 * np.exp(1j * w * a / c_f) / D


def n_pulse(t: np.ndarray, d: float, c: float, p0: float, r: float) -> np.ndarray:
    """Exact matched-case time signal (Diebold N-wave), retarded time t."""
    a = d / 2
    return np.where(np.abs(t) < a / c, p0 / (2 * r) * (-c * t), 0.0)


def peak_pressure(d: float, p0: float, r: float) -> float:
    return p0 * (d / 2) / (2 * r)


def find_zeros(f: np.ndarray, mag: np.ndarray, targets: np.ndarray, rel_window: float = 0.08) -> np.ndarray:
    """Locate spectral minima of |mag| near each target frequency (parabolic refinement)."""
    out = []
    for ft in targets:
        sel = np.where((f > ft * (1 - rel_window)) & (f < ft * (1 + rel_window)))[0]
        if sel.size < 3:
            out.append(np.nan)
            continue
        i = sel[np.argmin(mag[sel])]
        if 0 < i < len(f) - 1:
            y0, y1, y2 = np.log(mag[i - 1] + 1e-300), np.log(mag[i] + 1e-300), np.log(mag[i + 1] + 1e-300)
            den = y0 - 2 * y1 + y2
            shift = 0.5 * (y0 - y2) / den if den != 0 else 0.0
            out.append(f[i] + np.clip(shift, -1, 1) * (f[1] - f[0]))
        else:
            out.append(f[i])
    return np.array(out)


def pulse_length(t: np.ndarray, p: np.ndarray, rel: float = 1e-9) -> float:
    idx = np.where(np.abs(p) > rel * np.abs(p).max())[0]
    return float(t[idx[-1]] - t[idx[0]] + (t[1] - t[0]))


def checks(P) -> list[Check]:
    grid = Grid.from_params(P)
    c = P.si("cell.sound_speed")
    out: list[Check] = []

    k = gap_constants(3)
    k_ctx = np.array(P.value("physics.gap_constants"))
    err = np.max(np.abs(k - k_ctx) / k_ctx)
    out.append(Check(MODEL, "Roots of tan x = x reproduce gap constants 1.4303, 2.4590, 3.4709",
                     err < 1e-4, ", ".join(f"{v:.4f}" for v in k_ctx), ", ".join(f"{v:.4f}" for v in k),
                     note="[L, Diebold 1990]"))

    for d in P.si("cell.test_diameters"):
        r = 1e-3
        spec = spectrum(grid.f, d, c, 1.0, r)
        zeros = find_zeros(grid.f, np.abs(spec), gap_frequencies(d, c, 3))
        rel = np.abs(zeros / gap_frequencies(d, c, 3) - 1)
        out.append(Check(MODEL, f"Gap positions at 1.43, 2.46, 3.47 c/d (d = {d*1e6:.0f} µm), within 0.5 %",
                         bool(np.all(rel < 0.005)),
                         ", ".join(f"{v/1e6:.1f}" for v in gap_frequencies(d, c, 3)) + " MHz",
                         ", ".join(f"{v/1e6:.1f}" for v in zeros) + " MHz"))
        p_num = grid.to_time(spec)
        p_ex = n_pulse(grid.t, d, c, 1.0, r)
        T_num = pulse_length(grid.t, p_ex)
        # pulse length from the numerical (FFT) signal: width where |p| above 2 % of peak, plus edges
        T_fft = _support_from_fft(grid.t, p_num)
        out.append(Check(MODEL, f"Ideal pulse length equals d/c (d = {d*1e6:.0f} µm), within 2 %",
                         abs(T_fft / (d / c) - 1) < 0.02, f"{d/c*1e9:.2f} ns", f"{T_fft*1e9:.2f} ns"))
        rel_err = np.max(np.abs(p_num - p_ex)) / np.max(np.abs(p_ex))
        mid = np.abs(grid.t) < 0.9 * d / 2 / c
        rel_mid = np.max(np.abs(p_num[mid] - p_ex[mid])) / np.max(np.abs(p_ex))
        out.append(Check(MODEL, f"Frequency-domain solution equals exact N-wave in the matched case (d = {d*1e6:.0f} µm)",
                         rel_mid < 0.01, "< 1 % away from the pulse edges",
                         f"{rel_mid*100:.3f} % (edges incl. Gibbs: {rel_err*100:.0f} %)"))

    # mismatched case: causality and unchanged zeros
    d = P.si("cell.test_diameters")[-1]
    spec = spectrum(grid.f, d, c, 1.0, 1e-3, c_f=1480.0, rho_s=1100.0, rho_f=1000.0)
    p = grid.to_time(spec)
    early = grid.t < -(d / 2) / 1480.0 - 0.2e-9
    leak = np.sqrt(np.sum(p[early] ** 2) / np.sum(p ** 2))
    zeros = find_zeros(grid.f, np.abs(spec), gap_frequencies(d, c, 2))
    rel = np.max(np.abs(zeros / gap_frequencies(d, c, 2) - 1))
    out.append(Check(MODEL, "Mismatched sphere (c_s/c_f = 1.05, rho_s/rho_f = 1.1): causal, zeros unchanged",
                     leak < 1e-3 and rel < 0.005, "no signal before first arrival; zeros within 0.5 %",
                     f"pre-arrival energy {leak:.1e}; zero error {rel*100:.2f} %"))

    T12 = 12e-6 / 1550.0
    out.append(Check(MODEL, "CONTEXT.md example: 12 µm at 1550 m/s gives 7.7 ns",
                     abs(T12 * 1e9 - P.value("physics.pulse_length_12um_1550")) < 0.05,
                     f"{P.value('physics.pulse_length_12um_1550')} ns", f"{T12*1e9:.2f} ns"))
    return out


def _support_from_fft(t, p):
    # Gibbs ripple makes the 'nonzero' support ill-defined; use the zero crossing structure instead:
    # positive lobe starts at the first sample above 50 % of the peak, ramps linearly; extrapolate the
    # linear ramp to its end points from the samples between 25 % and 75 % of the extremes.
    i_max, i_min = np.argmax(p), np.argmin(p)
    # the N-wave is linear between its extremes: fit a line and extend to +/- extreme values
    sel = np.arange(min(i_max, i_min), max(i_max, i_min) + 1)
    core = sel[np.abs(p[sel]) < 0.8 * np.abs(p).max()]
    slope, icpt = np.polyfit(t[core], p[core], 1)
    p_hi, p_lo = p[i_max], p[i_min]
    # ends of the linear ramp where it reaches the true (Gibbs-free) extremes: amplitude from the fit
    amp = max(abs(slope * t[i_max] + icpt), abs(slope * t[i_min] + icpt))
    return 2 * amp / abs(slope)
