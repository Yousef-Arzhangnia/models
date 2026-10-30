"""Shared UI helpers for the board and the model pages (UI_SPEC.md sections 4, 5 and 7)."""
from __future__ import annotations

import io
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # works even without pip install -e .
    sys.path.insert(0, str(ROOT / "src"))

from u4 import tracker  # noqa: E402
from u4.params import Params  # noqa: E402

STATUS_COLORS = {"passed": "#2E8B57", "verifying": "#D9A21B", "blocked": "#D9A21B", "building": "#D9A21B",
                 "failed": "#C0392B", "error": "#C0392B", "not started": "#9AA0A6", "stopped": "#9AA0A6",
                 "running": "#D9A21B"}

# model registry for the board: number -> (name, milestone, page)
MODELS = [
    ("0", "Tracker demo", "M0", "pages/00_Demo.py"),
    ("1", "PA emission, uniform sphere", "M1", "pages/01_PA_sphere.py"),
    ("5", "Laser pulse shape and duration", "M1", "pages/05_Laser_pulse.py"),
    ("7", "Absorbed energy and p0 (simple)", "M1", "pages/M1_Chain_comparison.py"),
    ("8", "Water path attenuation", "M1", "pages/08_Water_attenuation.py"),
    ("10", "Transducer response and focal geometry", "M1", "pages/10_Transducer.py"),
    ("11", "Electronics: gain and noise", "M1", "pages/12_Noise_SNR.py"),
    ("12", "Noise and averaging", "M1", "pages/12_Noise_SNR.py"),
    ("chain", "M1 chain comparison", "M1", "pages/M1_Chain_comparison.py"),
    ("15", "Sensitivity and identifiability", "M2", None),
    ("2", "PA emission, core-shell", "M3", None), ("3", "US scattering, core-shell", "M3", None),
    ("9", "Substrate, agar, reverberation", "M3", None), ("13", "Library generation", "M3", None),
    ("4", "Real cell shape", "M4", None), ("6", "Beam profile, defocus", "M4", None), ("14", "Joint PA + US fit", "M4", None),
    ("19", "Synthetic datasets", "M5", None), ("20", "Classifier", "M5", None), ("21", "Batch-effect check", "M5", None),
    ("16", "Photothermal", "M6", None), ("17", "Elastography", "M6", None), ("18", "Dose", "M6", None),
]
HEADLINE = {"0": "tbd_count", "1": "first_gap_12um", "5": "cutoff_today", "7": "p0_today_12um",
            "8": "water_loss_upgrade1_375MHz", "10": "focus_water_distance_today", "11": "noise_density_today",
            "12": "snr1_today_12um", "chain": "snr_gain_upgrade1_min"}
REPORTS = {"M0": "reports/M0_report.md", "M1": "reports/M1_report.md"}

CSS = """
<style>
.num {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;}
.chip {display:inline-block; padding:1px 9px; border-radius:10px; color:white; font-size:0.78rem; font-weight:600;}
.card {border:1px solid rgba(128,128,128,0.35); border-radius:8px; padding:8px 10px; margin-bottom:8px;}
.card.grey {opacity:0.45;}
.small {font-size:0.82rem; opacity:0.85;}
[data-testid="stMetricValue"] {font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;}
</style>
"""


def setup(title: str, icon: str = "🔬"):
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def chip(status: str) -> str:
    return f"<span class='chip' style='background:{STATUS_COLORS.get(status, '#9AA0A6')}'>{status}</span>"


@st.cache_data(ttl=2)
def _load_params_cached(mtime: float):
    return Params.load(ROOT / "params.yaml").raw


def params() -> Params:
    p = ROOT / "params.yaml"
    return Params(_load_params_cached(p.stat().st_mtime), p)


