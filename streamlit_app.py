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
body {
    background-color: #f4f6f9;
}

.metric-card {
    padding: 25px;
    border-radius: 15px;
    text-align: center;
    color: white;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
}

.rpm {background: linear-gradient(135deg,#3498db,#5dade2);}
.vibration {background: linear-gradient(135deg,#f39c12,#f8c471);}
.normal {background: linear-gradient(135deg,#27ae60,#52be80);}
.warning {background: linear-gradient(135deg,#f1c40f,#f7dc6f);}
.danger {background: linear-gradient(135deg,#e74c3c,#ec7063);}

.metric-value {
    font-size: 42px;
    font-weight: bold;
}

.metric-label {
    font-size: 18px;
    opacity: 0.95;
    color: rgba(255,255,255,0.95);
}

h2, h3, h4 {
    color: #2c3e50;
}
</style>
""", unsafe_allow_html=True)

# ======================
# JUDUL
# ======================
st.markdown("## ⚙️ **Monitoring Getaran & RPM Mesin Industri**")
st.caption("Selamat Datang Di Website Pemantauan")

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
