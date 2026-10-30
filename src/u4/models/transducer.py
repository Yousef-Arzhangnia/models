"""Model 10: transducer response and focal geometry.

Electromechanical response: log-Gaussian magnitude with the -6 dB (half-amplitude) edges placed exactly
at the certificate band, peak 1 at the centre frequency, zero at DC; minimum phase (real cepstrum), so
the impulse response is causal and rings like a real narrow-band transducer.
    |H_T(f)| = exp(-ln2 (ln(f/fc) / w)^2),  w = ln(fc/f_lo) below fc, ln(f_hi/fc) above.
Receive sensitivity S (V/Pa into the preamp) multiplies the face-averaged pressure.

Focal geometry (on-axis point source, spherical cap of radius of curvature R and aperture radius A):
the face-averaged pressure is p(R_app, t) convolved with the spatial impulse response
    h_SIR(t) = sum_i w_i delta(t - dtau_i),  w_i = area fraction of annulus i,
where dtau_i is the ray travel-time difference (Snell refraction through the PMMA plate) between annulus
i and the axial ray. Paraxially the source appears at R_app = W + L c_p / c_w; the cap is in focus when
R_app = R, i.e. at a water distance W_focus = R - L c_p / c_w. 'at_focus' sets h_SIR = delta.
"""
from __future__ import annotations

import numpy as np
from scipy import fft as sfft
from scipy.optimize import brentq

from .common import Check, Grid

MODEL = "10"


def magnitude(f: np.ndarray, fc: float, f_lo: float, f_hi: float) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    out = np.zeros_like(f)
    pos = f > 0
    lf = np.log(f[pos] / fc)
    w = np.where(lf < 0, np.log(fc / f_lo), np.log(f_hi / fc))
    out[pos] = np.exp(-np.log(2) * (lf / w) ** 2)
    return out


