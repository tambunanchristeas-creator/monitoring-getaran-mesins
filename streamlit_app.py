import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
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
            .select("id,TIME,RPM,Vrms,AccRMS,STATUS")
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
                "id,created_at,sample_count,sampling_frequency,data"
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
# FUNGSI HITUNG FFT
# =========================================================

def calculate_fft(data, sampling_frequency):

    signal = np.asarray(data, dtype=float)

    # -----------------------------------------------------
    # Validasi
    # -----------------------------------------------------

    if len(signal) < 4:
        return None, None, None

    if sampling_frequency <= 0:
        return None, None, None

    # -----------------------------------------------------
    # Hilangkan DC / nilai rata-rata
    # -----------------------------------------------------

    signal = signal - np.mean(signal)

    # -----------------------------------------------------
    # Hann window
    # -----------------------------------------------------

    window = np.hanning(len(signal))

    signal_windowed = signal * window

    # -----------------------------------------------------
    # FFT
    # -----------------------------------------------------

    fft_result = np.fft.rfft(signal_windowed)

    # -----------------------------------------------------
    # Frekuensi
    # -----------------------------------------------------

    frequency = np.fft.rfftfreq(
        len(signal),
        d=1.0 / sampling_frequency
    )

    # -----------------------------------------------------
    # Amplitudo satu sisi
    # -----------------------------------------------------

    amplitude = (
        2.0 / np.sum(window)
    ) * np.abs(fft_result)

    # DC tidak dikali 2
    amplitude[0] = (
        np.abs(fft_result[0])
        / np.sum(window)
    )

    # -----------------------------------------------------
    # Nyquist tidak perlu dikali 2
    # jika jumlah sampel genap
    # -----------------------------------------------------

    if len(signal) % 2 == 0:
        amplitude[-1] = (
            np.abs(fft_result[-1])
            / np.sum(window)
        )

    return frequency, amplitude, signal

# =========================================================
# INTERPOLASI PEAK FFT
# =========================================================

def interpolate_peak_frequency(
    frequency,
    amplitude,
    index
):

    # Tidak bisa interpolasi di ujung
    if index <= 0 or index >= len(amplitude) - 1:
        return (
            frequency[index],
            amplitude[index]
        )

    y1 = amplitude[index - 1]
    y2 = amplitude[index]
    y3 = amplitude[index + 1]

    denominator = (
        y1
        - 2.0 * y2
        + y3
    )

    if denominator == 0:
        return (
            frequency[index],
            amplitude[index]
        )

    # Parabolic interpolation
    delta = 0.5 * (
        (y1 - y3)
        / denominator
    )

    frequency_resolution = (
        frequency[1] - frequency[0]
    )

    estimated_frequency = (
        frequency[index]
        + delta * frequency_resolution
    )

    # Estimasi amplitude
    estimated_amplitude = (
        y2
        - 0.25 * (y1 - y3) * delta
    )

    return (
        estimated_frequency,
        estimated_amplitude
    )


# =========================================================
# CARI PEAK DI SEKITAR FREKUENSI TARGET
# =========================================================

def get_peak_near_frequency(
    target_frequency,
    frequency,
    amplitude,
    bandwidth=1.0
):

    if target_frequency <= 0:
        return 0.0, 0.0

    if len(frequency) == 0:
        return 0.0, 0.0

    # -----------------------------------------------------
    # Jangan mencari di atas Nyquist
    # -----------------------------------------------------

    nyquist = frequency[-1]

    if target_frequency > nyquist:
        return 0.0, 0.0

    # -----------------------------------------------------
    # Batasi pencarian
    # -----------------------------------------------------

    lower = max(
        0.0,
        target_frequency - bandwidth
    )

    upper = min(
        nyquist,
        target_frequency + bandwidth
    )

    mask = (
        (frequency >= lower)
        &
        (frequency <= upper)
    )

    if not np.any(mask):
        return 0.0, 0.0

    local_indices = np.where(mask)[0]

    # -----------------------------------------------------
    # Cari amplitudo terbesar
    # -----------------------------------------------------

    local_index = local_indices[
        np.argmax(
            amplitude[local_indices]
        )
    ]

    # -----------------------------------------------------
    # Interpolasi peak
    # -----------------------------------------------------

    return interpolate_peak_frequency(
        frequency,
        amplitude,
        local_index
    )


