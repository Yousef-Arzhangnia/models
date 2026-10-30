"""Model 11 (gain and noise only): amplifier chain and digitiser front end.

    H_E(f) = G * HP1(f) * LP1(f) * B_n(f)
G = 10^(sum gains / 20); HP1, LP1 first-order corners of the amplifier chain; B_n the digitiser analogue
bandwidth as an n-th order Butterworth. Input-referred white noise density of the first stage:
    e_n = sqrt(4 k_B T R_s F),  F = 10^(NF/10)
(thermal noise of the source resistance times the noise factor). LNA recovery after the laser pickoff is
model 11 part 2 (M3) and not included.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from .common import Check

MODEL = "11"
K_B = 1.380649e-23


def gains_db(P, preset: str) -> list[float]:
    if preset == "today":
        return [P.value("today.electronics.preamp_gain"), P.value("today.electronics.booster_gain")]
    return [P.value(f"{preset}.electronics.lna_gain")]


def total_gain(P, preset: str) -> float:
    return 10 ** (sum(gains_db(P, preset)) / 20)


def response(P, preset: str, f: np.ndarray, gain: bool = True) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    s = 2j * np.pi * f
    fh, fl = P.si(f"{preset}.electronics.highpass"), P.si(f"{preset}.electronics.lowpass")
    H = (s / (2 * np.pi * fh)) / (1 + s / (2 * np.pi * fh)) / (1 + s / (2 * np.pi * fl))
    fb, nb = P.si(f"{preset}.digitiser.bandwidth"), int(P.value(f"{preset}.digitiser.bandwidth_order"))
    b, a = signal.butter(nb, 2 * np.pi * fb, analog=True)
    _, Hb = signal.freqs(b, a, worN=2 * np.pi * f)
    H = H * Hb
    return H * total_gain(P, preset) if gain else H


def noise_density(P, preset: str) -> float:
    """Input-referred voltage noise density (V/sqrt(Hz))."""
    T = P.si(f"{preset}.electronics.noise_temperature")
    R = P.si(f"{preset}.electronics.source_resistance")
    F = 10 ** (P.value(f"{preset}.electronics.noise_figure") / 10)
    return float(np.sqrt(4 * K_B * T * R * F))


def checks(P) -> list[Check]:
    out = []
    e0 = np.sqrt(4 * K_B * 295 * 50)
    out.append(Check(MODEL, "Thermal noise of 50 ohm at 295 K equals 0.90 nV/sqrt(Hz)", abs(e0 * 1e9 - 0.903) < 0.005,
                     "0.903 nV/√Hz (4 k T R)", f"{e0*1e9:.3f} nV/√Hz"))
    g_t = 20 * np.log10(total_gain(P, "today"))
    out.append(Check(MODEL, "Today's gain 13.6 dB + 27 dB = 40.6 dB", abs(g_t - 40.6) < 1e-9, "40.6 dB", f"{g_t:.1f} dB"))
    f = np.array([1e3, 20e6, P.si("today.digitiser.bandwidth")])
    H = np.abs(response(P, "today", f, gain=False))
    Pd = P.with_overrides({"today.electronics.lowpass": 1e9, "today.electronics.highpass": 1e-9})
    Hd = np.abs(response(Pd, "today", f, gain=False))
    ok = abs(H[1] - 1) < 0.01 and abs(20 * np.log10(Hd[2]) + 3.01) < 0.05
    out.append(Check(MODEL, "Today's chain flat at 20 MHz; digitiser filter alone -3 dB at 250 MHz", ok,
                     "0 dB at 20 MHz; -3.01 dB at 250 MHz",
                     f"{20*np.log10(H[1]):.2f} dB; {20*np.log10(Hd[2]):.2f} dB "
                     f"(whole chain {20*np.log10(H[2]):.2f} dB incl. 500 MHz amplifier pole)"))
    return out
