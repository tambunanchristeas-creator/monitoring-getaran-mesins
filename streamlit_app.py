import streamlit as st
import pandas as pd
import time
import random

# -----------------------------
# SETTING HALAMAN
# -----------------------------
st.set_page_config(
    page_title="Monitoring Getaran Mesin",
    page_icon="⚙️",
    layout="wide"
)

# -----------------------------
# AUTO REFRESH
# -----------------------------
REFRESH_INTERVAL = 3  # detik
time.sleep(REFRESH_INTERVAL)
st.rerun()

# -----------------------------
# HEADER
# -----------------------------
st.title("⚙️ Monitoring Mesin Berputar")
st.caption("Real-Time Early Warning System")

st.divider()

# -----------------------------
# SIMULASI DATA REAL-TIME
# (NANTI DIGANTI SUPABASE)
# -----------------------------
rpm = random.randint(1200, 1600)
getaran = round(random.uniform(2.0, 9.5), 2)

# -----------------------------
# LOGIKA STATUS
# -----------------------------
if getaran < 4.5:
    status = "NORMAL"
    warna = "🟢"
elif getaran < 7.0:
    status = "UNSATISFACTORY"
    warna = "🟡"
else:
    status = "DANGER"
    warna = "🔴"

# -----------------------------
# METRIC
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("RPM Mesin", rpm)
col2.metric("Getaran (mm/s)", getaran)
col3.metric("Status", f"{warna} {status}")

st.divider()

# -----------------------------
# GRAFIK
# -----------------------------
df = pd.DataFrame({
    "Parameter": ["RPM", "Getaran"],
    "Nilai": [rpm, getaran]
})

st.bar_chart(df)

# -----------------------------
# INFO UPDATE
# -----------------------------
st.caption(f"⏱ Auto refresh setiap {REFRESH_INTERVAL} detik")