# =========================================================
# CARI PEAK PADA BAND FREKUENSI TERTENTU
# =========================================================

def get_band_peak(
    lower_frequency,
    upper_frequency,
    frequency,
    amplitude
):

    if lower_frequency >= upper_frequency:
        return 0.0, 0.0

    mask = (
        (frequency >= lower_frequency)
        &
        (frequency <= upper_frequency)
    )

    if not np.any(mask):
        return 0.0, 0.0

    local_indices = np.where(mask)[0]

    local_index = local_indices[
        np.argmax(
            amplitude[local_indices]
        )
    ]

    return interpolate_peak_frequency(
        frequency,
        amplitude,
        local_index
    )

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


# ARMS
df["Vrms"] = pd.to_numeric(
    df["Vrms"],
    errors="coerce"
).fillna(0)

df["Vrms"] = df["Vrms"] / 100.0

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

velocity_rms = float(latest["Vrms"])

acceleration_rms = float(latest["AccRMS"])

status = latest["STATUS"]

# =========================================================
# FREKUENSI HARMONIK BERDASARKAN RPM
# =========================================================

one_x_frequency = rpm / 60.0
two_x_frequency = one_x_frequency * 2
three_x_frequency = one_x_frequency * 3

# =========================================================
# HITUNG FREKUENSI 1× FFT DAN VELOCITY RMS
# =========================================================

one_x_actual_frequency = 0.0
one_x_amplitude = 0.0

if fft_latest is not None:

    try:

        # -------------------------------------------------
        # Ambil data FFT
        # -------------------------------------------------

        fft_sample_count = int(
            fft_latest["sample_count"]
        )

        fft_sampling_frequency = float(
            fft_latest["sampling_frequency"]
        )

        fft_data_temp = fft_latest["data"]

        # -------------------------------------------------
        # Jika data berupa string JSON
        # -------------------------------------------------

        if isinstance(fft_data_temp, str):

            import json

            fft_data_temp = json.loads(
                fft_data_temp
            )

        fft_data_temp = np.array(
            fft_data_temp,
            dtype=float
        )

        # -------------------------------------------------
        # Pastikan jumlah data benar
        # -------------------------------------------------

        if len(fft_data_temp) == fft_sample_count:

            # -------------------------------------------------
            # D110 → Acceleration mm/s²
            # -------------------------------------------------

            fft_data_acc_temp = (
                fft_data_temp * 12.387
            )

            # -------------------------------------------------
            # Hitung FFT
            # -------------------------------------------------

            frequency_temp, amplitude_temp = calculate_fft(
                fft_data_acc_temp,
                fft_sampling_frequency
            )

            # -------------------------------------------------
            # Frekuensi 1× dari RPM
            # -------------------------------------------------

            rpm_frequency_temp = rpm / 60.0

            # -------------------------------------------------
            # Cari peak FFT di sekitar frekuensi 1×
            # -------------------------------------------------

            if rpm_frequency_temp > 0:

                mask_1x = (
                    np.abs(
                        frequency_temp
                        - rpm_frequency_temp
                    )
                    <= 1.0
                )

                if np.any(mask_1x):

                    local_indices_1x = np.where(
                        mask_1x
                    )[0]

                    local_index_1x = (
                        local_indices_1x[
                            np.argmax(
                                amplitude_temp[
                                    local_indices_1x
                                ]
                            )
                        ]
                    )

                    one_x_actual_frequency = (
                        frequency_temp[
                            local_index_1x
                        ]
                    )

                    one_x_amplitude = (
                        amplitude_temp[
                            local_index_1x
                        ]
                    )


    except Exception:

        one_x_actual_frequency = 0.0
        one_x_amplitude = 0.0
        velocity_rms = 0.0
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
        {velocity_rms:.2f} mm/s
        </h1>

        <h3>
        Acceleration RMS:
        {acceleration_rms:.2f} mm/s²
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

    st.warning(
        "Belum ada data FFT dari PLC."
    )

