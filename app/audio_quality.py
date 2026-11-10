"""How clean is a recording? Cheap signal-level features from the WAV bytes.

Frame energies (25 ms windows, 10 ms hop) are split into the quiet floor (background
noise between words) and the loud top (speech). Their ratio is a blind SNR estimate:
it needs no clean reference, so it works on live microphone audio.
"""
import io
import wave

import numpy as np


def read_wav(b: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(b)) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError("expected 16-bit PCM")
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def features(x: np.ndarray, sr: int) -> dict:
    win, hop = int(0.025 * sr), int(0.010 * sr)
    if len(x) < win * 4:
        return {"snr_db": 0.0, "floor_db": -90.0, "dynamic_db": 0.0, "speech_frac": 0.0, "duration_s": len(x) / sr}
    n = 1 + (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    e = np.mean(x[idx] ** 2, axis=1) + 1e-10
    db = 10 * np.log10(e)
    # Ignore digital silence (padding, or gaps gated out by browser noise suppression):
    # it is not the room's background noise and would make any recording look clean.
    live = db[db > -75]
    if len(live) >= 10:
        db = live
    floor, top = np.percentile(db, 10), np.percentile(db, 95)
    speech_frac = float(np.mean(db > floor + 0.5 * (top - floor)))
    # blind SNR: speech power over noise power, both from the frame-energy distribution
    snr = 10 * np.log10(max(10 ** (top / 10) - 10 ** (floor / 10), 1e-10) / 10 ** (floor / 10))
    return {"snr_db": round(float(snr), 2), "floor_db": round(float(floor), 2),
            "dynamic_db": round(float(top - floor), 2), "speech_frac": round(speech_frac, 3),
            "duration_s": round(len(x) / sr, 2)}


def from_wav(b: bytes) -> dict | None:
    try:
        return features(*read_wav(b))
    except Exception:
        return None


def pad_wav(b: bytes, lead_s: float = 0.4, tail_s: float = 0.2) -> bytes:
    """Add silence before/after speech. Prisma tends to drop the first word when speech starts at
    the very first sample (found on real recordings: names like ਬਿੱਟੂ / ਮਾਸਟਰ ਜੀ were lost).
    Non-WAV input is returned unchanged."""
    try:
        with wave.open(io.BytesIO(b)) as w:
            params, frames = w.getparams(), w.readframes(w.getnframes())
        silence = b"\x00" * params.sampwidth * params.nchannels
        out = io.BytesIO()
        with wave.open(out, "wb") as w:
            w.setparams(params)
            w.writeframes(silence * int(lead_s * params.framerate) + frames + silence * int(tail_s * params.framerate))
        return out.getvalue()
    except Exception:
        return b
