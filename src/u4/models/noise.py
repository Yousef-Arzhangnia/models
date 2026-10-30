"""Model 12: noise and averaging.

Noise at the digitiser input = amplified first-stage noise (PSD e_n^2 |H_E|^2, folded into the first
Nyquist zone of the digitiser) + quantisation (LSB^2 / 12) + intrinsic ADC noise. SNR is reported as
    SNR = 20 log10( max|s(t)| / sigma )
on (a) the raw digitised trace and (b) after a zero-phase digital band-pass over the band where the
clean received spectrum is within 20 dB of its peak. With N uncorrelated shots: SNR_N = SNR_1 + 10 log10 N
(jitter and drift ignored).
"""
from __future__ import annotations

import numpy as np

from .common import Check

MODEL = "12"


def lsb(full_scale: float, bits: int) -> float:
    return 2 * full_scale / 2 ** bits


def folded_psd(f: np.ndarray, psd: np.ndarray, fs_dig: float, n_dig: int) -> tuple[np.ndarray, np.ndarray]:
    """Fold a one-sided PSD (V^2/Hz on grid f) into the digitiser's first Nyquist zone.
    Returns digitiser rfft frequencies and the folded one-sided PSD on them."""
    fd = np.fft.rfftfreq(n_dig, 1 / fs_dig)
    dfd = fd[1] - fd[0]
    fa = np.abs(((f + fs_dig / 2) % fs_dig) - fs_dig / 2)
    df = f[1] - f[0]
    idx = np.clip(np.round(fa / dfd).astype(int), 0, len(fd) - 1)
    power = np.bincount(idx, weights=psd * df, minlength=len(fd))
    return fd, power / dfd


def sigma(fd: np.ndarray, psd_fold: np.ndarray, q_lsb: float, adc_noise_lsb: float, band: tuple | None = None) -> float:
    """rms noise (V) over the full digitiser band, or over band = (f_lo, f_hi)."""
    dfd = fd[1] - fd[0]
    sel = np.ones_like(fd, bool) if band is None else (fd >= band[0]) & (fd <= band[1])
    var_amp = np.sum(psd_fold[sel]) * dfd
    var_q = (q_lsb ** 2 / 12 + (adc_noise_lsb * q_lsb) ** 2) * (np.sum(sel) / len(fd))
    return float(np.sqrt(var_amp + var_q))


def snr_db(peak: float, sig: float) -> float:
    return float(20 * np.log10(max(peak, 1e-300) / sig))


def averaged_snr_db(snr1_db: float, n: int) -> float:
    return float(snr1_db + 10 * np.log10(n))


def averages_needed(snr1_db: float, target_db: float) -> float:
    return float(10 ** ((target_db - snr1_db) / 10))


def mc_average_gain(n_avg: int = 100, n_samp: int = 4000, n_trials: int = 20, seed: int = 1) -> float:
    """Monte Carlo: rms of the mean of n_avg white-noise shots, as an SNR gain in dB."""
    rng = np.random.default_rng(seed)
    ratios = []
    for _ in range(n_trials):
        shots = rng.standard_normal((n_avg, n_samp))
        ratios.append(1.0 / np.std(shots.mean(axis=0)))
    return float(20 * np.log10(np.mean(ratios)))


def quantise(x: np.ndarray, q: float, full_scale: float) -> np.ndarray:
    return np.clip(np.round(x / q) * q, -full_scale, full_scale)


def checks(P) -> list[Check]:
    out = []
    g = mc_average_gain(100, seed=int(P.value("simulation.noise_seed")))
    out.append(Check(MODEL, "Averaging 100 independent shots improves SNR by 20 dB (Monte Carlo)", abs(g - 20) < 0.3,
                     "20.0 dB", f"{g:.2f} dB"))
    rng = np.random.default_rng(2)
    q = 1e-3
    x = rng.uniform(-0.3, 0.3, 200000)
    err = np.std(quantise(x, q, 1.0) - x)
    out.append(Check(MODEL, "Quantisation noise equals LSB / sqrt(12)", abs(err / (q / np.sqrt(12)) - 1) < 0.02,
                     f"{q/np.sqrt(12)*1e6:.1f} µV", f"{err*1e6:.1f} µV"))
    # folding conserves variance
    f = np.linspace(0, 50e9, 500001)
    psd = np.where(f < 3e9, 1e-17, 0.0)
    fd, pf = folded_psd(f, psd, 8e9, 4000)
    var_in, var_out = np.sum(psd) * (f[1] - f[0]), np.sum(pf) * (fd[1] - fd[0])
    out.append(Check(MODEL, "Aliasing (folding) conserves noise power", abs(var_out / var_in - 1) < 1e-6,
                     "ratio 1", f"{var_out/var_in:.6f}"))
    return out
