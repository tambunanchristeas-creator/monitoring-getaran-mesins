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
# STYLE CSS (LIGHT MODE)
# ======================
st.markdown("""
<style>

/* Background utama */
[data-testid="stAppViewContainer"] {
    background-color: #ffffff;
}

/* Semua teks jadi hitam */
html, body, [class*="css"] {
    color: #000000 !important;
}

/* Header biru tua */
.main-header {
    background-color: #0b3d91;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    color: white;
    font-size: 32px;
    font-weight: bold;
}

/* Sub caption */
.subtitle {
    text-align: center;
    color: #333333;
    margin-bottom: 25px;
}

/* Card style */
.metric-card {
    padding: 25px;
    border-radius: 15px;
    text-align: center;
    color: black;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    background-color: #f8f9fa;
}

/* Status colors */
.normal {
    border-left: 8px solid #2ecc71;
}
.warning {
    border-left: 8px solid #f39c12;
}
.danger {
    border-left: 8px solid #e74c3c;
}

.metric-value {
    font-size: 42px;
    font-weight: bold;
}

.metric-label {
    font-size: 18px;
}

</style>
""", unsafe_allow_html=True)

# ======================
# JUDUL
# ======================
st.markdown("""
<div class="main-header">
⚙️ Monitoring Getaran & RPM Mesin Industri
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="subtitle">
Sistem Monitoring Real-Time Berbasis IoT
</div>
""", unsafe_allow_html=True)

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
    st.warning("⚠️ Belum ada data dari mesin")
    st.stop()

latest = df.iloc[0]

rpm = latest["rpm"]
vibration = latest["vibration"]
status = latest["status"]

# ======================
# WARNA STATUS
# ======================
if status.lower() == "normal":
    status_class = "normal"
elif status.lower() == "warning":
    status_class = "warning"
else:
    status_class = "danger"

# ======================
# KPI CARDS
# ======================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card rpm">
        <div class="metric-label">RPM Mesin</div>
        <div class="metric-value">{rpm}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card vibration">
        <div class="metric-label">Getaran (mm/s)</div>
        <div class="metric-value">{vibration}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card {status_class}">
        <div class="metric-label">Status Mesin</div>
        <div class="metric-value">{status.upper()}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ======================
# GRAFIK
# ======================
left, right = st.columns(2)

with left:
    st.subheader("📈 Grafik RPM")
    fig_rpm = px.line(
        df.sort_values("time"),
        x="time",
        y="rpm",
        markers=True
    )
    fig_rpm.update_layout(
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig_rpm, use_container_width=True)

with right:
    st.subheader("📉 Grafik Getaran")
    fig_vib = px.line(
        df.sort_values("time"),
        x="time",
        y="vibration",
        markers=True
    )
    fig_vib.update_layout(
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig_vib, use_container_width=True)

# ======================
# TABEL DATA
# ======================
st.subheader("📋 Data Terakhir")
st.dataframe(
    df,
    use_container_width=True,
    height=300
)

st.caption("🕒 Auto refresh setiap 5 detik")
