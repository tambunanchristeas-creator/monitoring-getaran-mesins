import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
import json
from streamlit_autorefresh import st_autorefresh
from scipy import signal as sp_signal


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
# PENGATURAN FILTER (SIDEBAR)
# =========================================================
st.sidebar.header("🎛️ Pengaturan Filter")

filter_type = st.sidebar.selectbox(
    "Jenis filter",
    ["Tanpa Filter", "High-Pass", "Low-Pass", "Band-Pass"],
    index=1
)

filter_order = st.sidebar.slider("Orde filter", 1, 8, 4)

f_low = 2.0
f_high = 100.0

if filter_type == "High-Pass":
    f_low = st.sidebar.number_input(
        "Cutoff High-Pass (Hz)", 0.1, 1000.0, 2.0, step=0.5
    )

elif filter_type == "Low-Pass":
    f_high = st.sidebar.number_input(
        "Cutoff Low-Pass (Hz)", 1.0, 2000.0, 100.0, step=5.0
    )

elif filter_type == "Band-Pass":
    f_low = st.sidebar.number_input(
        "Frekuensi bawah (Hz)", 0.1, 1000.0, 2.0, step=0.5
    )
    f_high = st.sidebar.number_input(
        "Frekuensi atas (Hz)", 1.0, 2000.0, 100.0, step=5.0
    )


# ---- Pengaturan sumbu Y grafik FFT (m/s2) ----
st.sidebar.header("📈 Grafik FFT")

fft_y_auto = st.sidebar.checkbox(
    "Batas Y otomatis",
    value=False,
    key="fft_y_auto"
)

fft_y_manual = st.sidebar.number_input(
    "Batas maksimal sumbu Y FFT (m/s²)",
    min_value=0.001,
    max_value=1000.0,
    value=1.0,
    step=0.1,
    format="%.3f",
    disabled=fft_y_auto,
    key="fft_y_manual"
)


# ---- Perataan spektrum (beberapa rekaman FFT) ----
st.sidebar.header("📉 Perataan Spektrum")

fft_avg_n = st.sidebar.slider(
    "Jumlah rekaman FFT yang dirata-ratakan",
    min_value=1,
    max_value=20,
    value=1,
    help=(
        "1 = FFT tunggal (tanpa perataan). Nilai lebih besar merata-ratakan "
        "daya spektrum dari beberapa rekaman FFT terbaru agar puncak noise "
        "acak mengecil, sedangkan harmonik 1x, 2x, 3x yang stabil tetap. "
        "Pakai hanya saat RPM konstan."
    ),
    key="fft_avg_n"
)


def apply_filter(data, fs, ftype, order, low, high):
    """Butterworth zero-phase filter. Jika setting tidak valid,
    sinyal dikembalikan tanpa difilter."""

    x = np.asarray(data, dtype=float)

    if ftype == "Tanpa Filter" or len(x) < 16 or fs <= 0:
        return x

    nyq = fs / 2.0

    if ftype == "High-Pass":
        wn, btype = low / nyq, "highpass"

    elif ftype == "Low-Pass":
        wn, btype = high / nyq, "lowpass"

    elif ftype == "Band-Pass":
        if low >= high:
            return x
        wn, btype = [low / nyq, high / nyq], "bandpass"

    else:
        return x

    # Cutoff harus berada di antara 0 dan Nyquist
    if np.any(np.asarray(wn) <= 0) or np.any(np.asarray(wn) >= 1):
        return x

    try:
        sos = sp_signal.butter(order, wn, btype=btype, output="sos")
        return sp_signal.sosfiltfilt(sos, x)
    except Exception:
        return x

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


