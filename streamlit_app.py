import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
import json
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
            .select(
                "id,TIME,RPM,VRMSX,VRMSY,VRMSZ,ARMSX,ARMSY,ARMSZ,STATUS"
            )
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
# LOAD DATA FFT
# =========================================================
def load_fft_data():

    try:

        res = (
            supabase
            .table("FFT")
            .select(
                "id,created_at,sample_count,sampling_frequency,data_x,data_y,data_z"
            )
            .order(
                "id",
                desc=True
            )
            .limit(1)
            .execute()
        )

        if not res.data:
            return None

        return res.data[0]

    except Exception as e:

        st.error("Gagal mengambil data FFT dari Supabase.")

        st.code(str(e))

        return None


# =========================================================
# AMBIL DATA
# =========================================================
df = load_data()

# =========================================================
# AMBIL FFT TERBARU
# =========================================================
fft_latest = load_fft_data()

# =========================================================
# CEK DATA
# =========================================================
if df.empty:

    st.warning("Belum ada data monitoring.")

    st.stop()

# =========================================================
# HITUNG FFT
# =========================================================
def calculate_fft(data, sampling_frequency):

    # -----------------------------------------------------
    # Konversi ke numpy
    # -----------------------------------------------------

    signal = np.array(
        data,
        dtype=float
    )

    # -----------------------------------------------------
    # Pastikan data cukup
    # -----------------------------------------------------

    if len(signal) < 2:
        return None, None

    # -----------------------------------------------------
    # Hilangkan DC / nilai rata-rata
    # -----------------------------------------------------

    signal = signal - np.mean(signal)

    # -----------------------------------------------------
    # Hanning window
    # -----------------------------------------------------

    window = np.hanning(len(signal))

    signal_windowed = signal * window

    # -----------------------------------------------------
    # FFT real signal
    # -----------------------------------------------------

    fft_result = np.fft.rfft(
        signal_windowed
    )

    # -----------------------------------------------------
    # Frekuensi
    # -----------------------------------------------------

    frequency = np.fft.rfftfreq(
        len(signal),
        d=1 / sampling_frequency
    )

    # -----------------------------------------------------
    # Magnitude
    # -----------------------------------------------------

    amplitude = (
        2.0 / np.sum(window)
    ) * np.abs(fft_result)

    # DC jangan dikalikan 2
    amplitude[0] = (
        np.abs(fft_result[0])
        / np.sum(window)
    )

    return frequency, amplitude

# =========================================================
# FORMAT DATA MONITORING
# =========================================================

df["RPM"] = pd.to_numeric(
    df["RPM"],
    errors="coerce"
).fillna(0)

for kolom in [
    "VRMSX",
    "VRMSY",
    "VRMSZ",
    "ARMSX",
    "ARMSY",
    "ARMSZ"
]:
    df[kolom] = pd.to_numeric(
        df[kolom],
        errors="coerce"
    ).fillna(0)

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

velocity_rms_x = float(latest["VRMSX"])
velocity_rms_y = float(latest["VRMSY"])
velocity_rms_z = float(latest["VRMSZ"])

acceleration_rms_x = float(latest["ARMSX"])
acceleration_rms_y = float(latest["ARMSY"])
acceleration_rms_z = float(latest["ARMSZ"])
status = latest["STATUS"]

# =========================================================
# FREKUENSI HARMONIK BERDASARKAN RPM
# =========================================================

one_x_frequency = rpm / 60.0
two_x_frequency = one_x_frequency * 2
three_x_frequency = one_x_frequency * 3

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
# VELOCITY RMS
# =========================================================

