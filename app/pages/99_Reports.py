from pathlib import Path

import streamlit as st

from common import ROOT, setup

setup("Reports")
st.title("Milestone reports")
reps = sorted((ROOT / "reports").glob("M*_report.md"))
if not reps:
    st.info("No reports yet.")
else:
    choice = st.selectbox("Report", reps, index=len(reps) - 1, format_func=lambda p: p.name)
    text = Path(choice).read_text(encoding="utf-8")
    base = Path(choice).parent
    for block in text.split("\n"):
        pass
    # render markdown, images inline
    import re
    parts = re.split(r"(!\[[^\]]*\]\([^)]+\))", text)
    for part in parts:
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", part)
        if m:
            p = (base / m.group(2)).resolve()
            if p.exists():
                st.image(str(p), caption=m.group(1), use_container_width=True)
        elif part.strip():
            st.markdown(part)
