import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Industrial Machine Monitoring",
    layout="wide"
)


# =========================================================
# AUTO REFRESH
# =========================================================
st_autorefresh(
    interval=1000,
    key="refresh"
)


# =========================================================
# DARK INDUSTRIAL STYLE
# =========================================================
st.markdown("""
<style>

[data-testid="stAppViewContainer"] {
    background-color: #0f172a;
    color: white;
}

h1, h2, h3, h4, p {
    color: white;
}

/* Tombol STOP */
button[kind="secondary"] {
    background-color: red !important;
    color: white !important;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SUPABASE
# =========================================================
SUPABASE_URL = "https://qpefflvoxwtbqssimbev.supabase.co"

SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFwZWZmbHZveHd0YnFzc2ltYmV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA2MzIzODUsImV4cCI6MjA4NjIwODM4NX0.tG6y6MoAvdgIOPHAYTpDJ-GO8pLIRrEn5vmsSo1PZFo"

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# SESSION STATE
# =========================================================
if "last_click" not in st.session_state:
    st.session_state.last_click = 0


# =========================================================
# LOAD DATA MONITORING
# =========================================================
def load_data():

    try:

        res = (
            supabase
            .table("monitoring")
            .select("id,TIME,RPM,Vrms,STATUS")
            .order("id", desc=True)
            .limit(100)
            .execute()
        )

        return pd.DataFrame(res.data)

    except Exception as e:

        st.error("Gagal mengambil data monitoring dari Supabase.")

        st.code(str(e))

        return pd.DataFrame()


# =========================================================
# AMBIL DATA
# =========================================================
df = load_data()


# =========================================================
# CEK DATA
# =========================================================
if df.empty:

    st.warning("Belum ada data monitoring.")

    st.stop()


# =========================================================
# FORMAT DATA
# =========================================================

# TIME
df["TIME"] = pd.to_datetime(
    df["TIME"],
    errors="coerce"
)


# RPM
df["RPM"] = pd.to_numeric(
    df["RPM"],
    errors="coerce"
).fillna(0)


# VRMS
df["Vrms"] = pd.to_numeric(
    df["Vrms"],
    errors="coerce"
).fillna(0)


# STATUS
df["STATUS"] = (
    df["STATUS"]
    .astype(str)
    .str.upper()
)


# =========================================================
# URUTKAN DATA
# =========================================================
df = df.sort_values(
    "id",
    ascending=False
)


# =========================================================
# DATA TERBARU
# =========================================================
latest = df.iloc[0]

rpm = float(latest["RPM"])

vibration = float(latest["Vrms"])

status = latest["STATUS"]


# =========================================================
# AMBIL DATA CONTROL D310
# =========================================================
try:

    control_res = (
        supabase
        .table("control")
        .select("D310")
        .eq("id", 1)
        .limit(1)
        .execute()
    )

    if control_res.data:

        cmd = int(
            control_res.data[0]["D310"]
        )

    else:

        cmd = 0

except Exception:

    cmd = 0


# =========================================================
# HEADER
# =========================================================
st.markdown("""
<h1 style='text-align:center'>
⚙️ INDUSTRIAL MACHINE MONITORING ⚙️
</h1>

<p style='text-align:center'>
PLC • ESP32 • IoT • REALTIME SYSTEM
</p>
""", unsafe_allow_html=True)


# =========================================================
# INFO DATA TERBARU
# =========================================================
st.markdown(
    f"""
    <p style='text-align:center;color:#94a3b8'>
    Data terakhir diterima: {latest["TIME"]}
    </p>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ALARM PANEL
# =========================================================

if status == "DANGER":

    if cmd == 0 and rpm < 50:

        st.markdown("""
        <div style='background:red;
        padding:20px;
        border-radius:10px;
        text-align:center'>

        <h1>⛔ AUTO STOP AKTIF</h1>

        <h3>
        Mesin dimatikan otomatis oleh PLC
        </h3>

        </div>
        """, unsafe_allow_html=True)

    else:

        st.markdown("""
        <div style='background:red;
        padding:20px;
        border-radius:10px;
        text-align:center'>

        <h1>🚨 DANGER</h1>

        <h3>
        Mesin sedang dihentikan otomatis...
        </h3>

        </div>
        """, unsafe_allow_html=True)


elif status == "WARNING":

    st.markdown("""
    <div style='background:orange;
    padding:20px;
    border-radius:10px;
    text-align:center'>

    <h1>
    ⚠ WARNING - PERLU PENGECEKAN ⚠
    </h1>

    </div>
    """, unsafe_allow_html=True)


elif status == "GOOD":

    if cmd == 0:

        st.markdown("""
        <div style='background:gray;
        padding:20px;
        border-radius:10px;
        text-align:center'>

        <h1>⚪ MESIN OFF</h1>

        <h3>
        Mesin dimatikan manual
        </h3>

        </div>
        """, unsafe_allow_html=True)

    else:

        st.markdown("""
        <div style='background:green;
        padding:20px;
        border-radius:10px;
        text-align:center'>

        <h1>🟢 RUNNING NORMAL</h1>

        </div>
        """, unsafe_allow_html=True)


# =========================================================
# KPI
# =========================================================
col1, col2 = st.columns(2)


# =========================================================
# RPM GAUGE
# =========================================================
with col1:

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=rpm,

            title={
                "text": "RPM Mesin"
            },

            number={
                "valueformat": ".0f"
            },

            gauge={

                "axis": {
                    "range": [0, 2500]
                },

                "steps": [

                    {
                        "range": [0, 833],
                        "color": "blue"
                    },

                    {
                        "range": [833, 1666],
                        "color": "yellow"
                    },

                    {
                        "range": [1666, 2500],
                        "color": "red"
                    }
                ]
            }
        )
    )

    st.plotly_chart(
        fig_gauge,
        use_container_width=True
    )


