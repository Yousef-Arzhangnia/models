import numpy as np
import pandas as pd
import streamlit as st

from common import checks_table, export, history, links, model_header, param_input, params, reset_button, run_section, setup
from plots import PALETTE, fig
from u4.models import chain, electronics, noise

setup("12 Noise and SNR")
P = params()
model_header("12", "Noise and averaging (with model 11: gain and noise)",
             "Amplified first-stage noise is folded into the digitiser's Nyquist band and added to quantisation and ADC "
             "noise. SNR is the signal peak over the noise rms, on the raw trace and after a digital band-pass over the "
             "band where the clean signal is within 20 dB of its peak. Averaging N independent shots adds 10 log10 N.",
             [r"e_n=\sqrt{4k_BTR_sF},\quad \sigma^2=\int e_n^2|H_E|^2\,df\ (\text{folded})+\frac{LSB^2}{12}+\sigma_{ADC}^2",
              r"\mathrm{SNR}=20\log_{10}\frac{\max|s|}{\sigma},\qquad \mathrm{SNR}_N=\mathrm{SNR}_1+10\log_{10}N"],
             ["white first-stage noise", "no jitter or drift between shots", "sensitivity and noise figure are placeholders"],
             "Standard noise theory; gains from CONTEXT.md [M], [S].")
st.markdown("#### Inputs")
c1, c2, c3, c4 = st.columns(4)
preset = c1.radio("Chain", list(chain.PRESETS), format_func=lambda k: chain.PRESETS[k], key="s12:preset")
d = c1.slider("Cell diameter (µm)", 3.0, 25.0, 12.0, 0.5, key="s12:d")
with c2:
    nf = param_input(P, f"{preset}.electronics.noise_figure", "Noise figure", 0.5, 15.0, 0.5, "s12:")
    S = param_input(P, f"{preset}.transducer.sensitivity", "Sensitivity", 0.1, 50.0, 0.1, "s12:")
with c3:
    mua = st.select_slider("µa at 532 nm (1/cm)", [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
                           value=P.value("cell.mua_532"), key="s12:mua", help=P.get("cell.mua_532").label())
    bits = param_input(P, f"{preset}.digitiser.bits", "Digitiser bits", 8, 16, 1, "s12:")
with c4:
    n_avg = int(param_input(P, f"{preset}.acquisition.averages", "Averages", 1, 100000, 1, "s12:"))
reset_button(["s12:"], "r12")
st.markdown("#### Run")
run_section("m1_noise", "SNR for both chains and sizes, µa sweep")

Po = P.with_overrides({f"{preset}.electronics.noise_figure": nf, f"{preset}.transducer.sensitivity": S,
                       f"{preset}.digitiser.bits": int(bits), f"{preset}.acquisition.averages": n_avg, "cell.mua_532": mua})


@st.cache_data(max_entries=20)
def sim(raw_key, preset, d):
    r = chain.simulate(Po, preset, d * 1e-6)
    return r


r = sim(str((preset, nf, S, bits, n_avg, mua)), preset, d)
i = r.info
st.markdown("#### Outputs")
m = st.columns(5)
m[0].metric("SNR, 1 shot (band-passed)", f"{i['snr_bp']:.1f} dB")
m[1].metric("SNR, 1 shot (raw)", f"{i['snr_raw']:.1f} dB")
m[2].metric(f"SNR, {n_avg} averages", f"{noise.averaged_snr_db(i['snr_bp'], n_avg):.1f} dB")
m[3].metric("Shots for 42.8 dB", f"{i['n_needed']:.3g}")
m[4].metric("Noise density e_n", f"{i['e_n']*1e9:.2f} nV/√Hz")
st.caption(f"Analysis band {r.band[0]/1e6:.1f} to {r.band[1]/1e6:.1f} MHz · noise rms {r.sigma_bp*1e3:.3f} mV "
           f"(raw {r.sigma_raw*1e3:.3f} mV) · gain {i['gain_db']:.1f} dB · LSB {i['lsb']*1e3:.3f} mV · "
           f"clipping: {'yes' if i['clipped'] else 'no'}. Placeholders tagged [C, TBD] in params.yaml.")
o1, o2 = st.columns(2)
N = np.logspace(0, 5, 60)
f1 = fig("SNR versus number of averages", "averages N", "SNR, band-passed (dB)", logx=True)
f1.add_scatter(x=N, y=i["snr_bp"] + 10 * np.log10(N), line=dict(color=PALETTE[preset]), name=preset)
f1.add_hline(y=P.value("goal.snr_target"), line=dict(dash="dot"), annotation_text="target 42.8 dB [S]")
o1.plotly_chart(f1, use_container_width=True)
t_abs = (r.t_dig + i["t_arrival"]) * 1e6
win = (t_abs > i["t_arrival"] * 1e6 - (0.1 if preset == "today" else 0.01)) & (t_abs < i["t_arrival"] * 1e6 + (1.2 if preset == "today" else 0.05))
f2 = fig("Example trace (band-passed): 1 shot and averaged", "time after laser (µs)", "signal at digitiser (mV)")
f2.add_scatter(x=t_abs[win], y=r.noisy_trace(1)[win] * 1e3, name="1 shot", line=dict(color="#BBBBBB", width=1))
f2.add_scatter(x=t_abs[win], y=r.noisy_trace(n_avg, seed=2)[win] * 1e3, name=f"{n_avg} averages", line=dict(color=PALETTE[preset]))
f2.add_scatter(x=t_abs[win], y=r.v_dig_bp[win] * 1e3, name="noise-free", line=dict(color="black", dash="dot", width=1))
o2.plotly_chart(f2, use_container_width=True)
f = np.logspace(5, 9.7, 400)
f3 = fig("Electronics response (model 11)", "frequency (MHz)", "|H_E| (dB)", logx=True, height=300)
f3.add_scatter(x=f / 1e6, y=20 * np.log10(np.abs(electronics.response(Po, preset, f))), line=dict(color=PALETTE[preset]), name="H_E")
st.plotly_chart(f3, use_container_width=True)
export(f2, pd.DataFrame({"t_us": t_abs[win], "clean_mV": r.v_dig_bp[win] * 1e3, "one_shot_mV": r.noisy_trace(1)[win] * 1e3}),
       "noise_trace", "x12")
st.markdown("#### Verification")
checks_table([c.as_row() for c in noise.checks(P)] + [c.as_row() for c in electronics.checks(P)])
st.markdown("#### History")
history("12", "snr_table", "d_um", "snr1", "single-shot SNR (dB)", "diameter (µm)")
links(["src/u4/models/noise.py", "src/u4/models/electronics.py"])
