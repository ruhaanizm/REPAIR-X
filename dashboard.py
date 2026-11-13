
"""REPAIR-X dashboard for the automatic repair pipeline."""

import json
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="REPAIR-X Dashboard",
    page_icon="🛠️",
    layout="wide",
)

REPORT_PATH = Path(__file__).resolve().parent / "auto_repair_report.json"

st.title("REPAIR-X")
st.subheader("AI-Assisted Software Fault Diagnosis and Repair")
st.caption(
    "Controlled prototype | AI patch generation | "
    "Isolated validation | Deterministic fallback"
)

if not REPORT_PATH.exists():
    st.warning(
        "No automatic repair report found. "
        "Run: python auto_repair.py --auto"
    )
    st.stop()

try:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    st.error(f"Unable to load report: {exc}")
    st.stop()

results = report.get("results", [])

provider = report.get("provider", "Unknown")
model = report.get("model", "Unknown")

st.markdown(f"**Provider:** {provider} | **Model:** `{model}`")

total = len(results)
successful = sum(bool(r.get("repair_success")) for r in results)
ai_repairs = sum(
    bool(r.get("repair_success")) and r.get("patch_source") == "ai"
    for r in results
)
fallback_repairs = sum(
    bool(r.get("repair_success")) and r.get("patch_source") == "fallback"
    for r in results
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Incidents", total)
c2.metric("Validated Repairs", successful)
c3.metric("AI Repairs", ai_repairs)
c4.metric("Fallback Repairs", fallback_repairs)

st.metric(
    "Pipeline Execution Time",
    f"{report.get('elapsed_seconds', 0):.2f} seconds",
)

st.divider()
st.subheader("Incident Overview")

overview = []

for result in results:
    overview.append({
        "Scenario": result.get("scenario", "Unknown"),
        "Exception": result.get("exception_type", "Unknown"),
        "Fault Category": result.get("fault_category", "Unknown"),
        "Patch Source": result.get("patch_source", "Unknown"),
        "Validated": bool(result.get("repair_success")),
    })

if overview:
    st.dataframe(overview, use_container_width=True, hide_index=True)
else:
    st.info("No incidents in the report.")

st.divider()
st.subheader("Repair Details")

for index, result in enumerate(results, start=1):
    scenario = result.get("scenario", "Unknown")
    success = bool(result.get("repair_success"))

    with st.expander(
        f"Incident {index}: {scenario} — "
        f"{'VALIDATED' if success else 'FAILED'}",
        expanded=True,
    ):
        left, right = st.columns(2)

        with left:
            st.write("**Exception:**", result.get("exception_type"))
            st.write("**Classification:**", result.get("fault_category"))
            st.write("**Patch Source:**", result.get("patch_source"))

            reason = result.get("fallback_reason")
            if reason:
                st.warning(f"Fallback reason: {reason}")

        with right:
            if success:
                st.success("Candidate passed isolated validation.")
            else:
                st.error("Candidate did not pass validation.")

        st.write("**Candidate Patch**")
        st.code(result.get("patch") or "# No patch available", language="python")

st.divider()
st.info(
    "REPAIR-X currently validates candidate patches in temporary files. "
    "Successful validation does not mean the patch has been deployed "
    "to the original application."
)

if st.button("Refresh Report"):
    st.rerun()