else:

    try:

        # =================================================
        # METADATA FFT
        # =================================================

        fft_id = fft_latest["id"]

        fft_time = fft_latest["created_at"]

        sample_count = int(
            fft_latest["sample_count"]
        )

        sampling_frequency = float(
            fft_latest["sampling_frequency"]
        )

        fft_data = fft_latest["data"]

        # -------------------------------------------------
        # Data JSON → list
        # -------------------------------------------------

        if isinstance(fft_data, str):

            import json

            fft_data = json.loads(
                fft_data
            )

        fft_data = np.asarray(
            fft_data,
            dtype=float
        )

        # =================================================
        # VALIDASI PARAMETER
        # =================================================

        if sample_count < 4:

            st.error(
                "Jumlah sampel FFT terlalu sedikit."
            )

            st.stop()

        if sampling_frequency <= 0:

            st.error(
                "Sampling frequency tidak valid."
            )

            st.stop()

        if len(fft_data) != sample_count:

            st.error(
                f"Jumlah data FFT tidak sesuai. "
                f"Expected: {sample_count}, "
                f"Received: {len(fft_data)}"
            )

            st.stop()

        # =================================================
        # PARAMETER FFT
        # =================================================

        nyquist = (
            sampling_frequency / 2.0
        )

        frequency_resolution = (
            sampling_frequency
            / sample_count
        )

        capture_duration = (
            sample_count
            / sampling_frequency
        )

        # =================================================
        # KONVERSI D110
        # =================================================

        # D110 × 12.387 = mm/s²

        fft_data_acc = (
            fft_data * 12.387
        )

        # =================================================
        # HITUNG FFT
        # =================================================

        frequency, amplitude, signal_detrended = (
            calculate_fft(
                fft_data_acc,
                sampling_frequency
            )
        )

        if frequency is None:

            st.error(
                "FFT gagal dihitung."
            )

            st.stop()

        # =================================================
        # DOMINANT FREQUENCY
        # =================================================

        if len(amplitude) > 1:

            # Abaikan DC / 0 Hz
            dominant_index = (
                np.argmax(
                    amplitude[1:]
                ) + 1
            )

            (
                dominant_frequency,
                dominant_amplitude
            ) = interpolate_peak_frequency(
                frequency,
                amplitude,
                dominant_index
            )

        else:

            dominant_frequency = 0.0
            dominant_amplitude = 0.0

        # =================================================
        # FREKUENSI 1× 2× 3× BERDASARKAN RPM
        # =================================================

        one_x_frequency = (
            rpm / 60.0
        )

        two_x_frequency = (
            one_x_frequency * 2.0
        )

        three_x_frequency = (
            one_x_frequency * 3.0
        )

        # =================================================
        # CARI PEAK HARMONIK
        # =================================================

        harmonic_bandwidth = 1.0

        (
            one_x_actual_frequency,
            one_x_amplitude
        ) = get_peak_near_frequency(
            one_x_frequency,
            frequency,
            amplitude,
            harmonic_bandwidth
        )

        (
            two_x_actual_frequency,
            two_x_amplitude
        ) = get_peak_near_frequency(
            two_x_frequency,
            frequency,
            amplitude,
            harmonic_bandwidth
        )

        (
            three_x_actual_frequency,
            three_x_amplitude
        ) = get_peak_near_frequency(
            three_x_frequency,
            frequency,
            amplitude,
            harmonic_bandwidth
        )

        # =================================================
        # DIAGNOSTIC KHUSUS PEAK 83–84 Hz
        # =================================================

        (
            peak_83_84_frequency,
            peak_83_84_amplitude
        ) = get_band_peak(
            82.0,
            86.0,
            frequency,
            amplitude
        )

        # =================================================
        # KPI FFT
        # =================================================

        c1, c2, c3, c4, c5 = st.columns(5)

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
                f"{frequency_resolution:.2f} Hz"
            )

        with c4:

            st.metric(
                "Nyquist",
                f"{nyquist:.0f} Hz"
            )

        with c5:

            st.metric(
                "Durasi Capture",
                f"{capture_duration:.2f} s"
            )

        # =================================================
        # DOMINANT PEAK
        # =================================================

        st.subheader(
            "Peak Dominan"
        )

        p1, p2, p3 = st.columns(3)

        with p1:

            st.metric(
                "Dominant Frequency",
                f"{dominant_frequency:.2f} Hz"
            )

        with p2:

            st.metric(
                "Amplitude",
                f"{dominant_amplitude:.2f} mm/s²"
            )

        with p3:

            st.metric(
                "RPM",
                f"{rpm:.0f}"
            )

        # =================================================
        # HARMONIK RPM
        # =================================================

        st.subheader(
            "Analisis Harmonik RPM"
        )

        h1, h2, h3 = st.columns(3)

        with h1:

            if one_x_frequency <= nyquist:

                st.metric(
                    "1× RPM",
                    f"{one_x_frequency:.2f} Hz",
                    f"FFT = {one_x_actual_frequency:.2f} Hz | "
                    f"Amp = {one_x_amplitude:.2f}"
                )

            else:

                st.metric(
                    "1× RPM",
                    f"{one_x_frequency:.2f} Hz",
                    "Di atas Nyquist"
                )

        with h2:

            if two_x_frequency <= nyquist:

                st.metric(
                    "2× RPM",
                    f"{two_x_frequency:.2f} Hz",
                    f"FFT = {two_x_actual_frequency:.2f} Hz | "
                    f"Amp = {two_x_amplitude:.2f}"
                )

            else:

                st.metric(
                    "2× RPM",
                    f"{two_x_frequency:.2f} Hz",
                    "Di atas Nyquist"
                )

        with h3:

            if three_x_frequency <= nyquist:

                st.metric(
                    "3× RPM",
                    f"{three_x_frequency:.2f} Hz",
                    f"FFT = {three_x_actual_frequency:.2f} Hz | "
                    f"Amp = {three_x_amplitude:.2f}"
                )

            else:

                st.metric(
                    "3× RPM",
                    f"{three_x_frequency:.2f} Hz",
                    "Di atas Nyquist"
                )

        # =================================================
        # DIAGNOSTIC 83–84 Hz
        # =================================================

        st.subheader(
            "🔎 Monitoring Peak 83–84 Hz"
        )

        d1, d2, d3 = st.columns(3)

        with d1:

            st.metric(
                "Peak 82–86 Hz",
                f"{peak_83_84_frequency:.2f} Hz"
            )

        with d2:

            st.metric(
                "Amplitude 82–86 Hz",
                f"{peak_83_84_amplitude:.2f} mm/s²"
            )

        with d3:

            if peak_83_84_amplitude > 0:

                st.write(
                    f"RPM saat ini: **{rpm:.0f} RPM**"
                )

                st.write(
                    f"2× RPM: **{two_x_frequency:.2f} Hz**"
                )

            else:

                st.write(
                    "Tidak ditemukan peak pada 82–86 Hz."
                )

        # =================================================
        # DATA FFT UNTUK GRAFIK
        # =================================================

        df_fft = pd.DataFrame({

            "Frequency": frequency,

            "Acceleration": amplitude

        })

        # =================================================
        # GRAFIK FFT
        # =================================================

        fig_fft = go.Figure()

        # -------------------------------------------------
        # FFT Spectrum
        # -------------------------------------------------

        fig_fft.add_trace(

            go.Scatter(

                x=df_fft["Frequency"],

                y=df_fft["Acceleration"],

                mode="lines",

                name="Acceleration FFT"

            )
        )

        # =================================================
        # MARKER DOMINANT
        # =================================================

        fig_fft.add_trace(

            go.Scatter(

                x=[dominant_frequency],

                y=[dominant_amplitude],

                mode="markers",

                marker={
                    "size": 12
                },

                name="Dominant Peak",

                hovertemplate=(
                    "Dominant<br>"
                    "Frequency: %{x:.2f} Hz<br>"
                    "Amplitude: %{y:.2f} mm/s²"
                    "<extra></extra>"
                )

            )
        )

        # =================================================
        # MARKER 1×
        # =================================================

        if (
            one_x_frequency > 0
            and one_x_frequency <= nyquist
        ):

            fig_fft.add_trace(

                go.Scatter(

                    x=[one_x_actual_frequency],

                    y=[one_x_amplitude],

                    mode="markers",

                    marker={
                        "size": 10
                    },

                    name="Peak 1×",

                    hovertemplate=(
                        "1× RPM<br>"
                        "Frequency: %{x:.2f} Hz<br>"
                        "Amplitude: %{y:.2f} mm/s²"
                        "<extra></extra>"
                    )

                )
            )

            fig_fft.add_vline(

                x=one_x_frequency,

                line_dash="dash",

                annotation_text=(
                    f"1× = "
                    f"{one_x_frequency:.2f} Hz"
                ),

                annotation_position="top"

            )

        # =================================================
        # MARKER 2×
        # =================================================

        if (
            two_x_frequency > 0
            and two_x_frequency <= nyquist
        ):

            fig_fft.add_trace(

                go.Scatter(

                    x=[two_x_actual_frequency],

                    y=[two_x_amplitude],

                    mode="markers",

                    marker={
                        "size": 10
                    },

                    name="Peak 2×",

                    hovertemplate=(
                        "2× RPM<br>"
                        "Frequency: %{x:.2f} Hz<br>"
                        "Amplitude: %{y:.2f} mm/s²"
                        "<extra></extra>"
                    )

                )
            )

            fig_fft.add_vline(

                x=two_x_frequency,

                line_dash="dash",

                annotation_text=(
                    f"2× = "
                    f"{two_x_frequency:.2f} Hz"
                ),

                annotation_position="top"

            )

        # =================================================
        # MARKER 3×
        # =================================================

        if (
            three_x_frequency > 0
            and three_x_frequency <= nyquist
        ):

            fig_fft.add_trace(

                go.Scatter(

                    x=[three_x_actual_frequency],

                    y=[three_x_amplitude],

                    mode="markers",

                    marker={
                        "size": 10
                    },

                    name="Peak 3×",

                    hovertemplate=(
                        "3× RPM<br>"
                        "Frequency: %{x:.2f} Hz<br>"
                        "Amplitude: %{y:.2f} mm/s²"
                        "<extra></extra>"
                    )

                )
            )

            fig_fft.add_vline(

                x=three_x_frequency,

                line_dash="dash",

                annotation_text=(
                    f"3× = "
                    f"{three_x_frequency:.2f} Hz"
                ),

                annotation_position="top"

            )

        # =================================================
        # TANDAI AREA 82–86 Hz
        # =================================================

        if nyquist >= 82:

            upper_83 = min(
                86,
                nyquist
            )

            fig_fft.add_vrect(

                x0=82,

                x1=upper_83,

                fillcolor="gray",

                opacity=0.15,

                line_width=0,

                annotation_text="82–86 Hz",

                annotation_position="top left"

            )

            if peak_83_84_frequency > 0:

                fig_fft.add_trace(

                    go.Scatter(

                        x=[
                            peak_83_84_frequency
                        ],

                        y=[
                            peak_83_84_amplitude
                        ],

                        mode="markers",

                        marker={
                            "size": 14
                        },

                        name="Peak 83–84 Hz",

                        hovertemplate=(
                            "Peak 82–86 Hz<br>"
                            "Frequency: %{x:.2f} Hz<br>"
                            "Amplitude: %{y:.2f} mm/s²"
                            "<extra></extra>"
                        )

                    )
                )

        # =================================================
        # LAYOUT FFT
        # =================================================

        fig_fft.update_layout(

            title=(
                "Frequency Spectrum "
                "(FFT)"
            ),

            xaxis_title=(
                "Frequency (Hz)"
            ),

            yaxis_title=(
                "Acceleration Amplitude "
                "(mm/s²)"
            ),

            xaxis=dict(

                range=[
                    0,
                    nyquist
                ]

            ),

            hovermode="x unified",

            height=600

        )

        st.plotly_chart(

            fig_fft,

            use_container_width=True

        )

        # =================================================
        # RAW SIGNAL
        # =================================================

        st.subheader(
            "Raw Signal D200–D699"
        )

        waktu = (
            np.arange(
                len(fft_data)
            )
            / sampling_frequency
        )

        df_raw_fft = pd.DataFrame({

            "Time": waktu,

            "D110": fft_data,

            "Acceleration": fft_data_acc

        })

        fig_raw = px.line(

            df_raw_fft,

            x="Time",

            y="Acceleration",

            title=(
                "Raw Signal - 500 Sampel"
            )

        )

        fig_raw.update_layout(

            xaxis_title="Time (s)",

            yaxis_title=(
                "Acceleration (mm/s²)"
            ),

            height=450

        )

        st.plotly_chart(

            fig_raw,

            use_container_width=True

        )

        # =================================================
        # INFO
        # =================================================

        st.caption(

            f"FFT ID: {fft_id} | "
            f"Data diterima: {fft_time} | "
            f"N = {sample_count} | "
            f"Fs = {sampling_frequency:.0f} Hz | "
            f"Δf = {frequency_resolution:.2f} Hz | "
            f"Nyquist = {nyquist:.0f} Hz | "
            f"Durasi = {capture_duration:.2f} s"

        )

    except Exception as e:

        st.error(
            "Terjadi kesalahan saat analisis FFT."
        )

        st.exception(e)
        
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