import numpy as np
import pandas as pd
import streamlit as st

from common import (checks_table, export, history, links, model_header, param_input, params, reset_button,
                    run_section, setup)
from plots import PALETTE, fig, vline
from u4.models import sphere_pa
from u4.models.common import Grid, db20

setup("01 PA sphere")
P = params()
model_header("1", "PA emission, uniform sphere",
             "A uniformly and instantly heated fluid sphere emits an N-shaped pressure pulse of length d/c. Its spectrum "
             "is zero wherever tan x = x (x = π f d / c), so the gap positions depend on c/d only. Diebold's "
             "frequency-domain solution also covers a density or sound-speed mismatch with the medium.",
             [r"p(r,\tau)=\frac{p_0}{2r}\,(-c\tau),\quad |\tau|<\frac{a}{c};\qquad T=\frac{d}{c}",
              r"P(\omega)=-i\,\frac{p_0a^2}{r c_s}\,\frac{\sin\hat q-\hat q\cos\hat q}{\hat q^2\,D(\hat q)}\,e^{i\omega a/c_f},"
              r"\quad D=(1-\hat\rho)\frac{\sin\hat q}{\hat q}-\cos\hat q-i\hat\rho\hat c\sin\hat q,\quad \hat q=\frac{\omega a}{c_s}",
              r"f_{gap,n}=k_n\,\frac{c_s}{d},\quad k_n=1.4303,\;2.4590,\;3.4709"],
             ["delta heating (laser is model 5)", "uniform absorption (model 7)", "fluid sphere, no shear",
              "spherical symmetry (flattening is model 4)"],
             "[L, Diebold, Khan, Park, Science 250 (1990) 101]; cited in P2.")

st.markdown("#### Inputs")
c1, c2, c3 = st.columns(3)
with c1:
    d = param_input(P, "cell.test_diameters", "Diameter", 3, 25, 0.1, "s01:", index=1) * 1e-6
with c2:
    c = param_input(P, "cell.sound_speed", "Sound speed of sphere", 1400, 1700, 1, "s01:")
with c3:
    rho_ratio = st.slider("Density ratio ρ_s/ρ_f (1 = matched)", 0.8, 1.3, 1.0, 0.01, key="s01:rho")
    c_f = st.slider("Medium sound speed c_f (m/s); 0 = matched", 0, 1600, 0, 1, key="s01:cf",
                    help="0 uses c_f = c_s (matched, Diebold's simplest case).")
reset_button(["s01:"], "r01")

st.markdown("#### Run")
run_section("m1_sphere", "gap check for 7 and 12 µm")

g = Grid.from_params(P)
cf = c if c_f == 0 else float(c_f)
spec = sphere_pa.spectrum(g.f, d, c, 1.0, 1e-3, c_f=cf, rho_s=rho_ratio * 1000, rho_f=1000)
p = g.to_time(spec)
gaps = sphere_pa.gap_frequencies(d, c, 3)
found = sphere_pa.find_zeros(g.f, np.abs(spec), gaps)

st.markdown("#### Outputs")
o1, o2 = st.columns(2)
sel_t = np.abs(g.t) < max(3 * d / c, 10e-9)
f1 = fig(f"Pulse length {d/c*1e9:.2f} ns = d/c", "retarded time τ (ns)", "pressure (normalised, r = 1 mm)")
f1.add_scatter(x=g.t[sel_t] * 1e9, y=p[sel_t] / np.abs(p).max(), name="frequency-domain solution", line=dict(color=PALETTE["b"]))
if rho_ratio == 1.0 and c_f == 0:
    f1.add_scatter(x=g.t[sel_t] * 1e9, y=sphere_pa.n_pulse(g.t[sel_t], d, c, 1.0, 1e-3) / np.abs(p).max(),
                   name="exact N-wave", line=dict(color=PALETTE["grey"], dash="dot"))
o1.plotly_chart(f1, use_container_width=True)
sel = g.f < max(6 * c / d, 1e9)
f2 = fig(f"First gap at {gaps[0]/1e6:.1f} MHz = 1.43 c/d", "frequency (MHz)", "|P(f)| (dB re peak)")
f2.add_scatter(x=g.f[sel] / 1e6, y=db20(spec[sel]), name="spectrum", line=dict(color=PALETTE["b"]))
for k, gp in enumerate(gaps):
    vline(f2, gp / 1e6, f"{sphere_pa.gap_constants(3)[k]:.2f} c/d")
f2.update_yaxes(range=[-70, 3])
o2.plotly_chart(f2, use_container_width=True)
tab = pd.DataFrame({"gap": [1, 2, 3], "k (c/d)": np.round(sphere_pa.gap_constants(3), 4),
                    "expected (MHz)": np.round(gaps / 1e6, 2), "found in spectrum (MHz)": np.round(found / 1e6, 2),
                    "error (%)": np.round((found / gaps - 1) * 100, 3)})
st.dataframe(tab, hide_index=True, use_container_width=True)
st.caption("Placeholder values: c = 1550 m/s [C, TBD]. Diameters 7 and 12 µm are M1 test cases [S].")
export(f2, pd.DataFrame({"f_MHz": g.f[sel] / 1e6, "dB": db20(spec[sel])}), "sphere_spectrum", "x01")

st.markdown("#### Verification")


@st.cache_data
def _checks(_mt):
    return [c.as_row() for c in sphere_pa.checks(P)]


checks_table(_checks(P.source.stat().st_mtime))
st.markdown("#### History")
history("1", "spectrum", "f_MHz", "dB", "dB re peak", "frequency (MHz)")
links(["src/u4/models/sphere_pa.py", "tests/test_m1.py::test_model_checks[1]"])