# --------------------------------------------------------------------------- model status from the tracker
def model_status(model: str) -> dict:
    act = tracker.query("SELECT * FROM runs WHERE model=? AND status='running' ORDER BY started DESC LIMIT 1", (model,))
    last = tracker.latest_finished(model)
    out = dict(status="not started", last=None, n_pass=0, n_tot=0, headline="", run=None)
    if last:
        cs = tracker.run_checks(last["id"])
        out.update(last=last["ended"] or last["started"], run=last, n_pass=sum(c["passed"] for c in cs), n_tot=len(cs))
        ext_fail = any((not c["passed"]) and c["kind"] == "external" for c in cs)
        if last["status"] in ("failed", "error"):
            out["status"] = "failed"
        elif last["status"] == "stopped":
            out["status"] = "not started"
        else:
            out["status"] = "blocked" if ext_fail else "passed"
        key = HEADLINE.get(model)
        for r in tracker.run_results(last["id"]):
            if r["key"] == key:
                v = r["value"]
                out["headline"] = f"{key.replace('_', ' ')} = {v:.4g} {r['unit']} {r['tag']}" if v is not None else r["text"]
    if act:
        out["status"] = "verifying"
    return out


# --------------------------------------------------------------------------- page building blocks
def param_input(P: Params, path: str, label: str, lo: float, hi: float, step: float, key_prefix: str = "",
                fmt: str | None = None, index: int | None = None):
    """Slider prefilled from params.yaml (file units). Shows unit, tag and TBD flag."""
    p = P.get(path)
    v = p.value[index] if index is not None else p.value
    key = f"{key_prefix}{path}{'' if index is None else f'[{index}]'}"
    if key not in st.session_state:
        st.session_state[key] = float(v)
    unit = "" if p.unit in ("-", "1") else f" ({p.unit})"
    tbd = " · TBD" if p.tbd else ""
    return st.slider(f"{label}{unit}", float(lo), float(hi), step=float(step), key=key, format=fmt,
                     help=f"params.yaml: {path} = {p.label()}. {p.note}")


def reset_button(prefix_paths: list[str], key: str = "reset"):
    if st.button("Reset to params.yaml", key=key):
        for k in list(st.session_state.keys()):
            if any(k.startswith(pp) for pp in prefix_paths):
                del st.session_state[k]
        st.rerun()


def checks_table(rows: list):
    if not rows:
        st.info("No checks recorded yet.")
        return
    df = pd.DataFrame([r.as_row() if hasattr(r, "as_row") else r for r in rows])
    n_pass = int((df["result"] == "pass").sum())
    st.markdown(f"**{n_pass} / {len(df)} checks passed.** Internal checks test the code; external checks compare "
                "with literature or bench values and need a decision when they fail.")

    def colour(v):
        return "color: #2E8B57; font-weight:600" if v == "pass" else "color: #C0392B; font-weight:600"
    st.dataframe(df.style.map(colour, subset=["result"]), use_container_width=True, hide_index=True)


def tracker_checks_rows(model: str) -> list[dict]:
    last = tracker.latest_finished(model)
    if not last:
        return []
    return [dict(model=model, check=c["name"], kind=c["kind"], expected=c["expected"], obtained=c["obtained"],
                 result="pass" if c["passed"] else "FAIL", note=c["note"]) for c in tracker.run_checks(last["id"])]


def history(model: str, data_name: str, x: str, y_prefix: str = "", y_label: str = "", x_label: str = ""):
    import plotly.graph_objects as go
    rs = tracker.runs(model, limit=50)
    if not rs:
        st.info("No runs of this model yet. Start one with the button above or from the command line.")
        return
    tab = pd.DataFrame([{"run": r["id"], "study": r["study"], "status": r["status"],
                         "started": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["started"])),
                         "checks": f"{sum(c['passed'] for c in tracker.run_checks(r['id']))}/{len(tracker.run_checks(r['id']))}"}
                        for r in rs])
    st.dataframe(tab, use_container_width=True, hide_index=True, height=min(250, 38 + 35 * len(tab)))
    choose = st.multiselect("Overlay saved results of runs", tab["run"].tolist(), default=tab["run"].tolist()[:1],
                            key=f"hist_{model}_{data_name}")
    fig = go.Figure()
    for rid in choose:
        arts = [a for a in tracker.run_artefacts(rid, "data") if a["name"] == data_name]
        if not arts or not Path(arts[0]["path"]).exists():
            continue
        df = pd.read_csv(arts[0]["path"])
        for col in [c for c in df.columns if c != x and c.startswith(y_prefix)]:
            fig.add_scatter(x=df[x], y=df[col], mode="lines", name=f"{rid[-6:]} {col}")
    if fig.data:
        fig.update_layout(height=320, xaxis_title=x_label or x, yaxis_title=y_label, margin=dict(t=20, b=40))
        st.plotly_chart(fig, use_container_width=True)


