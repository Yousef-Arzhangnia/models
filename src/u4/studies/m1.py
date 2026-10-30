"""M1 studies: models 1, 5, 7, 8, 10, 11, 12 and the chain comparison."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..models import absorption, chain, electronics, laser, noise, sphere_pa, transducer, water
from ..models.common import Check, Grid, db20
from . import plotting, study

C = plotting.COLORS
DIAM_TAG = "[S, M1 prompt test case]"
CS_TAG = "c = 1550 m/s [C, TBD placeholder]"


def _record(run, checks: list[Check]):
    for c in checks:
        run.check(c.name, c.passed, c.expected, c.obtained, c.kind, c.note)


# ---------------------------------------------------------------------------------------------- model 1
@study("m1_sphere", model="1", milestone="M1", title="Model 1: uniform sphere PA pulse and gaps")
def m1_sphere(P, run):
    _record(run, sphere_pa.checks(P))
    g = Grid.from_params(P)
    c = P.si("cell.sound_speed")
    fig, ax = plotting.new(1, 2, size=(11, 4.2))
    rows = []
    for i, d in enumerate(P.si("cell.test_diameters")):
        run.progress(0.3 + 0.3 * i, f"d = {d*1e6:.0f} µm")
        r = 1e-3
        spec = sphere_pa.spectrum(g.f, d, c, 1.0, r)
        p = sphere_pa.n_pulse(g.t, d, c, 1.0, r)
        ax[0].plot(g.t * 1e9, p / np.abs(p).max(), color=C[round(d, 9)], label=f"d = {d*1e6:.0f} µm, T = d/c = {d/c*1e9:.2f} ns")
        sel = g.f < 1.2e9
        ax[1].plot(g.f[sel] / 1e6, db20(spec[sel]), color=C[round(d, 9)], label=f"d = {d*1e6:.0f} µm")
        gaps = sphere_pa.gap_frequencies(d, c, 3)
        found = sphere_pa.find_zeros(g.f, np.abs(spec), gaps)
        for k, (ge, gf) in enumerate(zip(gaps, found)):
            ax[1].axvline(ge / 1e6, color=C[round(d, 9)], ls=":", lw=0.9)
            rows.append({"d_um": d * 1e6, "gap": k + 1, "k": sphere_pa.gap_constants(3)[k],
                         "expected_MHz": ge / 1e6, "found_MHz": gf / 1e6})
        run.result(f"first_gap_{d*1e6:.0f}um", gaps[0] / 1e6, unit="MHz", tag="[C]")
        run.result(f"pulse_length_{d*1e6:.0f}um", d / c * 1e9, unit="ns", tag="[C]")
    ax[0].set_xlim(-8, 8); ax[0].set_xlabel("retarded time τ (ns)"); ax[0].set_ylabel("pressure (normalised)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    ax[1].set_ylim(-60, 3); ax[1].set_xlabel("frequency (MHz)"); ax[1].set_ylabel("|P(f)| (dB re peak)")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    plotting.finish(fig, "Ideal N-pulse lasts d/c and its spectral gaps sit at 1.43, 2.46, 3.47 c/d",
                    f"Model 1, matched uniform sphere, delta heating. d = 7 and 12 µm {DIAM_TAG}; {CS_TAG}. "
                    "Dotted lines: analytical gap positions [L, Diebold 1990]. Spectra in dB re each peak.")
    run.figure(fig, "sphere_pulse_spectrum"); plotting.close(fig)
    run.data(pd.DataFrame(rows), "gap_table")
    sel = g.f < 1.2e9
    run.data(pd.DataFrame({"f_MHz": g.f[sel] / 1e6,
                           **{f"dB_{d*1e6:.0f}um": db20(sphere_pa.spectrum(g.f[sel], d, c, 1.0, 1e-3))
                              for d in P.si("cell.test_diameters")}}), "spectrum")
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- model 5
@study("m1_laser", model="5", milestone="M1", title="Model 5: laser pulse as low-pass filter")
def m1_laser(P, run):
    _record(run, laser.checks(P))
    g = Grid.from_params(P)
    c = P.si("cell.sound_speed")
    fig, ax = plotting.new(1, 2, size=(11, 4.2))
    sel = g.f < 2e9
    data = {"f_MHz": g.f[sel] / 1e6}
    for preset in ("today", "upgrade1"):
        tau, shape = P.si(f"{preset}.laser.pulse_fwhm"), P.value(f"{preset}.laser.pulse_shape")
        H = laser.filter_response(g.f, tau, shape)
        fc = laser.cutoff(tau, shape)
        ax[0].plot(g.f[sel] / 1e6, db20(H[sel], 1.0), color=C[preset],
                   label=f"{tau*1e9:.1f} ns {shape}: -6 dB at {fc/1e6:.0f} MHz")
        run.result(f"cutoff_{preset}", fc / 1e6, unit="MHz", tag="[C]")
        data[f"H_dB_{preset}"] = db20(H[sel], 1.0)
        d = 7e-6
        spec = sphere_pa.spectrum(g.f, d, c, 1.0, 1e-3)
        ax[1].plot(g.f[sel] / 1e6, db20(spec[sel] * H[sel], np.abs(spec).max()), color=C[preset],
                   label=f"7 µm sphere x {tau*1e9:.1f} ns pulse")
    spec = sphere_pa.spectrum(g.f, 7e-6, c, 1.0, 1e-3)
    ax[1].plot(g.f[sel] / 1e6, db20(spec[sel]), color=C["ideal"], ls="--", label="7 µm sphere, delta heating")
    for k in sphere_pa.gap_frequencies(7e-6, c, 3):
        ax[1].axvline(k / 1e6, color=C["gap"], ls=":", lw=0.8)
    for a in ax:
        a.set_xlabel("frequency (MHz)"); a.grid(alpha=0.3); a.legend(fontsize=8)
    ax[0].set_ylabel("|H_L(f)| (dB)"); ax[0].set_ylim(-40, 2)
    ax[1].set_ylabel("|P(f)| (dB re delta-heating peak)"); ax[1].set_ylim(-60, 3)
    plotting.finish(fig, "A 1.3 ns pulse halves the amplitude at 340 MHz; 0.5 ns keeps it to 880 MHz",
                    "Model 5, Gaussian pulse shape [C, TBD]. 1.3 ns [S, upper bound], 0.5 ns [S, Upgrade 1 target]. "
                    "Right: 7 µm sphere [S, M1 prompt], c = 1550 m/s [C, TBD]; gaps (dotted) do not move.")
    run.figure(fig, "laser_filter"); plotting.close(fig)
    run.data(pd.DataFrame(data), "laser_filter")
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- model 7
@study("m1_absorption", model="7", milestone="M1", title="Model 7 (simple): absorbed energy and p0")
def m1_absorption(P, run):
    _record(run, absorption.checks(P))
    rows = []
    for preset in ("today", "upgrade1"):
        for d in P.si("cell.test_diameters"):
            s = absorption.summary(P, preset, d)
            rows.append({"chain": preset, "d_um": d * 1e6, "mua_per_cm": s["mua"] / 100,
                         "E_abs_pJ": s["E_abs"] * 1e12, "p0_kPa": s["p0"] / 1e3,
                         "p0_local_kPa": s["p0_local"] / 1e3, "dT_mK": s["dT"] * 1e3})
            run.result(f"p0_{preset}_{d*1e6:.0f}um", s["p0"] / 1e3, unit="kPa", tag="[C]")
    run.data(pd.DataFrame(rows), "absorption_table")
    mua = np.logspace(np.log10(P.si("simulation.mua_sweep")[0]), np.log10(P.si("simulation.mua_sweep")[1]), 60)
    fig, ax = plotting.new(size=(7.5, 4))
    for d in P.si("cell.test_diameters"):
        p0 = [absorption.p0_uniform(P.si("today.sample_light.pulse_energy"), m, d, P.si("cell.gruneisen")) for m in mua]
        ax.loglog(mua / 100, np.array(p0) / 1e3, color=C[round(d, 9)], label=f"d = {d*1e6:.0f} µm")
    ax.axvline(P.value("cell.mua_532"), color=C["gap"], ls=":", label="placeholder 0.2 /cm [C, TBD]")
    ax.set_xlabel("absorption coefficient µa at 532 nm (1/cm)"); ax.set_ylabel("p0, energy-equivalent sphere (kPa)")
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    plotting.finish(fig, "Initial pressure scales with µa; the 532 nm value is the largest open input",
                    "Model 7 (simple). E = 380 nJ [C], Γ = 0.12 [L, water, TBD for cells], beam fully intercepted. "
                    "Same for both chains (Upgrade 1 energy assumed unchanged [C, TBD]).")
    run.figure(fig, "p0_vs_mua"); plotting.close(fig)
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- model 8
@study("m1_water", model="8", milestone="M1", title="Model 8: water and PMMA path")
def m1_water(P, run):
    _record(run, water.checks(P))
    f = np.linspace(1e6, 1.5e9, 3000)
    fig, ax = plotting.new(1, 2, size=(11, 4.2))
    data = {"f_MHz": f / 1e6}
    for preset in ("today", "upgrade1"):
        T, W = P.value(f"{preset}.sample.water_temperature"), P.si(f"{preset}.sample.water_path")
        loss = water.loss_db(P, f, W, T)
        ax[0].semilogy(f / 1e6, loss, color=C[preset], label=f"{W*1e3:.1f} mm water, {T} °C")
        data[f"loss_dB_{preset}"] = loss
        for fx in (20e6, 375e6):
            run.result(f"water_loss_{preset}_{fx/1e6:.0f}MHz", float(water.loss_db(P, np.array([fx]), W, T)[0]), "dB", "[C]")
    loss37 = water.loss_db(P, f, 50e-6, 37.0)
    ax[0].semilogy(f / 1e6, loss37, color=C["ideal"], ls="--", label="50 µm water, 37 °C (P1 case)")
    ax[0].plot([1000], [P.value("physics.p1_water_loss")], "k*", ms=10, label="P1 as quoted in CONTEXT.md [L]")
    ax[0].set_ylim(1e-3, 300); ax[0].set_xlabel("frequency (MHz)"); ax[0].set_ylabel("one-way loss (dB)")
    ax[0].grid(alpha=0.3, which="both"); ax[0].legend(fontsize=8)
    fp = np.linspace(0.1e6, 60e6, 3000)
    Tp = water.plate_transfer(P, fp, P.si("today.sample.pmma_thickness"), P.value("today.sample.water_temperature"))
    ax[1].plot(fp / 1e6, db20(Tp, 1.0), color=C["today"], label="0.7 mm PMMA, normal incidence")
    ax[1].axvspan(*[x / 1e6 for x in P.si("today.transducer.band_6db")], color=C["today"], alpha=0.08,
                  label="transducer -6 dB band [M]")
    ax[1].set_xlabel("frequency (MHz)"); ax[1].set_ylabel("|T_plate(f)| (dB)"); ax[1].set_ylim(-8, 1)
    ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8)
    run.data(pd.DataFrame(data), "water_loss")
    l_t = float(water.loss_db(P, np.array([20e6]), P.si("today.sample.water_path"), P.value("today.sample.water_temperature"))[0])
    l_u = float(water.loss_db(P, np.array([375e6]), P.si("upgrade1.sample.water_path"), P.value("upgrade1.sample.water_temperature"))[0])
    plotting.finish(fig, f"Water costs {l_t:.1f} dB at 20 MHz over 13 mm but {l_u:.1f} dB at 375 MHz over only 0.3 mm; PMMA adds ripple",
                    "Model 8. Water α/f² [L, Francois and Garrison 1982], 22 °C [C, TBD]. PMMA c = 2750 m/s, "
                    "ρ = 1190 kg/m³, α = 0.5 dB/(cm MHz) [L, typical, TBD]; plate resonances every 1.96 MHz.")
    run.figure(fig, "water_pmma"); plotting.close(fig)
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- model 10
@study("m1_transducer", model="10", milestone="M1", title="Model 10: transducer response and focal geometry")
def m1_transducer(P, run):
    _record(run, transducer.checks(P))
    g = Grid.from_params(P)
    fig, ax = plotting.new(1, 3, size=(14, 4.2))
    for preset in ("today", "upgrade1"):
        fc, (lo, hi) = P.si(f"{preset}.transducer.centre_frequency"), P.si(f"{preset}.transducer.band_6db")
        mag = transducer.magnitude(g.f, fc, lo, hi)
        sel = g.f < 1e9
        ax[0].semilogx(g.f[sel][1:] / 1e6, db20(mag[sel][1:], 1.0), color=C[preset],
                       label=f"{preset}: peak {fc/1e6:.0f} MHz, -6 dB {lo/1e6:.1f} to {hi/1e6:.1f} MHz")
        h = g.to_time(transducer.min_phase(mag, g.n))
        sel_t = (g.t > -0.02e-6) & (g.t < (0.6e-6 if preset == "today" else 0.03e-6))
        tt = g.t[sel_t] / (g.t[sel_t].max())
        ax[1].plot(g.t[sel_t] * 1e9, h[sel_t] / np.abs(h).max(), color=C[preset], label=preset)
    ax[0].set_ylim(-40, 2); ax[0].set_xlabel("frequency (MHz)"); ax[0].set_ylabel("|H_T(f)| (dB)")
    ax[0].grid(alpha=0.3, which="both"); ax[0].legend(fontsize=7.5)
    ax[1].set_xlabel("time (ns)"); ax[1].set_ylabel("impulse response (normalised)"); ax[1].grid(alpha=0.3)
    ax[1].legend(fontsize=8)
    cfg = chain.config(P, "today")
    Ws = np.linspace(9.5e-3, 14e-3, 46)
    spreads = [np.ptp(transducer.ray_delays(cfg["A"], cfg["R"], W, cfg["L"], cfg["c_w"], cfg["c_p"], 200)[0]) for W in Ws]
    ax[2].plot(Ws * 1e3, np.array(spreads) * 1e9, color=C["today"])
    ax[2].axvline(cfg["W_focus"] * 1e3, color=C["gap"], ls=":", label=f"paraxial focus {cfg['W_focus']*1e3:.2f} mm")
    ax[2].axvspan(*[x * 1e3 for x in P.si("today.sample.water_path_range")], color=C["today"], alpha=0.1,
                  label="measured water path 12.8 to 13.5 mm")
    ax[2].set_xlabel("water path, apex to PMMA (mm)"); ax[2].set_ylabel("arrival spread over aperture (ns)")
    ax[2].grid(alpha=0.3); ax[2].legend(fontsize=7.5)
    run.result("focus_water_distance_today", cfg["W_focus"] * 1e3, "mm", "[C]")
    sp = np.ptp(transducer.ray_delays(cfg["A"], cfg["R"], cfg["W"], cfg["L"], cfg["c_w"], cfg["c_p"], 400)[0])
    run.result("aperture_spread_today", sp * 1e9, "ns", "[C]")
    run.data(pd.DataFrame({"W_mm": Ws * 1e3, "spread_ns": np.array(spreads) * 1e9}), "defocus_spread")
    plotting.finish(fig, "Through 0.7 mm PMMA the 12 mm transducer focuses at 10.7 mm of water, so 13 mm is 2.3 mm out of focus",
                    "Model 10. Today: centre and -6 dB band [M, certificate], element 6 mm and ROC 12 mm [S]. Upgrade 1: "
                    "peak 375 MHz [L, P1], edges 150 and 500 MHz [S, target, TBD]. Log-Gaussian magnitude, minimum phase [C].")
    run.figure(fig, "transducer"); plotting.close(fig)
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- model 11
@study("m1_electronics", model="11", milestone="M1", title="Model 11: gain and noise")
def m1_electronics(P, run):
    _record(run, electronics.checks(P))
    f = np.logspace(5, 9.7, 800)
    fig, ax = plotting.new(size=(7.5, 4))
    for preset in ("today", "upgrade1"):
        H = electronics.response(P, preset, f)
        ax.semilogx(f / 1e6, 20 * np.log10(np.abs(H)), color=C[preset],
                    label=f"{preset}: {sum(electronics.gains_db(P, preset)):.1f} dB, e_n = "
                          f"{electronics.noise_density(P, preset)*1e9:.2f} nV/√Hz")
        run.result(f"gain_{preset}", sum(electronics.gains_db(P, preset)), "dB", "[S]/[M]")
        run.result(f"noise_density_{preset}", electronics.noise_density(P, preset) * 1e9, "nV/√Hz", "[C]")
    ax.set_ylim(0, 45); ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("|H_E(f)| (dB)"); ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    plotting.finish(fig, "Both chains give about 40 dB of flat gain across their transducer bands",
                    "Model 11. Gains 13.6 dB [M] + 27 dB [S] (today), 40 dB [S, target] (Upgrade 1). Corners, noise figures "
                    "(7 and 3 dB) and digitiser filter orders are placeholders [C, TBD]; digitiser bandwidth 250 MHz [S].")
    run.figure(fig, "electronics"); plotting.close(fig)
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- model 12
@study("m1_noise", model="12", milestone="M1", title="Model 12: noise, SNR and averaging")
def m1_noise(P, run):
    _record(run, noise.checks(P))
    mua0 = P.si("cell.mua_532")
    mua = np.logspace(np.log10(P.si("simulation.mua_sweep")[0]), np.log10(P.si("simulation.mua_sweep")[1]), 40)
    fig, ax = plotting.new(1, 2, size=(11, 4.2))
    rows = []
    k = 0
    for preset in ("today", "upgrade1"):
        for d in P.si("cell.test_diameters"):
            k += 1
            run.progress(0.1 + 0.2 * k, f"{preset}, d = {d*1e6:.0f} µm")
            r = chain.simulate(P, preset, d)
            s1 = r.info["snr_bp"]
            # SNR scales with absorbed energy (linear chain)
            Eab = np.array([absorption.absorbed_energy(1.0, m, d) for m in mua])
            s_mua = s1 + 20 * np.log10(Eab / absorption.absorbed_energy(1.0, mua0, d))
            ls = "-" if d > 10e-6 else "--"
            ax[0].semilogx(mua / 100, s_mua, color=C[preset], ls=ls, label=f"{preset}, {d*1e6:.0f} µm, 1 shot")
            N = np.logspace(0, 5, 50)
            ax[1].semilogx(N, s1 + 10 * np.log10(N), color=C[preset], ls=ls, label=f"{preset}, {d*1e6:.0f} µm")
            rows.append({"chain": preset, "d_um": d * 1e6, "snr1_bp": s1, "snr1_raw": r.info["snr_raw"],
                         "snr_avg": r.info["snr_bp_avg"], "n_avg": r.info["n_avg"],
                         "snr_budget": r.info["snr_bp_budget"], "n_budget": r.info["n_budget"],
                         "n_needed_42p8": r.info["n_needed"]})
            run.result(f"snr1_{preset}_{d*1e6:.0f}um", s1, "dB", "[C]")
            run.result(f"snr_avg_{preset}_{d*1e6:.0f}um", r.info["snr_bp_avg"], "dB", "[C]")
    lo, hi = P.value("earlier_estimates.snr_single_shot_cell")
    ax[0].axhspan(lo, hi, color=C["gap"], alpha=0.15, label="earlier estimate -40 to -20 dB [C]")
    ax[0].axvline(mua0 / 100, color=C["gap"], ls=":")
    ax[0].set_xlabel("µa at 532 nm (1/cm)"); ax[0].set_ylabel("single-shot SNR, band-passed (dB)"); ax[0].grid(alpha=0.3, which="both")
    ax[0].legend(fontsize=7)
    ax[1].axhline(P.value("goal.snr_target"), color="k", ls=":", label="target 42.8 dB [S]")
    ax[1].axvline(P.value("today.acquisition.averages"), color=C["gap"], ls=":")
    ax[1].axvline(P.si("goal.time_budget_per_cell") * min(P.si("today.laser.rep_rate")), color=C["gap"], ls="--",
                  label="30 s at 1 kHz")
    ax[1].set_xlabel("number of averaged shots"); ax[1].set_ylabel("SNR, band-passed (dB)"); ax[1].grid(alpha=0.3, which="both")
    ax[1].legend(fontsize=7)
    run.data(pd.DataFrame(rows), "snr_table")
    plotting.finish(fig, "At µa = 0.2 /cm today's chain stays below 0 dB even after 30 s; Upgrade 1 reaches the target in under 1000 shots",
                    "Model 12 with the full chain. µa sweep: SNR scales with absorbed energy. Sensitivities 5 µV/Pa (both), "
                    "noise figures, µa 0.2 /cm and Γ are placeholders [C, TBD]. Band-passed = -20 dB band of the clean signal.")
    run.figure(fig, "snr"); plotting.close(fig)
    run.progress(1.0, "done")


# ---------------------------------------------------------------------------------------------- chain
def _chain_checks(P, results: dict) -> list[Check]:
    out = []
    lo, hi = P.si("today.bead_test.spectrum_peak"), 20e6
    for d in P.si("cell.test_diameters"):
        r = results[("today", d)]
        fpk = r.info["peak_freq"]
        out.append(Check("chain", f"Today's chain, {d*1e6:.0f} µm: spectrum peak near 12 to 20 MHz (bead behaviour)",
                         lo * 0.95 <= fpk <= hi * 1.05, "12 to 20 MHz [M, bead]", f"{fpk/1e6:.1f} MHz", kind="external"))
        rng = r.info["ringing_20db"]
        out.append(Check("chain", f"Today's chain, {d*1e6:.0f} µm: ringing of hundreds of ns", rng >= 100e-9,
                         ">= 100 ns above -20 dB [M, bead]", f"{rng*1e9:.0f} ns", kind="external"))
    arr = results[("today", P.si("cell.test_diameters")[0])].info["t_arrival"]
    meas = P.si("today.bead_test.arrival_time")
    out.append(Check("chain", "Today's arrival time near the measured 9.5 µs (within 0.6 µs; trigger offset unknown)",
                     abs(arr - meas) < 0.6e-6, "9.5 µs [M]", f"{arr*1e6:.2f} µs", kind="external"))
    lo, hi = P.value("earlier_estimates.snr_single_shot_cell")
    for d in P.si("cell.test_diameters"):
        s = results[("today", d)].info["snr_bp"]
        out.append(Check("chain", f"Today's single-shot SNR, {d*1e6:.0f} µm unstained cell, within -40 to -20 dB",
                         lo <= s <= hi, "-40 to -20 dB [C, CONTEXT.md]", f"{s:.1f} dB", kind="external",
                         note="Driven by placeholders µa, S, NF. See the µa sweep on page 12."))
    ml = P.value("earlier_estimates.mismatch_loss")
    for d in P.si("cell.test_diameters"):
        L = -results[("today", d)].info["loss_vs_ideal_db"]
        out.append(Check("chain", f"Today's amplitude loss vs ideal pulse, {d*1e6:.0f} µm, about 50 dB (within 10 dB)",
                         abs(L - ml) <= 10, "50 dB [C, CONTEXT.md]", f"{L:.1f} dB", kind="external"))
    for d in P.si("cell.test_diameters"):
        r = results[("upgrade1", d)]
        gaps = sphere_pa.gap_frequencies(d, r.c_s, 2)
        gaps = gaps[gaps < 0.9 * P.si("upgrade1.transducer.band_6db")[1] * 1.3]
        z = sphere_pa.find_zeros(r.f, np.abs(r.spectra["digitiser_in"]), gaps, 0.05)
        rel = np.abs(z / gaps - 1)
        out.append(Check("chain", f"Upgrade 1 chain, {d*1e6:.0f} µm: gaps not moved by the instrument (within 1 %)",
                         bool(np.all(rel < 0.01)), ", ".join(f"{x/1e6:.1f}" for x in gaps) + " MHz",
                         ", ".join(f"{x/1e6:.1f}" for x in z) + " MHz"))
    for d in P.si("cell.test_diameters"):
        i = results[("upgrade1", d)].info
        out.append(Check("chain", f"Ideal peak pressure: numerical vs analytical p0 a/(2R), {d*1e6:.0f} µm (Gibbs < 10 %)",
                         abs(i["ideal_peak"] / i["ideal_peak_analytic"] - 1) < 0.10,
                         f"{i['ideal_peak_analytic']:.1f} Pa", f"{i['ideal_peak']:.1f} Pa"))
    return out


def bead_case(P) -> dict:
    """10 µm bead through today's chain: shape and the absorbed energy implied by the measured SNR."""
    d = P.si("today.bead_test.diameter")
    r = chain.simulate(P, "today", d, c_s=P.si("today.bead_test.sound_speed"), p0=1.0,
                       rho_s=P.si("today.bead_test.density"))
    snr_meas1 = P.value("today.bead_test.snr_averaged") - 10 * np.log10(P.value("today.acquisition.averages"))
    p0_req = 10 ** ((snr_meas1 - r.info["snr_bp"]) / 20)
    gamma_E = p0_req * absorption.volume(d)
    frac = gamma_E / (P.si("cell.gruneisen") * P.si("today.sample_light.pulse_energy"))
    return dict(result=r, snr_single_measured=snr_meas1, p0_required=p0_req, gamma_E=gamma_E, fraction_water_gamma=frac)


