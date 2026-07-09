import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
import streamlit as st

from services import analytics_service
from services.memory_service import EpisodicMemory

st.set_page_config(page_title="Analytics · AarogyamAI", page_icon="📊", layout="wide")

if "user_id" not in st.session_state:
    st.warning("Please log in from the main page first.")
    st.stop()

user_id = st.session_state["user_id"]
st.title("Analytics")

days = st.slider("Window (days)", min_value=7, max_value=60, value=14)
logs = EpisodicMemory.get_recent_logs(user_id, days)

if not logs:
    st.info("No logs in this window yet — use the Log Day page to add some.")
    st.stop()

summary = analytics_service.compute_summary(logs)
patterns = analytics_service.detect_notable_patterns(logs)

col1, col2, col3 = st.columns(3)
col1.metric("Days logged", summary["n_days_logged"])
col2.metric("Wellness score", summary["wellness_score"] or "—")
col3.metric("Avg mood (1-5)", summary.get("avg_mood_score") or "—")

if patterns:
    st.subheader("Statistically notable trends")
    st.caption(
        "Only trends with R² ≥ 0.3 are shown here — a real fit to the data, "
        "not a two-point diff that could just be noise."
    )
    for p in patterns:
        st.markdown(f"- {p}")
else:
    st.info("No trend in this window is strong enough to call notable yet (R² < 0.3 for all metrics).")

st.divider()
st.subheader("Trend charts")

for field in analytics_service.TRACKED_NUMERIC_FIELDS:
    dates = [l["log_date"] for l in logs if l.get(field) is not None]
    values = [l[field] for l in logs if l.get(field) is not None]
    if len(dates) < 2:
        continue
    trend = summary["trends"][field]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=values, mode="lines+markers", name=field))
    fig.update_layout(
        title=f"{field.replace('_', ' ').title()} — {trend['direction'].replace('_', ' ')} "
              f"(R²={trend['r_squared']})",
        height=300, margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
