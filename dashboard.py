"""Minimal dashboard for the REPAIR-X run history."""
import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="REPAIR-X", page_icon="🛠️", layout="wide")
st.title("REPAIR-X | AI-Driven Self-Healing Software")
st.caption("Controlled prototype • AI proposes, tests decide, rollback protects")

history_file = Path(__file__).with_name("repair_history.json")
if not history_file.exists():
    st.info("No run history yet. Run `python repair_x.py` first.")
    st.stop()

events = json.loads(history_file.read_text(encoding="utf-8"))
c1, c2, c3 = st.columns(3)
validations = [e for e in events if e.get("stage") == "validation"]
recoveries = [e for e in events if e.get("stage") == "recovery"]
c1.metric("Repair attempts", len(validations))
c2.metric("Validated patches", sum(bool(e.get("tests_passed")) for e in validations))
c3.metric("Final status", recoveries[-1].get("status", "UNKNOWN") if recoveries else "RUNNING")

st.subheader("Incident / repair timeline")
st.dataframe(events, width="stretch")
for e in validations:
    with st.expander(f"Attempt {e.get('attempt')} — {'PASS' if e.get('tests_passed') else 'FAIL'}"):
        st.code(e.get("patch_body", "(no patch returned)"), language="python")
        st.text(e.get("output", ""))
