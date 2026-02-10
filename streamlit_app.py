import streamlit as st
import pandas as pd
import time

# -----------------------------
# KONFIGURASI HALAMAN
# -----------------------------
st.set_page_config(
    page_title="Monitoring Getaran Mesin",
    page_icon="⚙️",
    layout="wide"
)

# -----------------------------
# CSS TAMBAHAN (BIAR CAKEP)
# -----------------------------
st.markdown("""
<style>
.metric-card {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0 4px 10px rgba(0,0,0,0.4);
}
.metric-title {
    font-size: 18px;
    color: #aaaaaa;
}
.metric-value {
    font-size: 36px;
    font-weight: bold;
    color: white;
}
.status-normal {
    background-color: #1f7a1f;
    padding: 15px;
    border-radius: 10px;
    color: white;
    text-align: center;
    font-size: 20px;
}
.status-warning {
    background-color: #b36b00;
    padding: 15px;
    border-radius: 10px;
    color: white;
    text-align: center;
    font-size: 20px;
}
.status-danger {
    background-color: #a61d24;
    padding: 15px;
    border-radius: 10px;
    color: white;
    text-align: center;
    font-size: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# HEADER
# -----------------------------
st.markdown("## ⚙️ Monitoring Mesin Berputar")
st.caption("Early Warning System Berbasis PLC, ESP32, dan IoT")

st.divider()

# -----------------------------
# DATA CONTOH (NANTI GANTI DARI SUPABASE)
# -----------------------------
rpm = 1450
getaran = 9.2   # mm/s

# -----------------------------
# STATUS MESIN
# -----------------------------
if getaran < 4.5:
    status = "NORMAL"
    status_class = "status-normal"
elif getaran < 7.0:
    status = "UNSATISFACTORY"
    status_class = "status-warning"
else:
    status = "DANGER"
    status_class = "status-danger"

# -----------------------------
# METRIC UTAMA
# -----------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">RPM Mesin</div>
        <div class="metric-value">{rpm}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Getaran (mm/s)</div>
        <div class="metric-value">{getaran}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="{status_class}">
        STATUS MESIN<br><b>{status}</b>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# -----------------------------
# GRAFIK GETARAN
# -----------------------------
st.subheader("📊 Grafik Monitoring")

df = pd.DataFrame({
    "RPM": [rpm],
    "Getaran (mm/s)": [getaran]
})

st.bar_chart(df, height=300)

# -----------------------------
# FOOTER
# -----------------------------
st.caption("© 2026 | Sistem Monitoring Mesin Industri")
