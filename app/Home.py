"""The board (UI_SPEC.md section 4). Reads only the tracker database and params.yaml."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from common import MODELS, REPORTS, ROOT, chip, model_status, params, setup, tracker

setup("Upgrade 4 board", "📋")
P = params()
active_ms = P.value("meta.active_milestone")

st.markdown(f"## {P.value('meta.project')}")
in_ms = [m for m in MODELS if m[2] == active_ms]
statuses = {m[0]: model_status(m[0]) for m in MODELS if m[3]}
n_ok = sum(1 for m in in_ms if statuses.get(m[0], {}).get("status") in ("passed", "blocked"))
c1, c2 = st.columns([1, 3])
c1.metric("Active milestone", active_ms)
c2.markdown(f"**Models with a completed, recorded run in {active_ms}: {n_ok} / {len(in_ms)}** "
            "(blocked = code checks pass, an external comparison needs a decision)")
c2.progress(n_ok / max(1, len(in_ms)))

live = st.toggle("Live refresh every 5 s", value=True, help="Polls the tracker database; never runs simulations.")


@st.fragment(run_every=5 if live else None)
def live_runs():
    try:
        tracker.mark_stale()
    except Exception:
        pass
    st.markdown("### Live runs")
    act = tracker.active_runs()
    if not act:
        st.caption(f"No run active. Start one with `python -m u4 run demo` or `python -m u4 run m1`. "
                   f"Last refresh {time.strftime('%H:%M:%S')}.")
    for r in act:
        el = time.time() - r["started"]
        prog = r["progress"] or 0.0
        eta = el / prog * (1 - prog) if prog > 0.01 else None
        cols = st.columns([3, 4, 1])
        cols[0].markdown(f"**{r['study']}** · model {r['model']} · {r['milestone']}<br>"
                         f"<span class='num small'>elapsed {el:5.0f} s · remaining "
                         f"{'?' if eta is None else f'{eta:5.0f} s'}</span>", unsafe_allow_html=True)
        cols[1].progress(prog, text=r["message"] or "")
        if cols[2].button("Stop", key=f"stop_{r['id']}"):
            tracker.request_stop(r["id"])
            st.toast(f"Stop flag written for {r['id']}")
        with st.expander("last 10 log lines"):
            st.code("".join(tracker.tail_log(r["log_path"], 10)) or "(empty)")
    recent = tracker.runs(limit=6)
    if recent:
        st.markdown("<span class='small'>Recent runs: " + " · ".join(
            f"{x['study']} {chip(x['status'])}" for x in recent) + "</span>", unsafe_allow_html=True)

    st.markdown("### Milestone lanes")
    lanes = st.columns(7)
    for col, ms in zip(lanes, ["M0", "M1", "M2", "M3", "M4", "M5", "M6"]):
        col.markdown(f"**{ms}**")
        future = ms > active_ms
        for num, name, m_ms, page in [m for m in MODELS if m[2] == ms]:
            s = model_status(num) if page else dict(status="not started", last=None, n_pass=0, n_tot=0, headline="")
            last = time.strftime("%d.%m %H:%M", time.localtime(s["last"])) if s["last"] else "never"
            grey = " grey" if future else ""
            label = f"Model {num}" if num not in ("chain", "0") else ("Chain" if num == "chain" else "Demo")
            col.markdown(
                f"<div class='card{grey}'><b>{label}</b> {chip(s['status'])}<br><span class='small'>{name}</span><br>"
                f"<span class='num small'>last {last} · checks {s['n_pass']}/{s['n_tot']}</span><br>"
                f"<span class='num small'>{s['headline']}</span></div>", unsafe_allow_html=True)
            if page and not future:
                col.page_link(page, label="page", icon="↗")
        if ms in REPORTS and (ROOT / REPORTS[ms]).exists():
            col.page_link("pages/99_Reports.py", label=f"{ms} report", icon="📄")


live_runs()

st.markdown("### Recent figures")
figs = tracker.recent_figures(6)
if not figs:
    st.caption("No figures yet.")
else:
    page_of = {m[0]: m[3] for m in MODELS}
    cols = st.columns(3)
    for i, fg in enumerate(figs):
        with cols[i % 3]:
            if Path(fg["path"]).exists():
                st.image(fg["path"], use_container_width=True)
            st.caption(f"{fg['name']} · {fg['study']} · model {fg['model']}")
            if page_of.get(fg["model"]):
                st.page_link(page_of[fg["model"]], label="model page", icon="↗")

st.markdown("### Open values (TBD in params.yaml)")
rows = [{"parameter": p.path, "placeholder": p.label().replace(" TBD", ""), "note": p.note} for p in P.tbd()]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=420)
st.caption("Status source: tracker database runs/status.sqlite and params.yaml only. The board never runs simulations.")
