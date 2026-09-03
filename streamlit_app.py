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
            .select("id,TIME,RPM,AccRMS,STATUS")
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
df["AccRMS"] = pd.to_numeric(
    df["AccRMS"],
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

acceleration_rms = float(latest["AccRMS"])

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
    # Velocity RMS
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
            {velocity_rms:.2f} mm/s²
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
# FFT ANALYSIS
# =========================================================

st.header("📊 Analisis FFT Getaran")

if fft_latest is None:

    st.warning(
        "Belum ada data FFT dari PLC."
    )

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

    fft_data = fft_latest["data"]

    # -----------------------------------------------------
    # Pastikan data berupa list
    # -----------------------------------------------------

    if isinstance(fft_data, str):

        import json

        fft_data = json.loads(
            fft_data
        )

    fft_data = np.array(
        fft_data,
        dtype=float
    )

    # =====================================================
    # KONVERSI D110 → PERCEPATAN
    # =====================================================

    # D110 × 12.387 = mm/s²
    fft_data_acc = fft_data * 0.012387

    # =====================================================
    # VALIDASI
    # =====================================================

    if len(fft_data) != sample_count:

        st.error(
            f"Jumlah data FFT tidak sesuai. "
            f"Expected: {sample_count}, "
            f"Received: {len(fft_data)}"
        )

    else:

        # =================================================
        # HITUNG FFT
        # =================================================

        frequency, amplitude = calculate_fft(
            fft_data_acc,
            sampling_frequency
        )

        # BUAT FIGURE FFT
        fig_fft = go.Figure()

        # =================================================
        # FREKUENSI DOMINAN
        # =================================================
        if len(amplitude) > 1:

            # Abaikan DC / 0 Hz
            dominant_index = (
                np.argmax(
                    amplitude[1:]
            ) + 1
            )

            dominant_frequency = (
                frequency[dominant_index]
            )

            dominant_amplitude = (
                amplitude[dominant_index]
            )

        else:

            dominant_frequency = 0
            dominant_amplitude = 0

        # =================================================
        # FREKUENSI 1X, 2X, 3X RPM
        # =================================================

        rpm_frequency = rpm / 60.0

        one_x_frequency = rpm_frequency
        two_x_frequency = rpm_frequency * 2
        three_x_frequency = rpm_frequency * 3

        # =================================================
        # FUNGSI MENCARI PEAK
        # =================================================

        def get_harmonic_amplitude(
            target_frequency,
            frequency,
            amplitude,
            bandwidth=1.0
        ):

            if target_frequency <= 0:
                return 0.0, 0.0

            # Cari semua titik FFT di sekitar
            # target frequency ± bandwidth

            mask = (
                np.abs(
                    frequency - target_frequency
                )
                <= bandwidth
            )

            if not np.any(mask):
                return 0.0, 0.0

            local_indices = np.where(mask)[0]

            # Cari peak terbesar di sekitar
            local_index = (
                local_indices[
                    np.argmax(
                        amplitude[local_indices]
                    )
                ]
            )

            return (
                frequency[local_index],
                amplitude[local_index]
            )

        # =================================================
        # PEAK 1X
        # =================================================

        one_x_actual_frequency, one_x_amplitude = (
            get_harmonic_amplitude(
                one_x_frequency,
                frequency,
                amplitude
            )
        )

        # =========================================================
        # Velocity RMS
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
                {velocity_rms:.2f} mm/s²
                </h1>

                <h2>
                Status: {status}
                </h2>

                </div>
                """,
                unsafe_allow_html=True
            )


        # =================================================
        # PEAK 2X
        # =================================================

        two_x_actual_frequency, two_x_amplitude = (
            get_harmonic_amplitude(
                two_x_frequency,
                frequency,
                amplitude
            )
        )

        # =====================================================
        # HITUNG VELOCITY RMS DARI ACCELERATION RMS
        # =====================================================

        if one_x_actual_frequency > 0:

            velocity_rms_mms = (
                acceleration_rms
                / (2 * np.pi * one_x_actual_frequency)
            )

        else:

            velocity_rms_mms = 0.0

        # =========================================================
        # Velocity RMS
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
                {velocity_rms:.2f} mm/s²
                </h1>

                <h2>
                Status: {status}
                </h2>

                </div>
                """,
                unsafe_allow_html=True
            )


        # =================================================
        # PEAK 3X
        # =================================================

        three_x_actual_frequency, three_x_amplitude = (
            get_harmonic_amplitude(
                three_x_frequency,
                frequency,
                amplitude
            )
        )
        # =================================================
        # KPI FFT
        # =================================================

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
            f"{sampling_frequency / sample_count:.2f} Hz"
        )

        with c4:

            st.metric(
            "RPM",
            f"{rpm:.0f}"
        )


        # =================================================
        # HARMONIK RPM
        # =================================================

        h1, h2, h3 = st.columns(3)

        with h1:

            st.metric(
                "1× RPM",
                f"{one_x_frequency:.2f} Hz",
                f"Peak = {one_x_actual_frequency:.2f}Hz | "
                f"Amp = {one_x_amplitude:.2f}"
            )

        with h2:

            st.metric(
                "2× RPM",
                f"{two_x_frequency:.2f} Hz",
                f"Peak = {two_x_actual_frequency:.2f}Hz | "
                f"Amp = {two_x_amplitude:.2f}"
            )

        with h3:

            st.metric(
                "3× RPM",
                f"{three_x_frequency:.2f} Hz",
                f"Peak = {three_x_actual_frequency:.2f}Hz | "
                f"Amp = {three_x_amplitude:.2f}"
            )
        # =================================================
        # GRAFIK FFT
        # =================================================

        df_fft = pd.DataFrame({

            "Frequency": frequency,

            "Acceleration": amplitude

        })
        
        # -------------------------------------------------
        # Batasi sampai Nyquist
        # -------------------------------------------------

        nyquist = (
            sampling_frequency / 2
        )

        df_fft = df_fft[
            df_fft["Frequency"] <= nyquist
        ]

        # -------------------------------------------------
        # Grafik
        # -------------------------------------------------

        fig_fft = go.Figure()

        fig_fft.add_trace(

            go.Scatter(

                x=df_fft["Frequency"],

                y=df_fft["Acceleration"],

                mode="lines",

                name="Acceleration FFT"

            )

        )

        # -------------------------------------------------
        # Garis 1x RPM
        # -------------------------------------------------

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
                    "size": 12
                },
                name="peak 1x"
                )
            )
            # -------------------------------------------------
            # Garis 2× RPM
            # -------------------------------------------------

            if(
                two_x_frequency > 0 
                and two_x_frequency <= nyquist
            ):
                fig_fft.add_trace(
                    go.Scatter(
                        x=[two_x_actual_frequency],
                        y=[two_x_amplitude],
                        mode="markers",
                        marker={
                            "size": 12
                        },
                        name="Peak 2x"
                    )
                )
            # -------------------------------------------------
            # Garis 3× RPM
            # -------------------------------------------------

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
                            "size": 12
                        },
                        name="Peak 3x"
                    )
                )

            # =================================================
            # GARIS 1X RPM
            # =================================================

            if one_x_frequency > 0:

                fig_fft.add_vline(

                    x=one_x_frequency,

                    line_dash="dash",

                    annotation_text=(
                        f"1× = {one_x_frequency:.2f} Hz"
                    ),

                    annotation_position="top"

                )


            # =================================================
            # GARIS 2X RPM
            # =================================================

            if (
                two_x_frequency > 0
                and two_x_frequency <= nyquist
            ):

                fig_fft.add_vline(

                x=two_x_frequency,

                line_dash="dash",

                annotation_text=(
                    f"2× = {two_x_frequency:.2f} Hz"
                ),

                annotation_position="top"

        )


            # =================================================
            # GARIS 3X RPM
            # =================================================

            if (
                three_x_frequency > 0
                and three_x_frequency <= nyquist
            ):

                fig_fft.add_vline(

                    x=three_x_frequency,

                    line_dash="dash",

                    annotation_text=(
                        f"3× = {three_x_frequency:.2f} Hz"
                ),

                annotation_position="top"

            )             

    
        # -------------------------------------------------
        # Tandai frekuensi dominan
        # -------------------------------------------------

        fig_fft.add_trace(

            go.Scatter(

                x=[
                    dominant_frequency
                ],

                y=[
                    dominant_amplitude
                ],

                mode="markers",

                marker={
                    "size": 12
                },

                name="Dominant Frequency"

            )

        )

        fig_fft.update_layout(

            title=(
                "Frequency Spectrum "
                "(FFT)"
            ),

            xaxis_title=(
                "Frequency (Hz)"
            ),

            yaxis_title=(
                "Acceleration Amplitude (mm/s²)"
            ),

            xaxis=dict(
                range=[
                    0,
                    nyquist
                ]
            ),

            hovermode="x unified"

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
                "500 Sampel Data Getaran "
            )

        )

        fig_raw.update_layout(

            xaxis_title=(
                "Time (s)"
            ),

            yaxis_title=(
                "Acceleration (mm/s²)"
            )

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
            f"Resolusi frekuensi: "
            f"{sampling_frequency / sample_count:.2f} Hz"

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
        y="AccRMS",
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
        yaxis_title="AccRMS (mm/s²)"
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