@study("m1_chain", model="chain", milestone="M1", title="M1 chain comparison: today vs Upgrade 1")
def m1_chain(P, run):
    results = {}
    k = 0
    for preset in ("today", "upgrade1"):
        for d in P.si("cell.test_diameters"):
            k += 1
            run.progress(0.1 * k, f"simulating {preset}, d = {d*1e6:.0f} µm")
            results[(preset, d)] = chain.simulate(P, preset, d)
    _record(run, _chain_checks(P, results))
    run.progress(0.5, "bead case")
    bead = bead_case(P)
    run.result("bead_implied_gamma_E", bead["gamma_E"] * 1e9, "nJ", "[C]",
               text="Γ·E_abs needed for the measured 25 dB at 1000 averages")
    run.result("bead_implied_fraction", bead["fraction_water_gamma"] * 100, "%", "[C]",
               text="of 380 nJ absorbed, if Γ = 0.12")
    run.result("bead_peak_freq", bead["result"].info["peak_freq"] / 1e6, "MHz", "[C]")

    # summary table
    rows = []
    for key, r in results.items():
        rows += chain.summary_rows(r)
        i = r.info
        run.result(f"snr1_{key[0]}_{key[1]*1e6:.0f}um", i["snr_bp"], "dB", "[C]")
        run.result(f"snr_avg_{key[0]}_{key[1]*1e6:.0f}um", i["snr_bp_avg"], "dB", "[C]")
    run.data(pd.DataFrame(rows), "chain_summary")

    # figure A: waveforms and spectra side by side
    run.progress(0.7, "figures")
    fig, ax = plotting.new(2, 2, size=(13, 7.6))
    for col, preset in enumerate(("today", "upgrade1")):
        for d in P.si("cell.test_diameters"):
            r = results[(preset, d)]
            t_abs = (r.t_dig + r.info["t_arrival"]) * 1e6
            v = r.v_dig / np.abs(r.v_dig).max()
            ax[0, col].plot(t_abs, v, color=C[round(d, 9)], lw=1,
                            label=f"{d*1e6:.0f} µm: peak {r.info['peak_raw']*1e6:.2f} µV" if preset == "today"
                            else f"{d*1e6:.0f} µm: peak {r.info['peak_raw']*1e3:.2f} mV")
            sel = (r.f > 0.5e6) & (r.f < (60e6 if preset == "today" else 1.2e9))
            ax[1, col].plot(r.f[sel] / 1e6, db20(r.spectra["digitiser_in"][sel]), color=C[round(d, 9)],
                            label=f"{d*1e6:.0f} µm received")
            ax[1, col].plot(r.f[sel] / 1e6, db20(r.spectra["ideal"][sel], np.abs(r.spectra["ideal"]).max()),
                            color=C[round(d, 9)], ls=":", lw=0.9, label=f"{d*1e6:.0f} µm ideal (own peak)")
        ta = results[(preset, 7e-6)].info["t_arrival"] * 1e6
        ax[0, col].set_xlim(ta - (0.1 if preset == "today" else 0.01), ta + (1.2 if preset == "today" else 0.04))
        ax[0, col].set_xlabel("time after laser (µs)"); ax[0, col].set_ylabel("digitised signal (normalised)")
        ax[0, col].set_title(chain.PRESETS[preset], fontsize=9.5); ax[0, col].grid(alpha=0.3); ax[0, col].legend(fontsize=7.5)
        ax[1, col].set_ylim(-60, 3); ax[1, col].set_xlabel("frequency (MHz)"); ax[1, col].set_ylabel("dB re peak")
        ax[1, col].grid(alpha=0.3); ax[1, col].legend(fontsize=7)
    plotting.finish(fig, "Today's chain hears only a 13 to 23 MHz tail that looks the same for 7 and 12 µm; Upgrade 1 resolves size",
                    "M1 chain, noise-free. d = 7 and 12 µm [S, M1 prompt], c = 1550 m/s [C, TBD], µa = 0.2 /cm [C, TBD]. "
                    "Today: 1.3 ns [S], 0.7 mm PMMA [M] + 13 mm water [C], certificate band [M], 40.6 dB, 500 MS/s 12 bit [S]. "
                    "Upgrade 1: 0.5 ns, 0.3 mm water, 150 to 500 MHz, 40 dB, 8 GS/s [S, targets]. Dotted: ideal spectrum.")
    run.figure(fig, "chain_waveforms_spectra"); plotting.close(fig)

    # figure B: where the signal is lost (stage by stage), 12 µm
    fig, ax = plotting.new(1, 2, size=(13, 4.4))
    stages = [("ideal", "ideal sphere"), ("laser", "+ laser"), ("path", "+ water / PMMA"), ("face", "+ aperture"),
              ("transducer", "+ transducer (x S)")]
    for col, preset in enumerate(("today", "upgrade1")):
        r = results[(preset, 12e-6)]
        sel = (r.f > 0.5e6) & (r.f < 1.5e9)
        ref = np.abs(r.spectra["ideal"]).max()
        for j, (key, lab) in enumerate(stages):
            spec = r.spectra[key] / (r.info["S"] if key == "transducer" else 1.0)
            ax[col].semilogx(r.f[sel] / 1e6, db20(spec[sel], ref), lw=1.1, label=lab,
                             color=plt_cycle(j))
        ax[col].set_ylim(-90, 3); ax[col].set_xlabel("frequency (MHz)"); ax[col].set_ylabel("dB re ideal peak")
        ax[col].set_title(chain.PRESETS[preset] + ", 12 µm", fontsize=9.5); ax[col].grid(alpha=0.3, which="both")
        ax[col].legend(fontsize=7.5)
    plotting.finish(fig, "Today the transducer band and defocus remove most of the pulse; in Upgrade 1 the bands overlap",
                    "Stage-by-stage spectra for a 12 µm sphere [S, M1 prompt]; same placeholders as above. Pressure-equivalent "
                    "transducer stage (divided by S). Model numbers: 1, 5, 8, 10.")
    run.figure(fig, "chain_stage_spectra"); plotting.close(fig)

    # figure C: SNR summary
    fig, ax = plotting.new(size=(9, 4.3))
    labels, s1, sa, sb = [], [], [], []
    for (preset, d), r in results.items():
        labels.append(f"{'today' if preset == 'today' else 'Upgrade 1'}\n{d*1e6:.0f} µm")
        s1.append(r.info["snr_bp"]); sa.append(r.info["snr_bp_avg"]); sb.append(r.info["snr_bp_budget"])
    x = np.arange(len(labels))
    ax.bar(x - 0.25, s1, 0.25, color="#9AA5B1", label="single shot")
    ax.bar(x, sa, 0.25, color="#4C6A88", label=f"{results[('today', 7e-6)].info['n_avg']} averages")
    ax.bar(x + 0.25, sb, 0.25, color="#1F3B57", label=f"{results[('today', 7e-6)].info['n_budget']} averages (30 s at 1 kHz)")
    for xi, v in zip(x, s1):
        ax.text(xi - 0.25, v + (1 if v >= 0 else -4), f"{v:.0f}", ha="center", fontsize=7.5)
    ax.axhline(P.value("goal.snr_target"), color="k", ls=":", label="target 42.8 dB [S]")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5); ax.set_ylabel("SNR, band-passed (dB)")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7.5, loc="upper left")
    gains = [results[("upgrade1", d)].info["snr_bp"] - results[("today", d)].info["snr_bp"] for d in P.si("cell.test_diameters")]
    run.result("snr_gain_upgrade1_min", min(gains), "dB", "[C]")
    run.result("snr_gain_upgrade1_max", max(gains), "dB", "[C]")
    plotting.finish(fig, f"Upgrade 1 gains {min(gains):.0f} to {max(gains):.0f} dB of single-shot SNR at the same light dose",
                    "Model 12 on the full chain. Unstained cell at 532 nm, µa = 0.2 /cm [C, TBD]; both sensitivities 5 µV/Pa "
                    "[C, TBD]; NF 7 dB today, 3 dB Upgrade 1 [C, TBD]. Absolute values move 1:1 (in dB) with µa, S and Γ.")
    run.figure(fig, "chain_snr"); plotting.close(fig)

    # figure D: bead, qualitative
    br = bead["result"]
    fig, ax = plotting.new(1, 2, size=(11, 4))
    t_abs = (br.t_dig + br.info["t_arrival"]) * 1e6
    ax[0].plot(t_abs, br.v_dig / np.abs(br.v_dig).max(), color=C["today"], lw=1)
    ax[0].axvline(P.si("today.bead_test.arrival_time") * 1e6, color="k", ls=":", label="measured arrival 9.5 µs [M]")
    ax[0].set_xlim(br.info["t_arrival"] * 1e6 - 0.1, br.info["t_arrival"] * 1e6 + 1.4)
    ax[0].set_xlabel("time after laser (µs)"); ax[0].set_ylabel("signal (normalised)"); ax[0].grid(alpha=0.3); ax[0].legend(fontsize=8)
    sel = (br.f > 0.5e6) & (br.f < 60e6)
    ax[1].plot(br.f[sel] / 1e6, db20(br.spectra["digitiser_in"][sel]), color=C["today"], label="model, 10 µm bead")
    ax[1].axvspan(*[x / 1e6 for x in P.si("today.bead_test.band")], color="k", alpha=0.1, label="measured band 10 to 13 MHz [M]")
    ax[1].axvline(P.si("today.bead_test.spectrum_peak") / 1e6, color="k", ls=":", label="measured peak 12 MHz [M]")
    ax[1].set_ylim(-40, 3); ax[1].set_xlabel("frequency (MHz)"); ax[1].set_ylabel("dB re peak"); ax[1].grid(alpha=0.3)
    ax[1].legend(fontsize=8)
    run.data(pd.DataFrame({"f_MHz": br.f[sel] / 1e6, "dB": db20(br.spectra["digitiser_in"][sel])}), "bead_spectrum")
    plotting.finish(fig, f"Modelled bead peaks at {br.info['peak_freq']/1e6:.0f} MHz vs 12 MHz measured: the model is still too broadband",
                    "Today's chain with a 10 µm bead [M] modelled as a fluid sphere, c = 2350 m/s, ρ = 1050 kg/m³ "
                    "[L, polystyrene, TBD]. Measured values from CONTEXT.md; raw bead data (reza/points) not available in M1.")
    run.figure(fig, "bead_qualitative"); plotting.close(fig)
    run.progress(1.0, "done")


def plt_cycle(j: int) -> str:
    return ["#444444", "#7A4FA0", "#2E7D5B", "#B4532A", "#1F5F8B"][j % 5]


M1_STUDIES = ["m1_sphere", "m1_laser", "m1_absorption", "m1_water", "m1_transducer", "m1_electronics", "m1_noise", "m1_chain"]
