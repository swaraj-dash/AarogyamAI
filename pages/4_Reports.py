import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from services import report_service

st.set_page_config(page_title="Reports · AarogyamAI", page_icon="📄")

if "user_id" not in st.session_state:
    st.warning("Please log in from the main page first.")
    st.stop()

user_id = st.session_state["user_id"]
st.title("Generate a report")

col1, col2 = st.columns(2)
with col1:
    start = st.date_input("Start date", value=date.today() - timedelta(days=7))
with col2:
    end = st.date_input("End date", value=date.today())

if st.button("Generate PDF", type="primary"):
    if start > end:
        st.error("Start date must be before end date.")
    else:
        with st.spinner("Analyzing logs, retrieving long-term patterns, writing narrative..."):
            try:
                result = report_service.generate_report(user_id, start.isoformat(), end.isoformat())
            except Exception as e:
                st.error(f"Couldn't generate report: {e}")
                result = None

        if result:
            st.success("Report generated!")
            st.write(result["narrative"])
            with open(result["filepath"], "rb") as f:
                st.download_button(
                    "Download PDF", data=f.read(),
                    file_name="AarogyamAI_Report.pdf", mime="application/pdf",
                )
