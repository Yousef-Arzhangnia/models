"""M0 demo page: start a dummy run and watch it on the board."""
import time

import streamlit as st

from common import checks_table, history, links, run_section, setup, tracker, tracker_checks_rows

setup("Demo (M0)")
st.title("Demo page (M0): tracker and live board")
st.markdown("#### What it models\nNothing physical. A 30-step dummy study that sleeps one second per step, records one "
            "check, one result, a figure and a CSV. It proves that a run started from the command line reaches the "
            "board live.")
st.markdown("#### Inputs\nNone (steps and step time are CLI options: `python -m u4 run demo --steps 30 --dt 1`).")
st.markdown("#### Run")
run_section("demo", "30 s dummy run")


@st.fragment(run_every=2)
def progress():
    act = [r for r in tracker.active_runs() if r["model"] == "0"]
    for r in act:
        st.progress(r["progress"] or 0.0, text=f"{r['id']}: {r['message']}")
    if not act:
        st.caption(f"No demo run active ({time.strftime('%H:%M:%S')}).")


progress()
st.markdown("#### Verification")
checks_table(tracker_checks_rows("0"))
st.markdown("#### History")
history("0", "demo", "x", "y", "amplitude (a.u.)", "x")
links(["src/u4/studies/demo.py", "src/u4/tracker.py"], "reports/M0_report.md")