def min_phase(mag_rfft: np.ndarray, n: int, floor: float = 1e-12) -> np.ndarray:
    """Minimum-phase spectrum (rfft layout) with the given magnitude, via the folded real cepstrum."""
    full = np.concatenate([mag_rfft, mag_rfft[-2:0:-1]]) if n % 2 == 0 else np.concatenate([mag_rfft, mag_rfft[:0:-1]])
    logm = np.log(np.maximum(full, floor))
    cep = sfft.ifft(logm).real
    fold = np.zeros(n)
    fold[0] = cep[0]
    fold[1:n // 2] = 2 * cep[1:n // 2]
    if n % 2 == 0:
        fold[n // 2] = cep[n // 2]
    H = np.exp(sfft.fft(fold))
    return H[: n // 2 + 1] * (mag_rfft > 0)


def response(grid: Grid, fc: float, f_lo: float, f_hi: float) -> np.ndarray:
    return min_phase(magnitude(grid.f, fc, f_lo, f_hi), grid.n)


def ray_delays(A: float, R: float, W: float, L: float, c_w: float, c_p: float, n_annuli: int = 400):
    """Travel-time differences (s) and area weights for annuli of a spherical cap.

    A aperture radius, R radius of curvature, W water distance apex to plate, L plate thickness.
    Source on axis at the far face of the plate (cell on the floor of the slide)."""
    edges = np.linspace(0.0, A, n_annuli + 1)
    rho = 0.5 * (edges[1:] + edges[:-1])
    drho = np.diff(edges)
    cos_cap = np.sqrt(1 - (rho / R) ** 2)
    wts = rho * drho / cos_cap
    wts = wts / wts.sum()
    sag = R - np.sqrt(R ** 2 - rho ** 2)
    tau0 = W / c_w + (L / c_p if L > 0 else 0.0)
    taus = np.empty_like(rho)
    for i, (r_i, h_i) in enumerate(zip(rho, sag)):
        Wi = W - h_i
        if L <= 0:
            taus[i] = np.hypot(r_i, Wi) / c_w
            continue
        th_max = np.arcsin(min(1.0, c_w / c_p)) - 1e-9

        def lateral(tw):
            tp = np.arcsin(np.clip(c_p / c_w * np.sin(tw), -1, 1))
            return Wi * np.tan(tw) + L * np.tan(tp) - r_i

        tw = brentq(lateral, 0.0, th_max) if r_i > 0 else 0.0
        tp = np.arcsin(c_p / c_w * np.sin(tw))
        taus[i] = Wi / (c_w * np.cos(tw)) + L / (c_p * np.cos(tp))
    return taus - tau0, wts


def sir_spectrum(f: np.ndarray, dtau: np.ndarray, wts: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    out = np.zeros(f.shape, dtype=complex)
    sel = np.ones(f.shape, bool) if mask is None else mask
    fs = f[sel]
    acc = np.zeros(fs.shape, dtype=complex)
    for k in range(0, len(dtau), 50):
        acc += (wts[k:k + 50, None] * np.exp(-2j * np.pi * dtau[k:k + 50, None] * fs[None, :])).sum(axis=0)
    out[sel] = acc
    return out


def apparent_distance(W: float, L: float, c_w: float, c_p: float) -> float:
    return W + (L * c_p / c_w if L > 0 else 0.0)


def focus_water_distance(R: float, L: float, c_w: float, c_p: float) -> float:
    return R - (L * c_p / c_w if L > 0 else 0.0)


def checks(P) -> list[Check]:
    from . import water
    out = []
    g = Grid.from_params(P)
    fc = P.si("today.transducer.centre_frequency")
    lo, hi = P.si("today.transducer.band_6db")
    mag = magnitude(g.f, fc, lo, hi)
    # -6 dB edges from the model
    i_pk = np.argmax(mag)
    below, above = g.f[:i_pk], g.f[i_pk:]
    e_lo = np.interp(0.5, mag[:i_pk], below)
    e_hi = np.interp(-0.5, -mag[i_pk:], above)
    out.append(Check(MODEL, "Model reproduces certificate: centre 20.0 MHz, -6 dB 15.9 to 26.2 MHz",
                     abs(g.f[i_pk] - fc) < 0.5e6 and abs(e_lo - lo) < 0.1e6 and abs(e_hi - hi) < 0.1e6,
                     f"{fc/1e6:.1f}; {lo/1e6:.1f} to {hi/1e6:.1f} MHz [M, certificate]",
                     f"{g.f[i_pk]/1e6:.1f}; {e_lo/1e6:.2f} to {e_hi/1e6:.2f} MHz"))
    H = min_phase(mag, g.n)
    h = g.to_time(H)
    pre = np.sum(h[g.t < -1e-9] ** 2) / np.sum(h ** 2)
    out.append(Check(MODEL, "Minimum-phase impulse response is causal and keeps the magnitude",
                     pre < 1e-6 and np.max(np.abs(np.abs(H) - mag)) < 1e-6,
                     "energy before t = 0 < 1e-6", f"{pre:.1e}"))
    # focal geometry: no plate, source at R -> no spread; plate: numerical focus equals paraxial formula
    T = P.value("today.sample.water_temperature")
    c_w, c_p = water.sound_speed(P, T), P.si("pmma.sound_speed")
    A, R = P.si("today.transducer.element_diameter") / 2, P.si("today.transducer.roc")
    dt, _ = ray_delays(A, R, R, 0.0, c_w, c_p)
    out.append(Check(MODEL, "Point source at the geometric focus (no plate): all rays arrive together",
                     np.ptp(dt) < 1e-12, "spread 0 ns", f"{np.ptp(dt)*1e9:.2e} ns"))
    L = P.si("today.sample.pmma_thickness")
    Ws = np.linspace(R - 3e-3, R + 1e-3, 81)
    spreads = [np.ptp(ray_delays(A, R, W, L, c_w, c_p, 200)[0]) for W in Ws]
    W_num = Ws[int(np.argmin(spreads))]
    W_par = focus_water_distance(R, L, c_w, c_p)
    out.append(Check(MODEL, "Focus through 0.7 mm PMMA: numerical best focus near paraxial R - L c_p/c_w",
                     abs(W_num - W_par) < 0.25e-3, f"{W_par*1e3:.2f} mm (paraxial)",
                     f"{W_num*1e3:.2f} mm (ray trace, min spread {min(spreads)*1e9:.1f} ns)",
                     note="Difference is spherical aberration of the plate at 14° half-angle."))
    return out
