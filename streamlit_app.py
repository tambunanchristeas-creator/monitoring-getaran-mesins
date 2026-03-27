import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ======================
# AUTO REFRESH 0,2 DETIK
# ======================
st_autorefresh(interval=200, key="refresh")

# ======================
# KONFIGURASI HALAMAN
# ======================
st.set_page_config(
    page_title="Monitoring Getaran Mesin",
    page_icon="⚙️",
    layout="wide"
)

# ======================
# BACKGROUND PUTIH GLOBAL
# ======================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-color: white;
}
</style>
""", unsafe_allow_html=True)

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
<div style='background-color:#0b3d91;padding:25px;border-radius:1 px'>
<h1 style='color:white;text-align:center;margin:0;'>
⚙️ Monitoring Getaran & RPM Mesin Industri ⚙️
</h1>
<p style='color:white;text-align:center;margin:0;'>
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
    response = supabase.table("monitoring") \
        .select("*") \
        .order("TIME", desc=True) \
        .limit(100) \
        .execute()

    return pd.DataFrame(response.data)

df = load_data()
# ======================
# FORMAT DATA BIAR RAPI
# ======================

# KHUSUS GRAFIK (HARUS DATETIME)
df["TIME"] = pd.to_datetime(df["TIME"])

# BUAT COPY UNTUK TABEL
df_table = df.copy()

# FORMAT HANYA UNTUK TABEL
df_table["TIME"] = df_table["TIME"].dt.strftime("%d-%m-%Y %H:%M:%S")

df_plot = df.sort_values("TIME").tail(30)

# Pembulatan angka
df["RPM"] = df["RPM"].astype(int)
df["Vrms(mm/s)"] = df["Vrms(mm/s)"].astype(float).round(2)

# Rename kolom biar lebih clean
df = df.rename(columns={
    "id": "No",
    "RPM": "RPM",
    "Vrms(mm/s)": "Vrms(mm/s)",
    "STATUS": "STATUS",
    "TIME": "TIME"
})

if df.empty:
    st.warning("Belum ada data dari mesin")
    st.stop()

latest = df.iloc[0]

rpm = latest["RPM"]
vibration = latest["Vrms(mm/s)"]
status = latest["STATUS"]

# ======================
# STATUS COLOR
# ======================
if status.lower() == "normal":
    status_color = "#2ecc71"
elif status.lower() in ["unsatisfactory", "warning"]:
    status_color = "#f1c40f"
else:
    status_color = "#e74c3c"

# ======================
# KPI CARDS
# ======================
col1, col2, col3 = st.columns(3)

card_style = """
background:#5a2d0c;
padding:25px;
border-radius:15px;
box-shadow:0 4px 12px rgba(0,0,0,0.2);
text-align:center;
"""

with col1:
    st.markdown(f"""
    <div style='{card_style}'>
        <h3 style='color:white'>Kecepatan Putar Mesin (RPM)</h3>
        <h1 style='color:white'>{rpm}</h1>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style='{card_style}'>
        <h3 style='color:white'>Kecepatan Getaran Vrms (mm/s)</h3>
        <h1 style='color:white'>{vibration}</h1>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style='
        background:{status_color};
        padding:25px;
        border-radius:15px;
        box-shadow:0 4px 12px rgba(0,0,0,0.2);
        text-align:center'>
        <h3 style='color:white'>Status Mesin</h3>
        <h1 style='color:white'>{status.upper()}</h1>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.divider()

# ======================
# JUDUL GRAFIK BIRU
# ======================
# Grafik RPM
col_g1, col_g2 = st.columns(2)

# Grafik RPM
with col_g1:
    st.markdown("""
    <div style='
            background:#0b3d91;
            padding:10px;
            border-radius:8px;
            text-align:center'>
    <h3 style='color:white;margin:0'>📈 Grafik RPM</h3>
    </div>
    """, unsafe_allow_html=True)

    fig_rpm = px.line(
        df.sort_values("TIME"),
        x="TIME",
        y="RPM",
    )

    fig_rpm.update_traces(line_color="blue")
    st.plotly_chart(fig_rpm, use_container_width=True)

# Grafik Getaran
with col_g2:
    st.markdown("""
    <div style='
            background:#0b3d91;
            padding:10px;
            border-radius:8px;
            text-align:center'>
    <h3 style='color:white;margin:0'>📉 Grafik Getaran</h3>
    </div>
    """, unsafe_allow_html=True)

    fig_vib = px.line(
        df.sort_values("TIME"),
        x="TIME",
        y="Vrms(mm/s)",
    )

    fig_vib.update_traces(line_color="blue")
    st.plotly_chart(fig_vib, use_container_width=True)

# ======================
# DATA MONITORING HEADER
# ======================
st.markdown("""
<div style='background:#5a2d0c;padding:10px;border-radius:8px'>
<h3 style='color:white;margin:0'>📋 Data Monitoring Terakhir</h3>
</div>
""", unsafe_allow_html=True)

# ======================
# STYLE TABEL PUTIH
# ======================
st.markdown("""
<style>
thead tr th {
    background-color: #5a2d0c !important;
    color: white !important;
}
tbody tr td {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.dataframe(
    df.sort_values("TIME", ascending=False),
    use_container_width=True,
    height=400,
    hide_index=True
)

st.caption("Auto refresh setiap 5 detik")
