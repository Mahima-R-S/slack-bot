import streamlit as st, pandas as pd, plotly.express as px
from db import conn, SERVICES
import agent

st.set_page_config(page_title="PlatformPulse", layout="wide")
st.title("PlatformPulse")

c = conn()
inc = pd.read_sql("SELECT * FROM incidents", c, parse_dates=["created_at", "resolved_at"])
met = pd.read_sql("SELECT * FROM metrics", c, parse_dates=["ts"])

days = st.sidebar.slider("Days", 1, 14, 7)
sel = st.sidebar.multiselect("Services", SERVICES, default=SERVICES)
cutoff = met.ts.max() - pd.Timedelta(days=days)
m = met[(met.ts >= cutoff) & met.service.isin(sel)]
i = inc[(inc.created_at >= cutoff) & inc.service.isin(sel)].copy()
i["ttr_min"] = (i.resolved_at - i.created_at).dt.total_seconds() / 60

mttr = i.ttr_min.mean()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Incidents", len(i))
k2.metric("Open now", int((i.status == "open").sum()))
k3.metric("MTTR (min)", f"{mttr:.0f}" if pd.notna(mttr) else "-")
k4.metric("Avg success rate", f"{m.success_rate.mean() * 100:.2f}%")

left, right = st.columns(2)
lat = m.groupby(["ts", "service"]).p95_latency_ms.mean().reset_index()
left.plotly_chart(px.line(lat, x="ts", y="p95_latency_ms", color="service", title="p95 latency (ms)"),
                  width="stretch")
by = i.groupby(["service", "severity"]).size().reset_index(name="count")
right.plotly_chart(px.bar(by, x="service", y="count", color="severity", title="Incidents by service and severity"),
                   width="stretch")

st.subheader("Incidents")
st.dataframe(i.sort_values("created_at", ascending=False), width="stretch")

st.subheader("Ask PlatformPulse")
q = st.text_input("e.g. Is Airflow healthy?")
if q:
    with st.spinner("Thinking..."):
        st.write(agent.ask(q))