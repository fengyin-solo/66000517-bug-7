import math
import random
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="RF Signal Analyzer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MODULATION_TYPES = ["AM", "FM", "BPSK", "QPSK", "16QAM"]


class GenerateRequest(BaseModel):
    modulation: str = "QPSK"
    samples: int = 1024
    snr: float = 20.0


def generate_signal(mod: str, samples: int, snr: float) -> tuple:
    """Generate IQ samples for given modulation"""
    t = np.arange(samples) / samples * 10  # time vector
    i, q = np.zeros(samples), np.zeros(samples)
    noise_scale = 10 ** (-snr / 20) * 0.5

    if mod == "AM":
        i = 0.7 * (1 + 0.5 * np.sin(2 * np.pi * 1.5 * t)) * np.cos(2 * np.pi * 5 * t)
        q = np.zeros(samples)
    elif mod == "FM":
        msg = np.sin(2 * np.pi * 1.2 * t)
        phase = np.cumsum(2 * np.pi * (5 + 3 * msg) / samples * 10)
        i = np.cos(phase) * 0.7
        q = np.sin(phase) * 0.7
    elif mod == "BPSK":
        symbols = np.sign(np.random.randn(samples // 16 + 1))
        symbols_upsampled = np.repeat(symbols, 16)[:samples]
        i = symbols_upsampled * np.cos(2 * np.pi * 5 * t) * 0.7
        q = np.zeros(samples)
    elif mod == "QPSK":
        sym_i = np.sign(np.random.randn(samples // 16 + 1))
        sym_q = np.sign(np.random.randn(samples // 16 + 1))
        si = np.repeat(sym_i, 16)[:samples]
        sq = np.repeat(sym_q, 16)[:samples]
        i = si * 0.5
        q = sq * 0.5
    elif mod == "16QAM":
        levels = np.array([-3, -1, 1, 3]) * 0.25
        sym_i = np.random.choice(levels, samples // 16 + 1)
        sym_q = np.random.choice(levels, samples // 16 + 1)
        i = np.repeat(sym_i, 16)[:samples]
        q = np.repeat(sym_q, 16)[:samples]
    else:
        i = np.cos(2 * np.pi * 5 * t) * 0.7
        q = np.sin(2 * np.pi * 5 * t) * 0.7

    # Add noise
    i += np.random.randn(samples) * noise_scale
    q += np.random.randn(samples) * noise_scale

    return i, q


def compute_fft(i: np.ndarray, q: np.ndarray, fs: float = 1000.0):
    """Compute FFT magnitude spectrum in dB"""
    iq = i + 1j * q
    n = len(iq)
    fft = np.fft.fftshift(np.fft.fft(iq))
    mag = np.abs(fft) / n
    mag_db = 20 * np.log10(mag + 1e-10)
    freqs = np.fft.fftshift(np.fft.fftfreq(n, 1/fs))
    return freqs.tolist(), mag_db.tolist()


def compute_waterfall(i: np.ndarray, q: np.ndarray, fs: float = 1000.0, rows: int = 40, min_seg: int = 16):
    """Compute spectrogram waterfall.

    Segment length adapts to the signal length so short signals still yield
    a usable waterfall. Returns [] only when there are fewer than min_seg
    samples, in which case a waterfall genuinely cannot be computed.
    Each row holds the full fftshifted magnitude (same frequency range as
    the spectrum endpoint) so the panels stay consistent.
    """
    n = len(i)
    if n < min_seg:
        return []
    seg = max(min_seg, n // rows)
    n_rows = min(rows, n // seg)
    waterfall = []
    for r in range(n_rows):
        seg_i = i[r * seg:(r + 1) * seg]
        seg_q = q[r * seg:(r + 1) * seg]
        fft = np.fft.fftshift(np.fft.fft(seg_i + 1j * seg_q))
        mag_db = 20 * np.log10(np.abs(fft) / len(seg_i) + 1e-10)
        waterfall.append({
            "time": r * seg / fs,
            "values": mag_db.tolist()
        })
    return waterfall


def classify_modulation(i: np.ndarray, q: np.ndarray) -> dict:
    """Simple modulation classification based on features"""
    iq = i + 1j * q
    amp = np.abs(iq)
    phase = np.angle(iq)

    scores = {}
    amp_var = np.var(amp) / (np.mean(np.abs(amp)) + 1e-5)
    phase_var = np.var(phase)

    # AM: high amplitude variation, low phase variation
    scores["AM"] = min(1.0, amp_var * 3) * (1 - min(0.5, phase_var / 5))
    # FM: low amplitude variation, high phase variation
    scores["FM"] = (1 - min(0.8, amp_var * 2)) * min(1.0, phase_var / 5 * 3)
    # BPSK: moderate amplitude
    scores["BPSK"] = 0.5 + 0.3 * np.abs(amp_var - 0.5)
    # QPSK
    scores["QPSK"] = 0.6 + 0.2 * (1 - amp_var)
    # 16QAM: higher amplitude variation than QPSK
    scores["16QAM"] = 0.5 + 0.4 * amp_var

    # Normalize
    total = sum(scores.values()) or 1
    scores = {k: v / total for k, v in scores.items()}

    best = max(scores, key=scores.get)
    candidates = sorted([{"type": k, "score": round(v, 3)} for k, v in scores.items()], key=lambda x: x["score"], reverse=True)

    return {
        "type": best,
        "confidence": round(scores[best], 3),
        "candidates": candidates,
        "symbolRate": 1000 / 16 if best in ("BPSK", "QPSK", "16QAM") else None,
        "frequencyOffset": round(random.uniform(-5, 5), 2)
    }


@app.post("/api/generate")
def generate_and_analyze(req: GenerateRequest):
    if req.modulation not in MODULATION_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的调制方式: {req.modulation}，可选: {MODULATION_TYPES}")
    if not 16 <= req.samples <= 65536:
        raise HTTPException(status_code=400, detail="样本数需在 16 ~ 65536 之间")
    if not -20 <= req.snr <= 80:
        raise HTTPException(status_code=400, detail="SNR 需在 -20 ~ 80 dB 之间")

    i, q = generate_signal(req.modulation, req.samples, req.snr)
    freqs, mags = compute_fft(i, q)
    waterfall = compute_waterfall(i, q)
    modulation = classify_modulation(i, q)

    n = len(i)
    step = max(1, n // 200)
    constellation = [{"i": float(i[k]), "q": float(q[k])} for k in range(0, n, step)]

    return {
        "spectrum": {"frequencies": freqs, "magnitudes": mags},
        "waterfall": waterfall,
        "constellation": constellation,
        "modulation": modulation
    }