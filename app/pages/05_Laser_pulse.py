import numpy as np
import pandas as pd
import streamlit as st

from common import checks_table, export, history, links, model_header, param_input, params, reset_button, run_section, setup
from plots import PALETTE, fig, vline
from u4.models import laser, sphere_pa
from u4.models.common import Grid, db20

setup("05 Laser pulse")
P = params()
model_header("5", "Laser pulse shape and duration",
             "The emitted pressure is the delta-heating response convolved with the normalised heating pulse. In the "
             "frequency domain the pulse acts as a low-pass filter whose half-amplitude point is 0.441/τ for a Gaussian.",
             [r"p(t)=p_\delta(t)\ast I(t),\qquad H_L(f)=\mathcal{F}\{I\}(f)",
              r"\text{Gaussian: } H_L=\exp\!\left[-\frac{(\pi f\tau)^2}{4\ln 2}\right],\quad f_{-6\,dB}=\frac{2\ln2}{\pi\tau}=\frac{0.441}{\tau}"],
             ["heating follows the pulse intensity (no thermal or stress relaxation)", "pulse shape unknown, Gaussian placeholder"],
             "CryLaS datasheet [S]; standard Fourier pair.")
st.markdown("#### Inputs")
c1, c2, c3 = st.columns(3)
with c1:
    tau = param_input(P, "today.laser.pulse_fwhm", "Pulse FWHM", 0.1, 3.0, 0.05, "s05:") * 1e-9
with c2:
    shape = st.selectbox("Shape", laser.SHAPES, index=0, key="s05:shape",
                         help="params.yaml: today.laser.pulse_shape = gaussian [C] TBD")
with c3:
    d = param_input(P, "cell.test_diameters", "Sphere diameter for the effect plot", 3, 25, 0.1, "s05:", index=0) * 1e-6
reset_button(["s05:"], "r05")
st.markdown("#### Run")
run_section("m1_laser", "filters for 1.3 and 0.5 ns")
g = Grid.from_params(P)
H = laser.filter_response(g.f, tau, shape)
fc = laser.cutoff(tau, shape)
st.markdown("#### Outputs")
st.markdown(f"<span class='num'>half-amplitude (-6 dB) frequency: **{fc/1e6:.0f} MHz**  ·  0.441/τ = {0.441/tau/1e6:.0f} MHz</span>",
            unsafe_allow_html=True)
o1, o2, o3 = st.columns(3)
sel_t = np.abs(g.t) < 3 * tau
f1 = fig(f"{shape} pulse, FWHM {tau*1e9:.2f} ns", "time (ns)", "heating rate (1/ns)")
f1.add_scatter(x=g.t[sel_t] * 1e9, y=laser.pulse(g.t[sel_t], tau, shape) * 1e-9, line=dict(color=PALETTE["today"]), name="I(t)")
o1.plotly_chart(f1, use_container_width=True)
sel = g.f < 3e9
f2 = fig(f"Low-pass: -6 dB at {fc/1e6:.0f} MHz", "frequency (MHz)", "|H_L| (dB)")
f2.add_scatter(x=g.f[sel] / 1e6, y=db20(H[sel], 1.0), line=dict(color=PALETTE["today"]), name="H_L")
vline(f2, fc / 1e6, "-6 dB")
f2.update_yaxes(range=[-40, 2])
o2.plotly_chart(f2, use_container_width=True)
c = P.si("cell.sound_speed")
S = sphere_pa.spectrum(g.f, d, c, 1.0, 1e-3)
f3 = fig(f"{d*1e6:.0f} µm sphere: gaps stay, high lobes drop", "frequency (MHz)", "dB re delta-heating peak")
f3.add_scatter(x=g.f[sel] / 1e6, y=db20(S[sel]), name="delta heating", line=dict(color=PALETTE["grey"], dash="dot"))
f3.add_scatter(x=g.f[sel] / 1e6, y=db20(S[sel] * H[sel], np.abs(S).max()), name="with pulse", line=dict(color=PALETTE["a"]))
f3.update_yaxes(range=[-70, 3])
o3.plotly_chart(f3, use_container_width=True)
export(f3, pd.DataFrame({"f_MHz": g.f[sel] / 1e6, "H_dB": db20(H[sel], 1.0)}), "laser_filter", "x05")
st.markdown("#### Verification")
checks_table([c.as_row() for c in laser.checks(P)])
st.markdown("#### History")
history("5", "laser_filter", "f_MHz", "H_dB", "|H_L| (dB)", "frequency (MHz)")
links(["src/u4/models/laser.py"])
