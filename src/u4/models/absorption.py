"""Model 7 (simple): absorbed energy and initial pressure of a uniform sphere.

Energy-equivalent uniform sphere:
    E_abs = E_pulse (1 - exp(-mu_a d))            (beam fully intercepted: spot << d)
    p0    = Gamma E_abs / V,   V = pi d^3 / 6
    dT    = E_abs / (rho C_p V)
Local (column) value for comparison: p0_local = Gamma mu_a F_peak.
At low frequency the emitted pressure depends only on Gamma E_abs (monopole), so the energy-equivalent
sphere is exact below the first gap; above it, the true column heating (2 µm spot) differs (model 6, M4).
"""
from __future__ import annotations

import numpy as np

from .common import Check, Grid
from . import sphere_pa

MODEL = "7"


def peak_fluence(energy: float, fwhm: float) -> float:
    """Peak fluence (J/m^2) of a Gaussian spot with intensity FWHM."""
    return 4 * np.log(2) * energy / (np.pi * fwhm ** 2)


def absorbed_energy(energy: float, mua: float, d: float) -> float:
    return energy * (1 - np.exp(-mua * d))


def volume(d: float) -> float:
    return np.pi * d ** 3 / 6


def p0_uniform(energy: float, mua: float, d: float, gamma: float) -> float:
    return gamma * absorbed_energy(energy, mua, d) / volume(d)


def p0_local(fluence: float, mua: float, gamma: float) -> float:
    return gamma * mua * fluence


def temperature_rise(energy: float, mua: float, d: float, rho: float, cp: float) -> float:
    return absorbed_energy(energy, mua, d) / (rho * cp * volume(d))


def summary(P, preset: str, d: float, mua: float | None = None) -> dict:
    E = P.si(f"{preset}.sample_light.pulse_energy")
    mua = P.si("cell.mua_532") if mua is None else mua
    gam = P.si("cell.gruneisen")
    F = peak_fluence(E, P.si("today.objective.spot_fwhm"))
    return dict(E_pulse=E, mua=mua, E_abs=absorbed_energy(E, mua, d), p0=p0_uniform(E, mua, d, gam),
                p0_local=p0_local(F, mua, gam), F_peak=F,
                dT=temperature_rise(E, mua, d, P.si("cell.density"), P.si("cell.heat_capacity")))


def checks(P) -> list[Check]:
    out = []
    E = P.si("today.sample_light.pulse_energy")
    F = peak_fluence(E, P.si("today.objective.spot_fwhm"))
    Fc = P.si("today.sample_light.peak_fluence")
    out.append(Check(MODEL, "380 nJ in a 2.0 µm FWHM Gaussian spot gives the quoted 8.4 J/cm² peak",
                     abs(F / Fc - 1) < 0.01, f"{Fc/1e4:.1f} J/cm² [C]", f"{F/1e4:.2f} J/cm²"))
    # low-frequency (monopole) limit: P(f) -> i w Gamma E_abs / (4 pi r c^2)
    g = Grid.from_params(P)
    d, c, r, gam = 12e-6, P.si("cell.sound_speed"), 1e-3, P.si("cell.gruneisen")
    mua = P.si("cell.mua_532")
    p0 = p0_uniform(E, mua, d, gam)
    f = np.array([1e5, 1e6])
    Pf = sphere_pa.spectrum(f, d, c, p0, r)
    mono = 2 * np.pi * f * gam * absorbed_energy(E, mua, d) / (4 * np.pi * r * c ** 2)
    err = np.max(np.abs(np.abs(Pf) / mono - 1))
    out.append(Check(MODEL, "Low-frequency limit equals monopole i w Gamma E_abs / (4 pi r c²)",
                     err < 1e-3, "ratio 1", f"max deviation {err:.1e}"))
    spot, dmin = P.si("today.objective.spot_fwhm"), min(P.si("cell.test_diameters"))
    out.append(Check(MODEL, "Spot much smaller than cell (beam fully intercepted)", spot < 0.5 * dmin,
                     "spot < d/2", f"{spot*1e6:.1f} µm vs d = {dmin*1e6:.0f} µm"))
    return out