def load_fft_latest_id():
    """Query ringan: hanya id FFT terbaru (tanpa data_x/y/z)."""
    try:
        res = (
            supabase.table("FFT")
            .select("id")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return res.data[0]["id"]
    except Exception:
        return None



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

def calculate_fft(data, sampling_frequency):
    signal = np.asarray(data, dtype=float)
    N = len(signal)

    if N < 4:
        return None, None

    # 1. Hilangkan DC offset
    signal = signal - np.mean(signal)

    # 2. FILTER (sesuai pilihan di sidebar)
    filtered = apply_filter(
        signal,
        sampling_frequency,
        filter_type,
        filter_order,
        f_low,
        f_high
    )

    # 3. Hanning window
    window = np.hanning(N)
    signal_windowed = filtered * window

    # 4. FFT
    fft_result = np.fft.rfft(signal_windowed)
    frequency = np.fft.rfftfreq(N, d=1.0 / sampling_frequency)

    # 5. Amplitudo
    amplitude = (2.0 / np.sum(window)) * np.abs(fft_result)
    amplitude[0] = 0.0

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
            l=40,
            r=80,
            t=70,
            b=40
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

        y0=0.20,
        y1=0.18,

        fillcolor="#4C9F38",

        line=dict(
            color="#4C9F38",
            width=1
        )
    )


    fig_gauge.add_annotation(

        x=0.485,
        y=0.19,

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
        Velocity RMS
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
                Velocity RMS Radial (X)
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
                Velocity RMS Axial (Y)
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
                Velocity RMS Radial (Z)
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
                Acceleration Radial (X)
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="acc-number">
                {acceleration_rms_x:.2f}
                <span>m/s²</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    with ay:

        st.markdown(
            """
            <div class="value-label">
                Acceleration Axial (Y)
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="acc-number">
                {acceleration_rms_y:.2f}
                <span>m/s²</span>
            </div>
            """,

            unsafe_allow_html=True
        )


    with az:

        st.markdown(
            """
            <div class="value-label">
                Acceleration Radial (Z)
            </div>
            """,

            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="acc-number">
                {acceleration_rms_z:.2f}
                <span>m/s²</span>
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
# Data FFT hanya diambil & digambar ulang ketika ESP32 mengirim
# data FFT baru (id berubah) atau pengaturan sidebar diubah.
# Selain itu, grafik dipakai ulang dari session_state sehingga
# tidak ikut refresh 1 detik bersama halaman.

BLUE = "#9BC2F9"
GRID = "#5E5C5C"
TXT = "#ffffff"


def style_fig(fig, title, xlabel, ylabel):
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            x=0.0, xanchor="left",
            font=dict(size=13, color="#ffffff")
        ),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        height=330,
        margin=dict(l=55, r=15, t=50, b=50),
        paper_bgcolor="#12151b",
        plot_bgcolor="#12151b",
        showlegend=False,
        hovermode="x unified",
        font=dict(size=10, color=TXT),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, ticks="")
    fig.update_yaxes(
        showgrid=True, gridcolor=GRID, gridwidth=1,
        zeroline=False, showline=False, ticks=""
    )
    return fig


def parse_fft_record(rec):
    """Satu baris tabel FFT -> (acc [x, y, z] dalam m/s2, fs, n_fft, sample_count)."""

    sample_count = int(rec["sample_count"])
    sampling_frequency = float(rec["sampling_frequency"])

    raw = []
    for key in ("data_x", "data_y", "data_z"):
        d = rec[key]
        if isinstance(d, str):
            d = json.loads(d)
        raw.append(np.asarray(d, dtype=float))

    # Data PLC dalam mm/s2 -> dijadikan m/s2
    FFT_SCALE = 0.001
    acc = [r * FFT_SCALE for r in raw]

    n_fft = min(len(a) for a in acc)
    if sample_count >= 4:
        n_fft = min(n_fft, sample_count)
    acc = [a[:n_fft] for a in acc]

    return acc, sampling_frequency, n_fft, sample_count


def build_fft_view(records):
    """Hitung FFT + buat semua figure. records[0] = rekaman FFT terbaru.

    Jika ada lebih dari satu rekaman, spektrum dirata-ratakan (daya rata-rata,
    lalu diakarkan) pada sumbu frekuensi rekaman terbaru. Grafik domain waktu
    tetap dari rekaman terbaru."""

    fft_latest = records[0]
    fft_id = fft_latest["id"]
    fft_time = fft_latest["created_at"]

    acc, sampling_frequency, n_fft, sample_count = parse_fft_record(fft_latest)

    if n_fft < 4:
        return {"error": f"Data FFT terlalu sedikit ({n_fft} titik)."}
    if sampling_frequency <= 0:
        return {"error": "Sampling frequency harus lebih besar dari 0 Hz."}

    nyquist = sampling_frequency / 2
    resolution_fft = sampling_frequency / n_fft

    try:
        ts = pd.to_datetime(fft_time).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        ts = str(fft_time)

    # FFT X, Y, Z rekaman terbaru (dibatasi sampai Nyquist)
    spectra = []
    for a in acc:
        f, amp = calculate_fft(a, sampling_frequency)
        m = f <= nyquist
        spectra.append((f[m], amp[m]))

    # Perataan dengan rekaman FFT sebelumnya (jika diminta)
    n_used = 1
    if len(records) > 1:
        f_ref = [s[0] for s in spectra]
        p_stack = [[s[1] ** 2] for s in spectra]

        for rec in records[1:]:
            try:
                acc_r, fs_r, n_r, _ = parse_fft_record(rec)
                if n_r < 4 or fs_r <= 0:
                    continue
                p_rec = []
                for i, a in enumerate(acc_r):
                    f_r, amp_r = calculate_fft(a, fs_r)
                    p_rec.append(
                        np.interp(f_ref[i], f_r, amp_r ** 2,
                                  left=np.nan, right=np.nan)
                    )
            except Exception:
                continue
            for i in range(3):
                p_stack[i].append(p_rec[i])
            n_used += 1

        spectra = [
            (f_ref[i], np.sqrt(np.nanmean(np.vstack(p_stack[i]), axis=0)))
            for i in range(3)
        ]

    # Sinyal domain waktu (rekaman terbaru): buang DC offset
    waktu = np.arange(n_fft) / sampling_frequency
    signals = [
        apply_filter(
            a - np.mean(a), sampling_frequency,
            filter_type, filter_order, f_low, f_high
        )
        for a in acc
    ]

    fft_y_max = 1.1 * max(float(np.max(s[1])) for s in spectra)
    y_top = max(fft_y_max, 0.001) if fft_y_auto else fft_y_manual

    sumbu = [("X", "Radial"), ("Y", "Axial"), ("Z", "Radial")]

    figs_time, figs_fft = [], []
    for (nama, arah), sig, (f, amp) in zip(sumbu, signals, spectra):

        ft = go.Figure(go.Scatter(
            x=waktu, y=sig, mode="lines",
            line=dict(color=BLUE, width=0.8)
        ))
        ft = style_fig(
            ft, f"Domain Waktu {nama} ({arah}) {ts}",
            "Waktu (detik)", "Amplitudo (m/s²)"
        )
        ft.update_xaxes(range=[0, waktu[-1]])
        figs_time.append(ft)

        judul_fft = f"Domain Frekuensi {nama} ({arah}) {ts}"
        if n_used > 1:
            judul_fft += f" (rata-rata {n_used} rekaman)"

        ff = go.Figure(go.Scatter(
            x=f, y=amp, mode="lines",
            line=dict(color=BLUE, width=1)
        ))
        ff = style_fig(
            ff, judul_fft,
            "Frekuensi (Hz)", "Magnitudo (m/s²)"
        )
        ff.update_xaxes(range=[0, nyquist], tick0=0, dtick=10)
        ff.update_yaxes(range=[0, y_top], autorange=False, fixedrange=True)
        figs_fft.append(ff)

    caption = (
        f"FFT ID: {fft_id} | Data diterima: {fft_time} | "
        f"Titik data FFT: {n_fft} | "
        f"Resolusi frekuensi: {resolution_fft:.2f} Hz"
    )
    if n_used > 1:
        caption += (
            f" | Spektrum = rata-rata {n_used} rekaman FFT terbaru "
            f"(domain waktu: rekaman terbaru)"
        )

    return {
        "error": None,
        "sample_count": sample_count,
        "sampling_frequency": sampling_frequency,
        "resolution_fft": resolution_fft,
        "nyquist": nyquist,
        "n_avg": n_used,
        "figs_time": figs_time,
        "figs_fft": figs_fft,
        "caption": caption,
    }


