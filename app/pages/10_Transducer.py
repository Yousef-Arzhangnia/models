import numpy as np
import pandas as pd
import streamlit as st

from common import checks_table, export, history, links, model_header, params, run_section, setup
from plots import PALETTE, fig, vline
from u4.models import chain, sphere_pa, transducer, water
from u4.models.common import Grid, db20

setup("10 Transducer")
P = params()
model_header("10", "Transducer response and focal geometry",
             "Log-Gaussian magnitude with the -6 dB edges exactly at the given band, minimum phase (causal ringing). "
             "For today's focused PVDF transducer, an on-axis point source is integrated over the spherical cap with "
             "Snell refraction through the PMMA floor; the spread of arrival times low-passes the signal when the "
             "source is not at the acoustic focus.",
             [r"|H_T(f)|=\exp\!\left[-\ln2\left(\frac{\ln(f/f_c)}{w}\right)^2\right],\ w=\ln\frac{f_c}{f_{lo}}\ (f<f_c),\ \ln\frac{f_{hi}}{f_c}\ (f>f_c)",
              r"\langle p\rangle_{face}(t)=p(R_{app},t)\ast\sum_i w_i\,\delta(t-\Delta\tau_i),\quad R_{app}=W+L\,\frac{c_p}{c_w},\quad W_{focus}=R-L\,\frac{c_p}{c_w}"],
             ["sensitivity S is a constant times the normalised response", "on-axis source, normal-incidence plate transmission for all rays",
              "Upgrade 1 cell exactly at focus"],
             "Today: certificate [M], datasheet [S]. Upgrade 1: P1 375 MHz unit [L, P1], band target [S].")
st.markdown("#### Inputs")
c1, c2, c3, c4 = st.columns(4)
preset = c1.selectbox("Preset", ["today (20 MHz)", "P1 375 MHz (Upgrade 1)", "custom"], key="s10:preset")
pk = "today" if preset.startswith("today") else "upgrade1"
fc0, (lo0, hi0) = P.value(f"{pk}.transducer.centre_frequency"), P.value(f"{pk}.transducer.band_6db")
custom = preset == "custom"
fc = c2.number_input("Centre (MHz)", 1.0, 2000.0, float(fc0), disabled=not custom, key=f"s10:fc{preset}") * 1e6
lo = c3.number_input("-6 dB low edge (MHz)", 0.5, 2000.0, float(lo0), disabled=not custom, key=f"s10:lo{preset}") * 1e6
hi = c4.number_input("-6 dB high edge (MHz)", 1.0, 3000.0, float(hi0), disabled=not custom, key=f"s10:hi{preset}") * 1e6
st.caption(f"params.yaml: {pk}.transducer.centre_frequency = {P.get(pk + '.transducer.centre_frequency').label()}; "
           f"band_6db = {P.get(pk + '.transducer.band_6db').label()}")
W = st.slider("Today's water path, apex to PMMA (mm), for the defocus panel", 9.0, 15.0,
              float(P.value("today.sample.water_path")), 0.05, key="s10:W",
              help=P.get("today.sample.water_path").label())
if lo >= fc or hi <= fc:
    st.error("Band edges must bracket the centre frequency.")
    st.stop()
st.markdown("#### Run")
run_section("m1_transducer", "certificate fit, focus through PMMA")

g = Grid.from_params(P)
mag = transducer.magnitude(g.f, fc, lo, hi)
H = transducer.min_phase(mag, g.n)
h = g.to_time(H)
st.markdown("#### Outputs")
o1, o2, o3 = st.columns(3)
sel = (g.f > 0) & (g.f < 4 * hi)
f1 = fig("Response: -6 dB edges at the band", "frequency (MHz)", "|H_T| (dB)")
f1.add_scatter(x=g.f[sel] / 1e6, y=db20(mag[sel], 1.0), line=dict(color=PALETTE["today"]), name="|H_T|")
for x in (lo, fc, hi):
    vline(f1, x / 1e6)
f1.update_yaxes(range=[-40, 2])
o1.plotly_chart(f1, use_container_width=True)
d = P.si("cell.test_diameters")[1]
sp = sphere_pa.spectrum(g.f, d, P.si("cell.sound_speed"), 1.0, 1e-3) * H
x = g.to_time(sp)
span = 40 / fc
selt = (g.t > -0.2 * span) & (g.t < span)
f2 = fig("Impulse response and filtered 12 µm pulse", "time (ns)", "normalised")
f2.add_scatter(x=g.t[selt] * 1e9, y=h[selt] / np.abs(h).max(), name="impulse response", line=dict(color=PALETTE["grey"]))
f2.add_scatter(x=g.t[selt] * 1e9, y=x[selt] / np.abs(x).max(), name="12 µm sphere through H_T", line=dict(color=PALETTE["b"]))
o2.plotly_chart(f2, use_container_width=True)
cfg = chain.config(P, "today")
Ws = np.linspace(9.0e-3, 15e-3, 61)
spreads = [np.ptp(transducer.ray_delays(cfg["A"], cfg["R"], w, cfg["L"], cfg["c_w"], cfg["c_p"], 150)[0]) * 1e9 for w in Ws]
cur = np.ptp(transducer.ray_delays(cfg["A"], cfg["R"], W * 1e-3, cfg["L"], cfg["c_w"], cfg["c_p"], 300)[0]) * 1e9
f3 = fig(f"Today at {W:.2f} mm: {cur:.0f} ns spread, first notch {1e3/cur if cur > 0 else float('inf'):.0f} MHz",
         "water path (mm)", "arrival spread over aperture (ns)")
f3.add_scatter(x=Ws * 1e3, y=spreads, line=dict(color=PALETTE["today"]), name="spread")
vline(f3, cfg["W_focus"] * 1e3, "focus")
vline(f3, W, "selected", color=PALETTE["upgrade1"], dash="solid")
o3.plotly_chart(f3, use_container_width=True)
export(f1, pd.DataFrame({"f_MHz": g.f[sel] / 1e6, "H_dB": db20(mag[sel], 1.0)}), "transducer_response", "x10")
st.markdown("#### Verification")
checks_table([c.as_row() for c in transducer.checks(P)])
st.markdown("#### History")
history("10", "defocus_spread", "W_mm", "spread", "spread (ns)", "water path (mm)")
links(["src/u4/models/transducer.py"])
