import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ======================
# AUTO REFRESH 0,5 DETIK
# ======================
st_autorefresh(interval=1000, key="refresh")

# ======================
# PAGE CONFIG
# ======================
st.set_page_config(layout="wide")

# ======================
# DARK INDUSTRIAL STYLE
# ======================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-color: #0f172a;
    color: white;
}
h1,h2,h3,h4,p {
    color:white;
}
</style>
""", unsafe_allow_html=True)

# ======================
# SUPABASE
# ======================
SUPABASE_URL = "https://qpefflvoxwtbqssimbev.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFwZWZmbHZveHd0YnFzc2ltYmV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA2MzIzODUsImV4cCI6MjA4NjIwODM4NX0.tG6y6MoAvdgIOPHAYTpDJ-GO8pLIRrEn5vmsSo1PZFo"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# LOAD DATA
# ======================
@st.cache_data(ttl=20)
def load_data():
    res = supabase.table("monitoring")\
        .select("*")\
        .order("TIME", desc=True)\
        .limit(100)\
        .execute()
    return pd.DataFrame(res.data)

df = load_data()

if df.empty:
    st.warning("Belum ada data")
    st.stop()

# ======================
# FORMAT DATA
# ======================
df["TIME"] = pd.to_datetime(df["TIME"])
df["RPM"] = df["RPM"].astype(int)
df["Vrms"] = df["Vrms"].astype(float).round(2)

latest = df.iloc[0]

rpm = latest["RPM"]
vibration = latest["Vrms"]
status = latest["STATUS"]

# ======================
# HEADER
# ======================
st.markdown("""
<h1 style='text-align:center'>⚙️ INDUSTRIAL MACHINE MONITORING ⚙️</h1>
<p style='text-align:center'>PLC • ESP32 • IoT • REALTIME SYSTEM</p>
""", unsafe_allow_html=True)

# ======================
# ALARM PANEL
# ======================
if status.lower() == "danger":
    st.markdown("""
    <div style='background:red;padding:20px;border-radius:10px;text-align:center;
    animation: blink 1s infinite'>
    <h1>🚨 DANGER - GETARAN TINGGI 🚨</h1>
    </div>
    <style>
    @keyframes blink {50% {opacity:0.4;}}
    </style>
    """, unsafe_allow_html=True)

elif status.lower() == "warning":
    st.markdown("""
    <div style='background:orange;padding:20px;border-radius:10px;text-align:center'>
    <h1>⚠ WARNING - PERLU PENGECEKAN</h1>
    </div>
    """, unsafe_allow_html=True)

# ======================
# KPI + GAUGE
# ======================
col1, col2 = st.columns(2)

with col1:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rpm,
        title={'text': "RPM Mesin"},
        gauge={
            'axis': {'range': [0, 2000]},
            'steps': [
                {'range': [0, 1200], 'color': "green"},
                {'range': [1200, 1500], 'color': "yellow"},
                {'range': [1500, 2000], 'color': "red"}
            ]
        }
    ))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col2:
    st.markdown(f"""
    <div style='background:#1e293b;padding:30px;border-radius:10px;text-align:center'>
        <h2>Getaran (Vrms)</h2>
        <h1>{vibration} mm/s</h1>
        <h2>Status: {status}</h2>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ======================
# GRAFIK
# ======================
colg1, colg2 = st.columns(2)

df_plot = df.sort_values("TIME").tail(50)

with colg1:
    fig_rpm = px.line(df_plot, x="TIME", y="RPM")
    fig_rpm.update_layout(title="Grafik RPM")
    st.plotly_chart(fig_rpm, use_container_width=True)

with colg2:
    fig_vib = px.line(df_plot, x="TIME", y="Vrms")
    fig_vib.add_hline(y=4, line_dash="dash", line_color="yellow")
    fig_vib.add_hline(y=7, line_dash="dash", line_color="red")
    fig_vib.update_layout(title="Grafik Getaran")
    st.plotly_chart(fig_vib, use_container_width=True)

st.divider()

# ======================
# TABEL
# ======================
st.dataframe(df.sort_values("TIME", ascending=False), use_container_width=True)