# ---- Ambil data hanya jika ada FFT baru atau jumlah perataan diubah ----
def load_fft_records(n):
    """n baris FFT terbaru (terbaru dulu)."""
    try:
        res = (
            supabase.table("FFT")
            .select(
                "id,created_at,sample_count,sampling_frequency,data_x,data_y,data_z"
            )
            .order("id", desc=True)
            .limit(int(n))
            .execute()
        )
        return res.data or []
    except Exception as e:
        st.error("Gagal mengambil data FFT dari Supabase.")
        st.code(str(e))
        return []


latest_fft_id = load_fft_latest_id()

if (
    latest_fft_id is not None
    and (
        "fft_raw" not in st.session_state
        or st.session_state.get("fft_raw_id") != latest_fft_id
        or st.session_state.get("fft_raw_n") != fft_avg_n
    )
):
    new_records = load_fft_records(fft_avg_n)
    if new_records:
        st.session_state.fft_raw = new_records
        st.session_state.fft_raw_id = new_records[0]["id"]
        st.session_state.fft_raw_n = fft_avg_n

fft_latest = st.session_state.get("fft_raw")
if isinstance(fft_latest, dict):          # sisa session lama (1 baris)
    fft_latest = [fft_latest]

# ---- Bangun ulang grafik hanya jika data/pengaturan berubah ----
if fft_latest:
    fft_sig = (
        fft_latest[0]["id"], len(fft_latest), filter_type, filter_order,
        f_low, f_high, fft_y_auto, fft_y_manual
    )
    if st.session_state.get("fft_sig") != fft_sig:
        try:
            st.session_state.fft_view = build_fft_view(fft_latest)
        except Exception as e:
            st.session_state.fft_view = {"error": f"Gagal memproses FFT: {e}"}
        st.session_state.fft_sig = fft_sig

st.header("📊 Analisis FFT Getaran")

view = st.session_state.get("fft_view")

if not fft_latest or view is None:

    st.warning("Belum ada data FFT dari PLC.")

elif view["error"]:

    st.error(view["error"])

else:

    PLOT_CFG = {"displayModeBar": False}

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Jumlah Sampel", view["sample_count"])
    c2.metric("Sampling", f"{view['sampling_frequency']:.0f} Hz")
    c3.metric("Resolusi FFT", f"{view['resolution_fft']:.2f} Hz")
    c4.metric("Nyquist", f"{view['nyquist']:.1f} Hz")
    c5.metric("Rekaman dirata-ratakan", view["n_avg"])

    cols = st.columns(3)
    for col, fig, k in zip(cols, view["figs_time"], "xyz"):
        with col:
            st.plotly_chart(
                fig, use_container_width=True, theme=None,
                config=PLOT_CFG, key=f"time_{k}"
            )

    cols = st.columns(3)
    for col, fig, k in zip(cols, view["figs_fft"], "xyz"):
        with col:
            st.plotly_chart(
                fig, use_container_width=True, theme=None,
                config=PLOT_CFG, key=f"fft_{k}"
            )

    st.caption(view["caption"])

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