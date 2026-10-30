"""Model 8: water path attenuation (plus the PMMA floor of today's slide).

Water, f^2 law (Francois and Garrison 1982, pure-water term):
    alpha(f, T) = A3(T) f^2,  A3 in dB/(km kHz^2)  ->  x 1e3 gives dB/(m MHz^2)
Sound speed c(T): Marczak 1997 polynomial. Attenuation is applied zero-phase (dispersion neglected).

PMMA plate (thickness L, fluid layer, normal incidence) between water on both sides:
    T(f) = 1 / (cos kL + i/2 (m + 1/m) sin kL),  m = Z_p / Z_w,  k = w / c_p - i alpha_p
(numpy sign convention; the bulk delay L / c_p is removed and added to the arrival time instead).
"""
from __future__ import annotations

import numpy as np

from .common import Check

MODEL = "8"
NP_PER_DB = np.log(10) / 20


def sound_speed(P, T: float) -> float:
    a = P.value("water.sound_speed_coeffs")
    return float(sum(ak * T ** k for k, ak in enumerate(a)))


def alpha_coeff(P, T: float) -> float:
    """Attenuation coefficient in dB/(m MHz^2)."""
    key = "water.atten_coeffs_low" if T <= 20 else "water.atten_coeffs_high"
    a = P.value(key)
    A3 = sum(ak * T ** k for k, ak in enumerate(a))  # dB/(km kHz^2)
    return A3 * 1e3


def loss_db(P, f: np.ndarray, L: float, T: float) -> np.ndarray:
    return alpha_coeff(P, T) * (np.asarray(f) / 1e6) ** 2 * L


def transfer(P, f: np.ndarray, L: float, T: float) -> np.ndarray:
    return 10 ** (-loss_db(P, f, L, T) / 20)


def plate_transfer(P, f: np.ndarray, L: float, T: float) -> np.ndarray:
    f = np.asarray(f, dtype=float)
    if L <= 0:
        return np.ones_like(f, dtype=complex)
    cp, rp = P.si("pmma.sound_speed"), P.si("pmma.density")
    cw, rw = sound_speed(P, T), P.si("water.density")
    a0, n = P.value("pmma.atten_coeff"), P.value("pmma.atten_exponent")
    alpha = a0 * 100 * (f / 1e6) ** n * NP_PER_DB  # Np/m
    k = 2 * np.pi * f / cp - 1j * alpha
    m = (rp * cp) / (rw * cw)
    Tr = 1.0 / (np.cos(k * L) + 0.5j * (m + 1 / m) * np.sin(k * L))
    return Tr * np.exp(1j * 2 * np.pi * f * L / cp)


def checks(P) -> list[Check]:
    out = []
    a20 = alpha_coeff(P, 20.0) / 100  # dB/(cm MHz^2)
    ref = P.value("water.atten_20C_reference")
    out.append(Check(MODEL, "Water at 20 °C: alpha/f² matches Pinkerton (1949), within 3 %",
                     abs(a20 / ref - 1) < 0.03, f"{ref:.5f} dB/(cm MHz²) [L]", f"{a20:.5f} dB/(cm MHz²)",
                     kind="external"))
    lo, hi = P.value("water.atten_coeffs_low"), P.value("water.atten_coeffs_high")
    A_lo = sum(a * 20.0 ** k for k, a in enumerate(lo))
    A_hi = sum(a * 20.0 ** k for k, a in enumerate(hi))
    out.append(Check(MODEL, "Two temperature branches agree at 20 °C, within 1 %", abs(A_lo / A_hi - 1) < 0.01,
                     "continuous", f"{A_lo:.3e} vs {A_hi:.3e} dB/(km kHz²)"))
    c20 = sound_speed(P, 20.0)
    out.append(Check(MODEL, "Water sound speed at 20 °C (Marczak) equals 1482.3 m/s", abs(c20 - 1482.3) < 0.5,
                     "1482.3 m/s [L, Del Grosso and Mader 1972]", f"{c20:.1f} m/s", kind="external"))
    Lp, fp, Tp = P.si("physics.p1_water_loss_path"), P.si("physics.p1_water_loss_freq"), P.value("physics.p1_water_loss_temp")
    loss = float(loss_db(P, np.array([fp]), Lp, Tp)[0])
    ref = P.value("physics.p1_water_loss")
    out.append(Check(MODEL, "P1 (as quoted in CONTEXT.md): ~20 dB over 50 µm at 1 GHz, 37 °C",
                     abs(loss - ref) < 0.3 * ref, f"{ref:.0f} dB [L, P1]", f"{loss:.1f} dB", kind="external",
                     note="Disagreement of ~3x. The f² coefficient at 37 °C is well established "
                          "(~0.14 dB/µm at 1 GHz). The quoted P1 figure needs checking against the paper text."))
    # lossless plate: |T| = 1 at half-wave resonance, |T|^2 + |R|^2 = 1
    raw = dict(P.raw)
    Pl = P.with_overrides({"pmma.atten_coeff": 0.0})
    L = P.si("today.sample.pmma_thickness")
    cp = P.si("pmma.sound_speed")
    f = np.array([cp / (2 * L), cp / (4 * L)])
    Tr = plate_transfer(Pl, f, L, 22.0)
    m = (P.si("pmma.density") * cp) / (P.si("water.density") * sound_speed(P, 22.0))
    Tq_expected = 2 / (m + 1 / m)
    ok = abs(abs(Tr[0]) - 1) < 1e-9 and abs(abs(Tr[1]) - Tq_expected) < 1e-9
    out.append(Check(MODEL, "Lossless PMMA plate: |T| = 1 at half-wave, 2/(m + 1/m) at quarter-wave", ok,
                     f"1.000, {Tq_expected:.3f}", f"{abs(Tr[0]):.3f}, {abs(Tr[1]):.3f}"))
    return out
