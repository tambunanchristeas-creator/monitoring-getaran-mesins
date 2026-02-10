import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# ======================
# KONFIGURASI SUPABASE
# ======================
SUPABASE_URL = "https://qpefflvoxwtbqssimbev.supabase.co"
SUPABASE_KEY = "sb_publishable_sqyi_4r3w3JiIR8wTyLG9g_0_oMexT7"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Monitoring Getaran Mesin",
    layout="wide"
)

st.title("📊 Monitoring Getaran & RPM Mesin")

# ======================
# AMBIL DATA
# ======================
@st.cache_data(ttl=5)  # auto refresh tiap 5 detik
def load_data():
    response = supabase.table("maintable") \
        .select("*") \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute()

    return pd.DataFrame(response.data)

df = load_data()

# ======================
# TAMPILAN DATA TERAKHIR
# ======================
if df.empty:
    st.warning("Belum ada data dari mesin")
    st.stop()

latest = df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("RPM", f"{latest['rpm']}")
col2.metric("Getaran (mm/s)", f"{latest['getaran']}")
col3.metric("Level", latest["level"])

# ======================
# GRAFIK
# ======================
st.subheader("Grafik RPM")
fig_rpm = px.line(df, x="created_at", y="rpm", markers=True)
st.plotly_chart(fig_rpm, use_container_width=True)

st.subheader("Grafik Getaran")
fig_getaran = px.line(df, x="created_at", y="getaran", markers=True)
st.plotly_chart(fig_getaran, use_container_width=True)

# ======================
# TABEL
# ======================
st.subheader("Data Terakhir")
st.dataframe(df)
