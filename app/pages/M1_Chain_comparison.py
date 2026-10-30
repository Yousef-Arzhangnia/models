import numpy as np
import pandas as pd
import streamlit as st

from common import checks_table, export, history, links, params, run_section, setup, tracker_checks_rows
from plots import PALETTE, fig
from u4.models import chain
from u4.models.common import db20

setup("M1 chain comparison")
P = params()
st.title("M1 chain comparison: today vs Upgrade 1")
st.markdown("#### What it models\nThe full analytical forward chain (models 1, 5, 7 simple, 8, 10, 11, 12) for a uniform "
            "sphere, through today's instrument and through the Upgrade 1 receive chain, side by side.")
st.latex(r"V(f)=P_{sphere}(f)\,H_L(f)\,H_W(f)\,H_P(f)\,H_{SIR}(f)\,S\,H_T(f)\,H_E(f),\quad "
         r"p_0=\frac{\Gamma E(1-e^{-\mu_a d})}{\pi d^3/6}")
st.markdown("**Assumptions:** energy-equivalent uniform sphere (model 7 simple); both sensitivities 5 µV/Pa; µa, Γ, "
            "noise figures and digitiser details are placeholders [C, TBD]. **References:** CONTEXT.md, P1, Diebold 1990.")
st.markdown("#### Inputs")
c1, c2, c3, c4 = st.columns(4)
d = c1.slider("Cell diameter (µm)", 3.0, 25.0, 12.0, 0.5, key="sch:d", help="M1 test cases 7 and 12 µm [S]")
c = c2.slider("Sound speed (m/s)", 1450, 1700, int(P.value("cell.sound_speed")), 5, key="sch:c",
              help=P.get("cell.sound_speed").label())
mua = c3.select_slider("µa at 532 nm (1/cm)", [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
                       value=P.value("cell.mua_532"), key="sch:mua", help=P.get("cell.mua_532").label())
W = c4.slider("Today's water path (mm)", 9.0, 15.0, float(P.value("today.sample.water_path")), 0.05, key="sch:W")
presets = st.multiselect("Chain presets", list(chain.PRESETS), default=list(chain.PRESETS),
                         format_func=lambda k: chain.PRESETS[k], key="sch:pre")
st.markdown("#### Run")
run_section("m1_chain", "both chains, 7 and 12 µm, all chain checks")

Po = P.with_overrides({"cell.sound_speed": c, "cell.mua_532": mua, "today.sample.water_path": W})


@st.cache_data(max_entries=30)
def sim(key, preset):
    return chain.simulate(Po, preset, d * 1e-6)


res = {p: sim(str((d, c, mua, W, p)), p) for p in presets}
st.markdown("#### Outputs")
cols = st.columns(max(1, len(res)))
rows = []
for col, (p, r) in zip(cols, res.items()):
    i = r.info
    with col:
        st.markdown(f"**{chain.PRESETS[p]}**")
        a, b, cc = st.columns(3)
        a.metric("SNR 1 shot", f"{i['snr_bp']:.1f} dB")
        b.metric(f"SNR {i['n_avg']} avg", f"{i['snr_bp_avg']:.1f} dB")
        cc.metric("spectrum peak", f"{i['peak_freq']/1e6:.0f} MHz")
        t_abs = (r.t_dig + i["t_arrival"]) * 1e6
        win = (t_abs > i["t_arrival"] * 1e6 - (0.1 if p == "today" else 0.01)) & (t_abs < i["t_arrival"] * 1e6 + (1.3 if p == "today" else 0.05))
        f1 = fig("Digitised waveform (noise-free)", "time after laser (µs)", "signal at digitiser (mV)", height=320)
        f1.add_scatter(x=t_abs[win], y=r.v_dig[win] * 1e3, line=dict(color=PALETTE[p]), name="clean")
        f1.add_scatter(x=t_abs[win], y=r.noisy_trace(i["n_avg"], band_passed=True)[win] * 1e3, name=f"{i['n_avg']} averages",
                       line=dict(color="#999999", width=1), opacity=0.7)
        st.plotly_chart(f1, use_container_width=True, key=f"w{p}")
        sel = (r.f > 0.3e6) & (r.f < (60e6 if p == "today" else 1.2e9))
        f2 = fig("Spectrum: received vs ideal", "frequency (MHz)", "dB re own peak", height=320)
        f2.add_scatter(x=r.f[sel] / 1e6, y=db20(r.spectra["digitiser_in"][sel]), name="received", line=dict(color=PALETTE[p]))
        f2.add_scatter(x=r.f[sel] / 1e6, y=db20(r.spectra["ideal"][sel], np.abs(r.spectra["ideal"]).max()), name="ideal",
                       line=dict(color="#888888", dash="dot"))
        for k, gp in enumerate(i["gaps"]):
            if gp < r.f[sel][-1]:
                f2.add_vline(x=gp / 1e6, line=dict(color="#BBBBBB", dash="dot", width=1))
        f2.update_yaxes(range=[-60, 3])
        st.plotly_chart(f2, use_container_width=True, key=f"s{p}")
        rows += chain.summary_rows(r)
tab = pd.DataFrame(rows)
if not tab.empty:
    tab["quantity (unit)"] = tab["quantity"] + " (" + tab["unit"] + ")"
st.dataframe(tab.pivot_table(index="quantity (unit)", columns="chain", values="value", aggfunc="first", sort=False),
             use_container_width=True)
st.caption("All numbers [C] from placeholders where params.yaml marks TBD. Absorbed energy and p0 are model 7 (simple).")
if res:
    export(f2, tab, "chain_summary", "xch")
st.markdown("#### Verification")
st.caption("Recorded chain checks from the last m1_chain run (start it above).")
checks_table(tracker_checks_rows("chain"))
st.markdown("#### History")
history("chain", "bead_spectrum", "f_MHz", "dB", "dB re peak", "frequency (MHz), bead case")
links(["src/u4/models/chain.py", "src/u4/models/absorption.py", "src/u4/studies/m1.py"])
