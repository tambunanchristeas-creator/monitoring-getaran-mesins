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

[data-testid="stHeader"] {
    background-color: #0f172a;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

h1, h2, h3, h4, h5, h6, p {
    color: white;
}

.monitor-panel {
    padding: 5px 0 15px 0;
}

.panel-title {
    font-size: 34px;
    font-weight: 700;
    color: white;
}

.value-label {
    font-size: 16px;
    color: #cbd5e1;
    margin-bottom: 5px;
}

.value-number {
    font-size: 31px;
    font-weight: 400;
    color: white;
    white-space: nowrap;
}

.value-number span {
    font-size: 18px;
    color: #e2e8f0;
}

.acc-number {
    font-size: 25px;
    font-weight: 400;
    color: white;
    white-space: nowrap;
}

.acc-number span {
    font-size: 15px;
    color: #e2e8f0;
}

.panel-line {
    border: none;
    border-top: 1px solid #334155;
    margin-top: 28px;
    margin-bottom: 28px;
}

.section-title {
    font-size: 25px;
    font-weight: 600;
    color: white;
    margin-bottom: 20px;
}

.frequency-box {
    text-align: center;
    margin-top: 28px;
    font-size: 22px;
    color: white;
}

.status-box {
    text-align: center;
    margin-top: 22px;
    font-size: 30px;
    font-weight: 600;
}

.status-box span {
    color: white;
}

button[kind="secondary"] {
    background-color: #ef4444 !important;
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
# FUNGSI PENANDA HARMONIK 1X, 2X, 3X
# =========================================================

def add_harmonic_markers(fig, one_x, two_x, three_x):

    fig.add_vline(
        x=one_x,
        line_dash="dash",
        line_color="cyan",
        line_width=2
    )

    fig.add_annotation(
        x=one_x,
        y=1,
        yref="paper",
        text=f"1× = {one_x:.2f} Hz",
        showarrow=False,
        yshift=10,
        font=dict(color="cyan")
    )

    fig.add_vline(
        x=two_x,
        line_dash="dash",
        line_color="yellow",
        line_width=2
    )

    fig.add_annotation(
        x=two_x,
        y=1,
        yref="paper",
        text=f"2× = {two_x:.2f} Hz",
        showarrow=False,
        yshift=10,
        font=dict(color="yellow")
    )

    fig.add_vline(
        x=three_x,
        line_dash="dash",
        line_color="red",
        line_width=2
    )

    fig.add_annotation(
        x=three_x,
        y=1,
        yref="paper",
        text=f"3× = {three_x:.2f} Hz",
        showarrow=False,
        yshift=10,
        font=dict(color="red")
    )

    return fig

# =========================================================
# AMBIL DATA CONTROL D5
# =========================================================
try:

    control_res = (
        supabase
        .table("control")
        .select("D5")
        .eq("id", 1)
        .limit(1)
        .execute()
    )

    if control_res.data:

        cmd = int(
            control_res.data[0]["D5"]
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
# DASHBOARD UTAMA
# =========================================================

col_left, col_right = st.columns(
    [1, 1.45],
    gap="medium"
)


# =========================================================
# RPM GAUGE
# =========================================================

with col_left:

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=rpm,

            title={
                "text": "RPM Mesin",
                "font": {
                    "size": 22,
                    "color": "white"
                }
            },

            number={
                "valueformat": ".0f",
                "font": {
                    "size": 64,
                    "color": "white"
                }
            },

            gauge={

                "axis": {
                    "range": [0, 2500],

                    "tickmode": "array",

                    "tickvals": [
                        0,
                        500,
                        1000,
                        1500,
                        2000,
                        2500
                    ],

                    "tickfont": {
                        "color": "white",
                        "size": 13
                    }
                },

                "bar": {
                    "color": "#4C9F38",
                    "thickness": 0.25
                },

                "bgcolor": "#0f172a",

                "borderwidth": 0,

                "steps": [

                    {
                        "range": [0, 833],
                        "color": "#0000FF"
                    },

                    {
                        "range": [833, 1666],
                        "color": "#3A7D20"
                    },

                    {
                        "range": [1666, 2083],
                        "color": "#FFFF00"
                    },

                    {
                        "range": [2083, 2500],
                        "color": "#FF2B1A"
                    }
                ],

                "threshold": {

                    "line": {
                        "color": "white",
                        "width": 4
                    },

                    "thickness": 0.8,

                    "value": rpm
                }
            }
        )
    )


    fig_gauge.update_layout(

        height=560,

        margin=dict(
            l=20,
            r=20,
            t=70,
            b=20
        ),

        paper_bgcolor="#0f172a",

        plot_bgcolor="#0f172a",

        font=dict(
            color="white"
        )
    )


    # =====================================================
    # INDIKATOR UNIT RPM
    # =====================================================

    fig_gauge.add_shape(

        type="rect",

        xref="paper",
        yref="paper",

        x0=0.445,
        x1=0.475,

        y0=0.25,
        y1=0.20,

        fillcolor="#4C9F38",

        line=dict(
            color="#4C9F38",
            width=1
        )
    )


    fig_gauge.add_annotation(

        x=0.485,
        y=0.025,

        xref="paper",
        yref="paper",

        text="RPM",

        showarrow=False,

        font=dict(
            color="#FFFFFF",
            size=14,
            family="Arial"
        ),

        xanchor="left",

        yanchor="middle"
    )


    st.plotly_chart(

        fig_gauge,

        use_container_width=True,

        config={
            "displayModeBar": False
        }
    )


# =========================================================
# PANEL GETARAN
# =========================================================

with col_right:

    st.markdown(
        """
<div class="monitor-panel">
    <div class="panel-title">
        Getaran (Velocity RMS)
    </div>
</div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # VELOCITY RMS X Y Z
    # =====================================================

    vx, vy, vz = st.columns(3)


    with vx:

        st.markdown(
            """
            <div class="value-label">
                Velocity RMS X
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="value-number">
                {velocity_rms_x:.2f}
                <span>mm/s</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    with vy:

        st.markdown(
            """
            <div class="value-label">
                Velocity RMS Y
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="value-number">
                {velocity_rms_y:.2f}
                <span>mm/s</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    with vz:

        st.markdown(
            """
            <div class="value-label">
                Velocity RMS Z
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="value-number">
                {velocity_rms_z:.2f}
                <span>mm/s</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    # =====================================================
    # GARIS PEMISAH
    # =====================================================

    st.markdown(
        "<hr class='panel-line'>",
        unsafe_allow_html=True
    )


    # =====================================================
    # ACCELERATION RMS
    # =====================================================

    st.markdown(
        """
        <div class="section-title">
            Acceleration RMS
        </div>
        """,

        unsafe_allow_html=True
    )


    ax, ay, az = st.columns(3)


    with ax:

        st.markdown(
            """
            <div class="value-label">
                Acceleration X
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="acc-number">
                {acceleration_rms_x:.2f}
                <span>mm/s²</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    with ay:

        st.markdown(
            """
            <div class="value-label">
                Acceleration Y
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="acc-number">
                {acceleration_rms_y:.2f}
                <span>mm/s²</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    with az:

        st.markdown(
            """
            <div class="value-label">
                Acceleration Z
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="acc-number">
                {acceleration_rms_z:.2f}
                <span>mm/s²</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    # =====================================================
    # FREKUENSI 1X
    # =====================================================

    st.markdown(
        f"""
    <div class="frequency-box">
        <b>1× Frequency: {one_x_frequency:.2f} Hz</b>
    </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # STATUS
    # =====================================================

    if status == "GOOD":

        status_color = "#22c55e"

    elif status == "WARNING":

        status_color = "#facc15"

    elif status == "DANGER":

        status_color = "#ef4444"

    else:

        status_color = "#94a3b8"


    st.markdown(
        f"""
    <div class="status-box">
        <span>Status:</span>
        <b style="color:{status_color}">{status}</b>
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
        # STOP MESIN
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
                                "D5": 0
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
        # RUN MESIN
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
                                "D5": 1
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


# =========================================================
# PEMISAH KE FFT
# =========================================================

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
        # FUNGSI PEAK HARMONIK 1X, 2X, 3X
        # =================================================

        def get_harmonic_peaks(
            frequency,
            amplitude,
            rpm,
            bandwidth=1.0
        ):

            if frequency is None or amplitude is None:
                return {
                    "1x": (0.0, 0.0),
                    "2x": (0.0, 0.0),
                    "3x": (0.0, 0.0)
                }

            if len(amplitude) <= 1:
                return {
                    "1x": (0.0, 0.0),
                    "2x": (0.0, 0.0),
                    "3x": (0.0, 0.0)
                }

            if rpm <= 0:
                return {
                    "1x": (0.0, 0.0),
                    "2x": (0.0, 0.0),
                    "3x": (0.0, 0.0)
                }

            # Frekuensi putaran mesin
            one_x = rpm / 60.0

            results = {}

            # Cari peak 1X, 2X, dan 3X
            for harmonic in [1, 2, 3]:

                # Frekuensi teoritis harmonik
                target_frequency = one_x * harmonic

                # Area pencarian peak
                mask = (
                    (frequency >= target_frequency - bandwidth)
                    &
                    (frequency <= target_frequency + bandwidth)
                )

                # Jika tidak ada data di sekitar frekuensi target
                if not np.any(mask):

                    results[f"{harmonic}x"] = (
                        target_frequency,
                        0.0
                    )

                    continue

                # Ambil data pada area tersebut
                local_frequency = frequency[mask]

                local_amplitude = amplitude[mask]

                # Cari amplitudo terbesar
                peak_index = np.argmax(
                    local_amplitude
                )

                peak_frequency = float(
                    local_frequency[peak_index]
                )

                peak_amplitude = float(
                    local_amplitude[peak_index]
                )

                # Simpan hasil
                results[f"{harmonic}x"] = (
                    peak_frequency,
                    peak_amplitude
                )

            return results

        # =================================================
        # PEAK 1X, 2X, 3X SUMBU X
        # =================================================

        harmonic_x = get_harmonic_peaks(
            frequency_x,
            amplitude_x,
            rpm,
            bandwidth=1.0
        )

        freq_1x_x, amp_1x_x = harmonic_x["1x"]
        freq_2x_x, amp_2x_x = harmonic_x["2x"]
        freq_3x_x, amp_3x_x = harmonic_x["3x"]


        # =================================================
        # PEAK 1X, 2X, 3X SUMBU Y
        # =================================================

        harmonic_y = get_harmonic_peaks(
            frequency_y,
            amplitude_y,
            rpm,
            bandwidth=1.0
        )

        freq_1x_y, amp_1x_y = harmonic_y["1x"]
        freq_2x_y, amp_2x_y = harmonic_y["2x"]
        freq_3x_y, amp_3x_y = harmonic_y["3x"]


        # =================================================
        # PEAK 1X, 2X, 3X SUMBU Z
        # =================================================

        harmonic_z = get_harmonic_peaks(
            frequency_z,
            amplitude_z,
            rpm,
            bandwidth=1.0
        )

        freq_1x_z, amp_1x_z = harmonic_z["1x"]
        freq_2x_z, amp_2x_z = harmonic_z["2x"]
        freq_3x_z, amp_3x_z = harmonic_z["3x"]

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
        # PEAK HARMONIK SUMBU X
        # =================================================

        st.subheader("Harmonik Sumbu X")

        x1, x2, x3 = st.columns(3)

        with x1:
            st.metric(
                "Peak 1× X",
                f"{freq_1x_x:.2f} Hz",
                f"Amplitudo: {amp_1x_x:.2f}"
            )

        with x2:
            st.metric(
                "Peak 2× X",
                f"{freq_2x_x:.2f} Hz",
                f"Amplitudo: {amp_2x_x:.2f}"
            )

        with x3:
            st.metric(
                "Peak 3× X",
                f"{freq_3x_x:.2f} Hz",
                f"Amplitudo: {amp_3x_x:.2f}"
            )


        # =================================================
        # PEAK HARMONIK SUMBU Y
        # =================================================

        st.subheader("Harmonik Sumbu Y")

        y1, y2, y3 = st.columns(3)

        with y1:
            st.metric(
                "Peak 1× Y",
                f"{freq_1x_y:.2f} Hz",
                f"Amplitudo: {amp_1x_y:.2f}"
            )

        with y2:
            st.metric(
                "Peak 2× Y",
                f"{freq_2x_y:.2f} Hz",
                f"Amplitudo: {amp_2x_y:.2f}"
            )

        with y3:
            st.metric(
                "Peak 3× Y",
                f"{freq_3x_y:.2f} Hz",
                f"Amplitudo: {amp_3x_y:.2f}"
            )


        # =================================================
        # PEAK HARMONIK SUMBU Z
        # =================================================

        st.subheader("Harmonik Sumbu Z")

        z1, z2, z3 = st.columns(3)

        with z1:
            st.metric(
                "Peak 1× Z",
                f"{freq_1x_z:.2f} Hz",
                f"Amplitudo: {amp_1x_z:.2f}"
            )

        with z2:
            st.metric(
                "Peak 2× Z",
                f"{freq_2x_z:.2f} Hz",
                f"Amplitudo: {amp_2x_z:.2f}"
            )

        with z3:
            st.metric(
                "Peak 3× Z",
                f"{freq_3x_z:.2f} Hz",
                f"Amplitudo: {amp_3x_z:.2f}"
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

        fig_fft_x = add_harmonic_markers(
            fig_fft_x,
            one_x_frequency,
            two_x_frequency,
            three_x_frequency
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

        fig_fft_y = add_harmonic_markers(
            fig_fft_y,
            one_x_frequency,
            two_x_frequency,
            three_x_frequency
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

        fig_fft_z = add_harmonic_markers(
            fig_fft_z,
            one_x_frequency,
            two_x_frequency,
            three_x_frequency
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