# =========================================================
# VRMS
# =========================================================
with col2:

    st.markdown(
        f"""
        <div style='background:#1e293b;
        padding:30px;
        border-radius:10px;
        text-align:center'>

        <h2>Getaran (Vrms)</h2>

        <h1>
        {vibration:.2f} mm/s
        </h1>

        <h2>
        Status: {status}
        </h2>

        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # KONTROL MESIN
    # =====================================================

    if status == "WARNING":

        st.markdown(
            "### ⚙️ Kontrol Mesin"
        )

        col_btn1, col_btn2 = st.columns(2)


        # =================================================
        # STOP
        # =================================================
        with col_btn1:

            if st.button(
                "🛑 MATIKAN MESIN",
                use_container_width=True
            ):

                if (
                    time.time()
                    -
                    st.session_state.last_click
                    > 2
                ):

                    st.session_state.last_click = (
                        time.time()
                    )

                    try:

                        (
                            supabase
                            .table("control")
                            .update({
                                "D310": 0
                            })
                            .eq("id", 1)
                            .execute()
                        )

                        st.success(
                            "Perintah STOP dikirim!"
                        )

                    except Exception as e:

                        st.error(
                            f"Gagal: {e}"
                        )

                else:

                    st.warning(
                        "Tunggu 2 detik sebelum klik lagi"
                    )


        # =================================================
        # RUN
        # =================================================
        with col_btn2:

            if st.button(
                "▶️ HIDUPKAN MESIN",
                use_container_width=True
            ):

                if (
                    time.time()
                    -
                    st.session_state.last_click
                    > 2
                ):

                    st.session_state.last_click = (
                        time.time()
                    )

                    try:

                        (
                            supabase
                            .table("control")
                            .update({
                                "D310": 1
                            })
                            .eq("id", 1)
                            .execute()
                        )

                        st.success(
                            "Perintah RUN dikirim!"
                        )

                    except Exception as e:

                        st.error(
                            f"Gagal: {e}"
                        )

                else:

                    st.warning(
                        "Tunggu 2 detik sebelum klik lagi"
                    )


st.divider()


# =========================================================
# DATA UNTUK GRAFIK
# =========================================================

df_plot = (
    df
    .sort_values("id")
    .tail(50)
)


# =========================================================
# GRAFIK
# =========================================================
colg1, colg2 = st.columns(2)


# =========================================================
# GRAFIK RPM
# =========================================================
with colg1:

    fig_rpm = px.line(
        df_plot,
        x="TIME",
        y="RPM",
        markers=True
    )

    fig_rpm.update_layout(
        title="Grafik RPM",
        xaxis_title="Waktu",
        yaxis_title="RPM"
    )

    st.plotly_chart(
        fig_rpm,
        use_container_width=True
    )


# =========================================================
# GRAFIK GETARAN
# =========================================================
with colg2:

    fig_vib = px.line(
        df_plot,
        x="TIME",
        y="Vrms",
        markers=True
    )

    fig_vib.add_hline(
        y=4,
        line_dash="dash",
        line_color="yellow"
    )

    fig_vib.add_hline(
        y=7,
        line_dash="dash",
        line_color="red"
    )

    fig_vib.update_layout(
        title="Grafik Getaran",
        xaxis_title="Waktu",
        yaxis_title="Vrms (mm/s)"
    )

    st.plotly_chart(
        fig_vib,
        use_container_width=True
    )


st.divider()


# =========================================================
# TABEL
# =========================================================
st.subheader(
    "Data Monitoring"
)


st.dataframe(
    df.sort_values(
        "id",
        ascending=False
    ),
    use_container_width=True,
    hide_index=True
)