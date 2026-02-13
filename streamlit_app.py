import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# ======================
# KONFIGURASI HALAMAN
# ======================
st.set_page_config(
    page_title="Monitoring Getaran Mesin",
    page_icon="⚙️",
    layout="wide"
)

# ======================
# KONFIGURASI SUPABASE
# ======================
SUPABASE_URL = "https://qpefflvoxwtbqssimbev.supabase.co"
SUPABASE_KEY = "sb_publishable_sqyi_4r3w3JiIR8wTyLG9g_0_oMexT7"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ======================
# HEADER
# ======================
st.markdown("""
<div style='background-color:#0b3d91;padding:25px;border-radius:12px'>
<h1 style='color:chocolate;text-align:center;margin:0;'>
⚙️ Monitoring Getaran & RPM Mesin Industri ⚙️
</h1>
<p style='color:chocolate;text-align:center;margin:0;'>
Sistem Monitoring Real-Time Berbasis PLC, ESP32 & IoT
</p>
</div>
""", unsafe_allow_html=True)

st.write("")

# ======================
# AMBIL DATA
# ======================
@st.cache_data(ttl=5)
def load_data():
    response = supabase.table("maintable") \
        .select("*") \
        .order("time", desc=True) \
        .limit(100) \
        .execute()

    return pd.DataFrame(response.data)

df = load_data()

if df.empty:
    st.warning("Belum ada data dari mesin")
    st.stop()

latest = df.iloc[0]

rpm = latest["rpm"]
vibration = latest["vibration"]
status = latest["status"]

# ======================
# WARNA STATUS DINAMIS
# ======================
if status.lower() == "normal":
    color = "#2ecc71"
elif status.lower() in ["unsatisfactory", "warning"]:
    color = "#f1c40f"
else:
    color = "#e74c3c"

# ======================
# KPI CARDS
# ======================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div style='
        background:chocolate;
        padding:25px;
        border-radius:15px;
        box-shadow:0 4px 12px rgba(0,0,0,0.1);
        text-align:center'>
        <h3 style='color:black'>RPM Mesin</h3>
        <h1 style='color:black'>{rpm}</h1>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style='
        background:chocolate;
        padding:25px;
        border-radius:15px;
        box-shadow:0 4px 12px rgba(0,0,0,0.1);
        text-align:center'>
        <h3 style='color:black'>Getaran (mm/s)</h3>
        <h1 style='color:black'>{vibration}</h1>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style='
        background:{color};
        padding:25px;
        border-radius:15px;
        box-shadow:0 4px 12px rgba(0,0,0,0.1);
        text-align:center'>
        <h3 style='color:black'>Status Mesin</h3>
        <h1 style='color:black'>{status.upper()}</h1>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.divider()

# ======================
# GRAFIK
# ======================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 Grafik RPM")
    fig_rpm = px.line(
        df.sort_values("time"),
        x="time",
        y="rpm",
        markers=True,
        line_shape="spline"
    )
    fig_rpm.update_layout(
        template="plotly_white",
        height=400,
        xaxis_title="Waktu",
        yaxis_title="RPM"
    )
    st.plotly_chart(fig_rpm, use_container_width=True)

with col_right:
    st.subheader("📉 Grafik Getaran")
    fig_vib = px.line(
        df.sort_values("time"),
        x="time",
        y="vibration",
        markers=True,
        line_shape="spline"
    )
    fig_vib.update_layout(
        template="plotly_white",
        height=400,
        xaxis_title="Waktu",
        yaxis_title="mm/s"
    )
    st.plotly_chart(fig_vib, use_container_width=True)

st.divider()

# ======================
# TABEL DATA
# ======================
st.subheader("📋 Data Monitoring Terakhir")
st.dataframe(
    df.sort_values("time", ascending=False),
    use_container_width=True,
    height=350
)

st.caption("Auto refresh setiap 5 detik")
