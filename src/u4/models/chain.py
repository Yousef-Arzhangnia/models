"""M1 forward chain: models 1, 5, 7, 8, 10, 11, 12 in series (frequency domain).

    P_ideal(f)  sphere, delta heating, at the apparent distance R_app          (model 1, 7)
  x H_L(f)      laser pulse                                                     (model 5)
  x H_W H_P     water f^2 attenuation and PMMA plate                            (model 8)
  x H_SIR       aperture integration (defocus) or delta (at focus)              (model 10)
  x S H_T       receive sensitivity and transducer response                     (model 10)
  x H_E         amplifiers and digitiser bandwidth                              (model 11)
  -> sampled at the digitiser rate; noise, quantisation, SNR, averaging          (model 12)

Presets 'today' and 'upgrade1' read their values from params.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import fft as sfft

from . import absorption, electronics, laser, noise, sphere_pa, transducer, water
from .common import Grid, envelope_duration

PRESETS = {"today": "Today's chain (20 MHz, 0.7 mm PMMA + 13 mm water, 1.3 ns)",
           "upgrade1": "Upgrade 1 chain (150 to 500 MHz, 0.3 mm water, 0.5 ns)"}


@dataclass
class ChainResult:
    preset: str
    d: float
    c_s: float
    grid: Grid
    t: np.ndarray
    f: np.ndarray
    spectra: dict           # stage name -> complex spectrum on f
    signals: dict           # stage name -> time signal on t
    t_dig: np.ndarray
    v_dig: np.ndarray       # clean digitised trace (V)
    v_dig_bp: np.ndarray    # clean trace after the analysis band-pass (V)
    band: tuple
    sigma_raw: float
    sigma_bp: float
    info: dict = field(default_factory=dict)

    def noisy_trace(self, n_avg: int = 1, seed: int = 1, band_passed: bool = True) -> np.ndarray:
        """Example noisy digitised trace, averaged over n_avg shots (white noise at the stated sigma)."""
        rng = np.random.default_rng(seed)
        sig = (self.sigma_bp if band_passed else self.sigma_raw) / np.sqrt(n_avg)
        base = self.v_dig_bp if band_passed else self.v_dig
        if band_passed:
            nz = rng.standard_normal(len(base))
            Z = sfft.rfft(nz)
            fd = sfft.rfftfreq(len(base), 1 / self.info["fs_dig"])
            Z[(fd < self.band[0]) | (fd > self.band[1])] = 0
            nz = sfft.irfft(Z, n=len(base))
            nz *= sig / np.std(nz)
            return base + nz
        return base + sig * rng.standard_normal(len(base))


def config(P, preset: str) -> dict:
    T = P.value(f"{preset}.sample.water_temperature")
    cfg = dict(
        T=T, c_w=water.sound_speed(P, T), rho_w=P.si("water.density"), c_p=P.si("pmma.sound_speed"),
        W=P.si(f"{preset}.sample.water_path"), L=P.si(f"{preset}.sample.pmma_thickness"),
        tau=P.si(f"{preset}.laser.pulse_fwhm"), shape=P.value(f"{preset}.laser.pulse_shape"),
        fc=P.si(f"{preset}.transducer.centre_frequency"), band6=tuple(P.si(f"{preset}.transducer.band_6db")),
        S=P.si(f"{preset}.transducer.sensitivity"), geometry=P.value(f"{preset}.transducer.geometry"),
        fs_dig=P.si(f"{preset}.digitiser.sample_rate"), bits=int(P.value(f"{preset}.digitiser.bits")),
        full_scale=P.si(f"{preset}.digitiser.input_range"), adc_noise=P.value(f"{preset}.digitiser.adc_noise"),
        n_avg=int(P.value(f"{preset}.acquisition.averages")),
        gain_db=sum(electronics.gains_db(P, preset)), e_n=electronics.noise_density(P, preset),
    )
    if cfg["geometry"] == "defocus":
        cfg["A"] = P.si(f"{preset}.transducer.element_diameter") / 2
        cfg["R"] = P.si(f"{preset}.transducer.roc")
        cfg["R_app"] = transducer.apparent_distance(cfg["W"], cfg["L"], cfg["c_w"], cfg["c_p"])
        cfg["W_focus"] = transducer.focus_water_distance(cfg["R"], cfg["L"], cfg["c_w"], cfg["c_p"])
    else:
        cfg["R_app"] = cfg["W"]
        cfg["W_focus"] = P.si(f"{preset}.transducer.focal_length")
    cfg["t_arrival"] = cfg["W"] / cfg["c_w"] + (cfg["L"] / cfg["c_p"] if cfg["L"] > 0 else 0.0)
    return cfg


def simulate(P, preset: str, d: float, c_s: float | None = None, mua: float | None = None,
             p0: float | None = None, rho_s: float | None = None, grid: Grid | None = None) -> ChainResult:
    grid = grid or Grid.from_params(P)
    t, f = grid.t, grid.f
    cfg = config(P, preset)
    c_s = P.si("cell.sound_speed") if c_s is None else c_s
    rho_s = P.si("cell.density") if rho_s is None else rho_s
    ab = absorption.summary(P, preset, d, mua)
    p0 = ab["p0"] if p0 is None else p0

    P_ideal = sphere_pa.spectrum(f, d, c_s, p0, cfg["R_app"], c_f=cfg["c_w"], rho_s=rho_s, rho_f=cfg["rho_w"])
    H_L = laser.filter_response(f, cfg["tau"], cfg["shape"])
    H_W = water.transfer(P, f, cfg["W"], cfg["T"])
    H_P = water.plate_transfer(P, f, cfg["L"], cfg["T"])
    magT = transducer.magnitude(f, cfg["fc"], *cfg["band6"])
    H_T = transducer.min_phase(magT, grid.n)
    if cfg["geometry"] == "defocus":
        dtau, wts = transducer.ray_delays(cfg["A"], cfg["R"], cfg["W"], cfg["L"], cfg["c_w"], cfg["c_p"],
                                          int(P.value("simulation.sir_annuli")))
        H_S = transducer.sir_spectrum(f, dtau, wts, mask=f < 8 * cfg["band6"][1])
        cfg["sir_spread"] = float(np.ptp(dtau))
    else:
        H_S = np.ones_like(f, dtype=complex)
        cfg["sir_spread"] = 0.0
    H_E = electronics.response(P, preset, f)

    spectra = {"ideal": P_ideal}
    spectra["laser"] = spectra["ideal"] * H_L
    spectra["path"] = spectra["laser"] * H_W * H_P
    spectra["face"] = spectra["path"] * H_S
    spectra["transducer"] = spectra["face"] * cfg["S"] * H_T
    spectra["digitiser_in"] = spectra["transducer"] * H_E
    signals = {k: grid.to_time(v) for k, v in spectra.items()}

    fs_d = cfg["fs_dig"]
    t_dig = np.arange(t[0], t[-1], 1 / fs_d)
    v_dig = np.interp(t_dig, t, signals["digitiser_in"])

    # noise
    psd = cfg["e_n"] ** 2 * np.abs(H_E) ** 2
    fd, pf = noise.folded_psd(f, psd, fs_d, len(t_dig))
    q = noise.lsb(cfg["full_scale"], cfg["bits"])
    sig_raw = noise.sigma(fd, pf, q, cfg["adc_noise"])

    # analysis band: clean received spectrum within X dB of its peak (contiguous around the peak)
    Vd = sfft.rfft(v_dig)
    mag = np.abs(Vd)
    ipk = int(np.argmax(mag[1:]) + 1)
    thr = mag[ipk] * 10 ** (-P.value("simulation.analysis_band_db") / 20)
    lo = ipk
    while lo > 1 and mag[lo - 1] >= thr:
        lo -= 1
    hi = ipk
    while hi < len(mag) - 1 and mag[hi + 1] >= thr:
        hi += 1
    band = (fd[lo], fd[hi])
    Vbp = np.where((fd >= band[0]) & (fd <= band[1]), Vd, 0)
    v_bp = sfft.irfft(Vbp, n=len(v_dig))
    sig_bp = noise.sigma(fd, pf, q, cfg["adc_noise"], band)

    peak_raw, peak_bp = float(np.max(np.abs(v_dig))), float(np.max(np.abs(v_bp)))
    snr_raw, snr_bp = noise.snr_db(peak_raw, sig_raw), noise.snr_db(peak_bp, sig_bp)
    G = 10 ** (cfg["gain_db"] / 20)
    p_equiv = signals["digitiser_in"] / (cfg["S"] * G)
    vE = np.abs(spectra["digitiser_in"])
    rate_min = min(P.si("today.laser.rep_rate"))
    n_budget = int(P.si("goal.time_budget_per_cell") * rate_min)
    target = P.value("goal.snr_target")

    info = dict(cfg)
    info.update(
        p0=p0, E_abs=ab["E_abs"], dT=ab["dT"], mua=ab["mua"], p0_local=ab["p0_local"],
        ideal_peak=float(np.max(np.abs(signals["ideal"]))),
        ideal_peak_analytic=sphere_pa.peak_pressure(d, p0, cfg["R_app"]),
        pulse_length=d / c_s, gaps=sphere_pa.gap_frequencies(d, c_s, 3),
        face_peak=float(np.max(np.abs(signals["face"]))),
        peak_raw=peak_raw, peak_bp=peak_bp, snr_raw=snr_raw, snr_bp=snr_bp,
        snr_bp_avg=noise.averaged_snr_db(snr_bp, cfg["n_avg"]),
        snr_raw_avg=noise.averaged_snr_db(snr_raw, cfg["n_avg"]),
        n_budget=n_budget, snr_bp_budget=noise.averaged_snr_db(snr_bp, n_budget),
        n_needed=noise.averages_needed(snr_bp, target), snr_target=target,
        loss_vs_ideal_db=float(20 * np.log10(np.max(np.abs(p_equiv)) / np.max(np.abs(signals["ideal"])))),
        peak_freq=float(f[np.argmax(vE)]), ringing_20db=envelope_duration(t, signals["digitiser_in"], -20.0),
        clipped=bool(peak_raw > cfg["full_scale"]), lsb=q,
        sigma_in_raw=sig_raw / G, analysis_band=band,
    )
    return ChainResult(preset, d, c_s, grid, t, f, spectra, signals, t_dig, v_dig, v_bp, band, sig_raw, sig_bp, info)


def summary_rows(res: ChainResult) -> list[dict]:
    i = res.info
    lab = PRESETS[res.preset]
    rows = [
        ("Initial pressure p0 (energy-equivalent sphere)", i["p0"] / 1e3, "kPa", "[C]"),
        ("Absorbed energy", i["E_abs"] * 1e12, "pJ", "[C]"),
        ("Temperature rise", i["dT"] * 1e3, "mK", "[C]"),
        ("Ideal peak pressure at transducer", i["ideal_peak_analytic"], "Pa", "[C]"),
        ("Apparent source distance R_app", i["R_app"] * 1e3, "mm", "[C]"),
        ("Arrival time (sphere centre)", i["t_arrival"] * 1e6, "µs", "[C]"),
        ("Aperture time spread (defocus)", i["sir_spread"] * 1e9, "ns", "[C]"),
        ("Peak of received spectrum", i["peak_freq"] / 1e6, "MHz", "[C]"),
        ("Ringing (envelope above -20 dB)", i["ringing_20db"] * 1e9, "ns", "[C]"),
        ("Amplitude kept vs ideal pulse", i["loss_vs_ideal_db"], "dB", "[C]"),
        ("Analysis band", f"{i['analysis_band'][0]/1e6:.1f} to {i['analysis_band'][1]/1e6:.1f}", "MHz", "[C]"),
        ("Input noise density", i["e_n"] * 1e9, "nV/√Hz", "[C]"),
        ("Noise rms at digitiser (band-passed)", res.sigma_bp * 1e3, "mV", "[C]"),
        ("Signal peak at digitiser (band-passed)", i["peak_bp"] * 1e3, "mV", "[C]"),
        ("SNR single shot (band-passed)", i["snr_bp"], "dB", "[C]"),
        ("SNR single shot (raw trace)", i["snr_raw"], "dB", "[C]"),
        (f"SNR with {i['n_avg']} averages (band-passed)", i["snr_bp_avg"], "dB", "[C]"),
        (f"SNR with {i['n_budget']} averages (30 s at 1 kHz)", i["snr_bp_budget"], "dB", "[C]"),
        ("Averages needed for the 42.8 dB target", i["n_needed"], "shots", "[C]"),
    ]
    out = []
    for name, v, u, tag in rows:
        if isinstance(v, (float, int, np.floating)):
            v = f"{v:.3g}" if abs(v) < 1e4 else f"{v:.3e}"
        out.append({"chain": lab, "d (µm)": round(res.d * 1e6, 1), "quantity": name, "value": v, "unit": u, "tag": tag})
    return out
