import numpy as np
import pandas as pd
import streamlit as st

from common import checks_table, export, history, links, model_header, param_input, params, reset_button, run_section, setup
from plots import PALETTE, fig
from u4.models import water
from u4.models.common import db20

setup("08 Water attenuation")
P = params()
model_header("8", "Water path attenuation (and the PMMA floor)",
             "Water attenuation grows with f² and falls with temperature. Today's signal also crosses the 0.7 mm PMMA "
             "floor of the slide, modelled as a fluid layer at normal incidence (impedance mismatch, resonances, loss).",
             [r"L_{dB}(f)=A_3(T)\,f^2\,L,\qquad A_3:\ \text{Francois and Garrison (1982), dB/(m MHz}^2)",
              r"T_{plate}=\left[\cos kL+\tfrac{i}{2}\left(m+\tfrac1m\right)\sin kL\right]^{-1},\quad m=\frac{\rho_pc_p}{\rho_wc_w}"],
             ["dispersion neglected (zero-phase loss)", "plate at normal incidence, no shear waves",
              "PMMA properties typical values (TBD)"],
             "[L, Francois and Garrison 1982], [L, Pinkerton 1949], [L, Marczak 1997], P1 as quoted in CONTEXT.md.")
st.markdown("#### Inputs")
c1, c2, c3 = st.columns(3)
with c1:
    L = param_input(P, "today.sample.water_path", "Water path", 0.01, 20, 0.01, "s08:") * 1e-3
with c2:
    T = param_input(P, "today.sample.water_temperature", "Temperature", 5, 45, 0.5, "s08:")
with c3:
    Lp = param_input(P, "today.sample.pmma_thickness", "PMMA thickness (0 = none)", 0.0, 2.0, 0.05, "s08:") * 1e-3
reset_button(["s08:"], "r08")
st.markdown("#### Run")
run_section("m1_water", "today and Upgrade 1 paths, P1 comparison")
f = np.linspace(0.5e6, 1.5e9, 3000)
loss = water.loss_db(P, f, L, T)
st.markdown("#### Outputs")
a = water.alpha_coeff(P, T)
st.markdown(f"<span class='num'>α/f² = {a/100:.5f} dB/(cm MHz²) at {T} °C · c = {water.sound_speed(P, T):.1f} m/s · "
            f"loss at 20 MHz {water.loss_db(P, np.array([20e6]), L, T)[0]:.2f} dB, at 375 MHz "
            f"{water.loss_db(P, np.array([375e6]), L, T)[0]:.2f} dB</span>", unsafe_allow_html=True)
o1, o2 = st.columns(2)
f1 = fig(f"{L*1e3:.2f} mm of water at {T} °C", "frequency (MHz)", "one-way loss (dB)", logy=True)
f1.add_scatter(x=f / 1e6, y=loss, name="water", line=dict(color=PALETTE["upgrade1"]))
f1.update_yaxes(range=[-3, 2.5])
o1.plotly_chart(f1, use_container_width=True)
fp = np.linspace(0.1e6, 80e6, 3000)
Tp = water.plate_transfer(P, fp, Lp, T)
f2 = fig(f"PMMA plate {Lp*1e3:.2f} mm: transmission", "frequency (MHz)", "|T| (dB)")
f2.add_scatter(x=fp / 1e6, y=db20(Tp, 1.0), name="plate", line=dict(color=PALETTE["today"]))
f2.update_yaxes(range=[-10, 1])
o2.plotly_chart(f2, use_container_width=True)
export(f1, pd.DataFrame({"f_MHz": f / 1e6, "loss_dB": loss}), "water_loss", "x08")
st.markdown("#### Verification")
checks_table([c.as_row() for c in water.checks(P)])
st.markdown("#### History")
history("8", "water_loss", "f_MHz", "loss", "loss (dB)", "frequency (MHz)")
links(["src/u4/models/water.py"])