def _plotly_to_mpl(fig):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    m, ax = plt.subplots(figsize=(8, 4.2))
    for tr in fig.data:
        if getattr(tr, "x", None) is None or getattr(tr, "y", None) is None:
            continue
        dash = getattr(getattr(tr, "line", None), "dash", None)
        ax.plot(np.asarray(tr.x, float), np.asarray(tr.y, float), label=tr.name,
                ls=":" if dash in ("dot", "dash") else "-", lw=1.2)
    lay = fig.layout
    ax.set_xlabel(lay.xaxis.title.text or ""); ax.set_ylabel(lay.yaxis.title.text or "")
    if lay.xaxis.type == "log":
        ax.set_xscale("log")
    if lay.yaxis.type == "log":
        ax.set_yscale("log")
    if lay.xaxis.range:
        ax.set_xlim(*lay.xaxis.range)
    if lay.yaxis.range:
        ax.set_ylim(*lay.yaxis.range)
    ax.grid(alpha=0.3)
    if any(tr.name for tr in fig.data):
        ax.legend(fontsize=7)
    ax.set_title(lay.title.text or "", fontsize=10, loc="left")
    return m


def export(fig, df: pd.DataFrame | None, name: str, key: str):
    c1, c2, c3 = st.columns(3)
    try:
        m = _plotly_to_mpl(fig)
        for col, fmt in ((c1, "png"), (c2, "svg")):
            buf = io.BytesIO()
            m.savefig(buf, format=fmt, dpi=150, bbox_inches="tight")
            col.download_button(f"Figure ({fmt.upper()})", buf.getvalue(), f"{name}.{fmt}", key=f"{key}_{fmt}")
        import matplotlib.pyplot as plt
        plt.close(m)
    except Exception as e:  # export should never break a page
        c1.caption(f"figure export unavailable: {e}")
    if df is not None:
        c3.download_button("Data (CSV)", df.to_csv(index=False).encode(), f"{name}.csv", key=f"{key}_csv")


def start_study(name: str) -> None:
    flags = 0
    if sys.platform.startswith("win"):
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([sys.executable, "-m", "u4", "run", name], cwd=str(ROOT), creationflags=flags,
                     env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_section(study: str, label: str):
    c1, c2 = st.columns([1, 3])
    if c1.button(f"Start study '{study}' in the background", key=f"start_{study}"):
        start_study(study)
        c2.success(f"Started. It appears on the board within a few seconds (or: python -m u4 run {study}).")
    else:
        c2.caption(f"Quick results below are computed in the page. The recorded study ({label}) runs outside the UI, "
                   f"reports to the tracker and fills Verification and History. CLI: `python -m u4 run {study}`")


def links(files: list[str], report: str = "reports/M1_report.md"):
    st.markdown("**Links**")
    for f in files:
        st.markdown(f"- source: `{f}`")
    st.markdown(f"- milestone report: `{report}` (rendered on the Reports page)")
    st.page_link("pages/99_Reports.py", label="Open the Reports page", icon="📄")


def model_header(number: str, name: str, what: str, equations: list[str], assumptions: list[str], refs: str):
    st.title(f"Model {number}: {name}")
    st.markdown("#### What it models")
    st.markdown(what)
    for e in equations:
        st.latex(e)
    st.markdown("**Assumptions:** " + " ".join(f"({i+1}) {a}" for i, a in enumerate(assumptions)))
    st.markdown(f"**References:** {refs}")
