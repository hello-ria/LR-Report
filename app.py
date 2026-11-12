"""Streamlit dashboard. Run with:  streamlit run app.py"""
from datetime import date

import pandas as pd
import streamlit as st

from analyze import analyze, load_tasks
from report import generate_report

st.set_page_config(page_title="Status Assistant", layout="wide")
st.title("Weekly status and risk assistant")

with st.sidebar:
    uploaded = st.file_uploader("Task export (CSV)", type="csv")
    as_of = st.date_input("Report date", value=date(2026, 10, 26))
    use_ai = st.toggle("Use AI for the write-up", value=True,
                       help="Needs ANTHROPIC_API_KEY. Falls back to a template without it.")

try:
    df = load_tasks(uploaded if uploaded else "sample_tasks.csv")
except ValueError as err:
    st.error(str(err))
    st.stop()

f = analyze(df, as_of)

colour = {"Red": "red", "Amber": "orange", "Green": "green"}[f["health"]]
st.markdown(f"### Health: :{colour}[{f['health']}]  \n" + "; ".join(f["health_reasons"]))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tasks done", f"{f['done']} / {f['total_tasks']}")
c2.metric("Avg completion", f"{f['percent_complete']}%")
c3.metric("Overdue", len(f["overdue"]))
c4.metric("Blocked", len(f["blocked"]))

left, right = st.columns(2)
with left:
    st.subheader("Status mix")
    st.bar_chart(pd.Series(f["status_counts"]))
with right:
    st.subheader("Overdue and blocked by owner")
    st.bar_chart(pd.DataFrame(f["owner_load"]).set_index("owner")[["overdue", "blocked"]])

st.subheader("Overdue tasks")
st.dataframe(pd.DataFrame(f["overdue"]), use_container_width=True, hide_index=True)

st.subheader("Draft report")
if st.button("Generate report", type="primary"):
    with st.spinner("Writing report..."):
        text, source = generate_report(f, use_ai=use_ai)
    st.caption(f"Source: {source}")
    st.markdown(text)
    st.download_button("Download as Markdown", text, file_name=f"status_{f['as_of']}.md")
