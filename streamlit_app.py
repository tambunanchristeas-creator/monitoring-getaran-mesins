import streamlit as st
import pandas as pd

st.set_page_config(page_title="Monitoring Mesin", layout="centered")

st.title("⚙️ Monitoring Mesin Berputar")
st.caption("Early Warning System Berbasis PLC & ESP32")

# -----------------------------
# DATA CONTOH
# -----------------------------
rpm = 1450
getaran = 0.0  # mm/s

# -----------------------------
# STATUS MESIN
# -----------------------------
if getaran < 4.5:
    st.success("STATUS: NORMAL")
elif getaran < 7.1:
    st.warning("STATUS: UNSATISFACTORY")
else:
    st.error("STATUS: DANGER")

# -----------------------------
# METRIC
# -----------------------------
col1, col2 = st.columns(2)
col1.metric("RPM Mesin", rpm)
col2.metric("Getaran Mesin (mm/s)", getaran)

# -----------------------------
# GRAFIK SEDERHANA (TANPA PLOTLY)
# -----------------------------
df = pd.DataFrame({
    "RPM": [rpm],
    "Getaran (mm/s)": [getaran]
})

st.subheader("Grafik Monitoring")
st.bar_chart(df)
st.title("TES COMMIT BERHASIL")
