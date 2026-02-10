import streamlit as st
import requests

SUPABASE_URL = "https://qpefflvoxwtbqssimbev.supabase.co"
SUPABASE_KEY = "sb_publishable_sqyi_4r3w3JiIR8wTyLG9g_0_oMexT7"
TABLE = "maintable"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

st.title("⚙️ Monitoring Getaran Mesin")

url = f"{SUPABASE_URL}/rest/v1/{TABLE}?select=*&order=created_at.desc&limit=1"
res = requests.get(url, headers=HEADERS)

if res.status_code != 200:
    st.error("Gagal ambil data")
    st.stop()

data = res.json()

if len(data) == 0:
    st.warning("Belum ada data")
    st.stop()

d = data[0]

st.metric("RPM", d["rpm"])
st.metric("Getaran", d["vibration"])
st.metric("Status", d["status"])