with col2:

    st.markdown(
        f"""
        <div style='background:#1e293b;
        padding:30px;
        border-radius:10px;
        text-align:center'>

        <h2>Getaran (Velocity RMS)</h2>

        <h1>
        {velocity_rms_x:.2f} mm/s
        </h1>

        <h3>
        Acceleration RMS X: {acceleration_rms_x:.2f} mm/s²
        </h3>

        <h3>
        Acceleration RMS Y: {acceleration_rms_y:.2f} mm/s²
        </h3>

        <h3>
        Acceleration RMS Z: {acceleration_rms_z:.2f} mm/s²
        </h3>

        <h3>
        1× Frequency:
        {one_x_frequency:.2f} Hz
        </h3>

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
# FFT ANALYSIS
# =========================================================

st.header("📊 Analisis FFT Getaran")

if fft_latest is None:

    st.warning("Belum ada data FFT dari PLC.")

else:

    # =====================================================
    # METADATA FFT
    # =====================================================

    fft_id = fft_latest["id"]
    fft_time = fft_latest["created_at"]

    sample_count = int(
        fft_latest["sample_count"]
    )

    sampling_frequency = float(
        fft_latest["sampling_frequency"]
    )

    # =====================================================
    # AMBIL DATA X, Y, Z
    # =====================================================

    fft_data_x = fft_latest["data_x"]
    fft_data_y = fft_latest["data_y"]
    fft_data_z = fft_latest["data_z"]

    if isinstance(fft_data_x, str):
        fft_data_x = json.loads(fft_data_x)

    if isinstance(fft_data_y, str):
        fft_data_y = json.loads(fft_data_y)

    if isinstance(fft_data_z, str):
        fft_data_z = json.loads(fft_data_z)

    fft_data_x = np.asarray(
        fft_data_x,
        dtype=float
    )

    fft_data_y = np.asarray(
        fft_data_y,
        dtype=float
    )

    fft_data_z = np.asarray(
        fft_data_z,
        dtype=float
    )

    # =====================================================
    # KONVERSI D110 KE PERCEPATAN
    # =====================================================
    # Gunakan faktor ini hanya jika data_x, data_y, data_z
    # masih berupa nilai D110.

    fft_data_acc_x = fft_data_x * 12.387
    fft_data_acc_y = fft_data_y * 12.387
    fft_data_acc_z = fft_data_z * 12.387

    # =====================================================
    # VALIDASI DATA
    # =====================================================

    if (
        len(fft_data_acc_x) != sample_count
        or len(fft_data_acc_y) != sample_count
        or len(fft_data_acc_z) != sample_count
    ):

        st.error(
            f"Jumlah data FFT tidak sesuai. "
            f"Expected: {sample_count}, "
            f"X: {len(fft_data_acc_x)}, "
            f"Y: {len(fft_data_acc_y)}, "
            f"Z: {len(fft_data_acc_z)}"
        )

    elif sampling_frequency <= 0:

        st.error("Sampling frequency harus lebih besar dari 0 Hz.")

    else:

        # =================================================
        # HITUNG FFT X, Y, Z
        # =================================================

        frequency_x, amplitude_x = calculate_fft(
            fft_data_acc_x,
            sampling_frequency
        )

        frequency_y, amplitude_y = calculate_fft(
            fft_data_acc_y,
            sampling_frequency
        )

        frequency_z, amplitude_z = calculate_fft(
            fft_data_acc_z,
            sampling_frequency
        )

        # =================================================
        # FUNGSI FREKUENSI DOMINAN
        # =================================================

        def get_dominant_peak(frequency, amplitude):

            if frequency is None or amplitude is None:
                return 0.0, 0.0

            if len(amplitude) <= 1:
                return 0.0, 0.0

            dominant_index = (
                np.argmax(amplitude[1:]) + 1
            )

            return (
                float(frequency[dominant_index]),
                float(amplitude[dominant_index])
            )

        # =================================================
        # FREKUENSI DOMINAN X, Y, Z
        # =================================================

        dominant_frequency_x, dominant_amplitude_x = (
            get_dominant_peak(
                frequency_x,
                amplitude_x
            )
        )

        dominant_frequency_y, dominant_amplitude_y = (
            get_dominant_peak(
                frequency_y,
                amplitude_y
            )
        )

        dominant_frequency_z, dominant_amplitude_z = (
            get_dominant_peak(
                frequency_z,
                amplitude_z
            )
        )

        # =================================================
        # INFORMASI FFT
        # =================================================

        nyquist = sampling_frequency / 2
        resolution_fft = sampling_frequency / sample_count

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Jumlah Sampel",
                sample_count
            )

        with c2:
            st.metric(
                "Sampling",
                f"{sampling_frequency:.0f} Hz"
            )

        with c3:
            st.metric(
                "Resolusi FFT",
                f"{resolution_fft:.2f} Hz"
            )

        with c4:
            st.metric(
                "Nyquist",
                f"{nyquist:.1f} Hz"
            )

        # =================================================
        # FREKUENSI DOMINAN X, Y, Z
        # =================================================

        d1, d2, d3 = st.columns(3)

        with d1:
            st.metric(
                "Dominan Sumbu X",
                f"{dominant_frequency_x:.2f} Hz",
                f"Amplitudo: {dominant_amplitude_x:.2f}"
            )

        with d2:
            st.metric(
                "Dominan Sumbu Y",
                f"{dominant_frequency_y:.2f} Hz",
                f"Amplitudo: {dominant_amplitude_y:.2f}"
            )

        with d3:
            st.metric(
                "Dominan Sumbu Z",
                f"{dominant_frequency_z:.2f} Hz",
                f"Amplitudo: {dominant_amplitude_z:.2f}"
            )

        # =================================================
        # DATA FRAME FFT X, Y, Z
        # =================================================

        df_fft_x = pd.DataFrame({
            "Frequency": frequency_x,
            "Acceleration": amplitude_x
        })

        df_fft_y = pd.DataFrame({
            "Frequency": frequency_y,
            "Acceleration": amplitude_y
        })

        df_fft_z = pd.DataFrame({
            "Frequency": frequency_z,
            "Acceleration": amplitude_z
        })

        # =================================================
        # BATASI FREKUENSI SAMPAI NYQUIST
        # =================================================

        df_fft_x = df_fft_x[
            df_fft_x["Frequency"] <= nyquist
        ]

        df_fft_y = df_fft_y[
            df_fft_y["Frequency"] <= nyquist
        ]

        df_fft_z = df_fft_z[
            df_fft_z["Frequency"] <= nyquist
        ]

        # =================================================
        # GRAFIK FFT SUMBU X
        # =================================================

        st.subheader("Spektrum FFT Sumbu X")

        fig_fft_x = go.Figure()

        fig_fft_x.add_trace(
            go.Scatter(
                x=df_fft_x["Frequency"],
                y=df_fft_x["Acceleration"],
                mode="lines",
                name="FFT Sumbu X"
            )
        )

        fig_fft_x.update_layout(
            title="FFT Getaran Sumbu X",
            xaxis_title="Frekuensi (Hz)",
            yaxis_title="Amplitudo Percepatan (mm/s²)",
            xaxis=dict(
                range=[0, nyquist]
            ),
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_fft_x,
            use_container_width=True
        )

        # =================================================
        # GRAFIK FFT SUMBU Y
        # =================================================

        st.subheader("Spektrum FFT Sumbu Y")

        fig_fft_y = go.Figure()

        fig_fft_y.add_trace(
            go.Scatter(
                x=df_fft_y["Frequency"],
                y=df_fft_y["Acceleration"],
                mode="lines",
                name="FFT Sumbu Y"
            )
        )

        fig_fft_y.update_layout(
            title="FFT Getaran Sumbu Y",
            xaxis_title="Frekuensi (Hz)",
            yaxis_title="Amplitudo Percepatan (mm/s²)",
            xaxis=dict(
                range=[0, nyquist]
            ),
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_fft_y,
            use_container_width=True
        )

        # =================================================
        # GRAFIK FFT SUMBU Z
        # =================================================

        st.subheader("Spektrum FFT Sumbu Z")

        fig_fft_z = go.Figure()

        fig_fft_z.add_trace(
            go.Scatter(
                x=df_fft_z["Frequency"],
                y=df_fft_z["Acceleration"],
                mode="lines",
                name="FFT Sumbu Z"
            )
        )

        fig_fft_z.update_layout(
            title="FFT Getaran Sumbu Z",
            xaxis_title="Frekuensi (Hz)",
            yaxis_title="Amplitudo Percepatan (mm/s²)",
            xaxis=dict(
                range=[0, nyquist]
            ),
            hovermode="x unified"
        )

        st.plotly_chart(
            fig_fft_z,
            use_container_width=True
        )

        # =================================================
        # RAW SIGNAL X, Y, Z
        # =================================================

        st.subheader("Raw Signal Getaran X, Y, dan Z")

        waktu = (
            np.arange(sample_count)
            / sampling_frequency
        )

        df_raw_fft = pd.DataFrame({
            "Time": waktu,
            "X": fft_data_acc_x,
            "Y": fft_data_acc_y,
            "Z": fft_data_acc_z
        })

        fig_raw = px.line(
            df_raw_fft,
            x="Time",
            y=["X", "Y", "Z"],
            title="Raw Signal Getaran X, Y, dan Z"
        )

        fig_raw.update_layout(
            xaxis_title="Waktu (s)",
            yaxis_title="Percepatan (mm/s²)"
        )

        st.plotly_chart(
            fig_raw,
            use_container_width=True
        )

        # =================================================
        # INFORMASI DATA FFT
        # =================================================

        st.caption(
            f"FFT ID: {fft_id} | "
            f"Data diterima: {fft_time} | "
            f"Resolusi frekuensi: "
            f"{resolution_fft:.2f} Hz"
        )
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
        y=["VRMSX", "VRMSY", "VRMSZ"],
        markers=True,
        title="Grafik Velocity RMS X, Y, dan Z"
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
        title="Grafik Getaran - Velocity RMS",
        xaxis_title="Waktu",
        yaxis_title="velocity RMS (mm/s)"
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