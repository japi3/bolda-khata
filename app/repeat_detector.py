"""Runtime side of the "did I hear that right?" detector (trained by scripts/train_repeat_detector.py).

Combines the recording's audio quality with the language model's confidence and returns the
probability that a ledger write would be wrong. Above the threshold the app reads back what
it heard and asks for a one-tap confirmation before writing.
"""
import joblib

from . import config

_bundle = None
LOUD_SNR_DB = 12.0   # below this blind-SNR estimate, also suggest holding the phone closer


def _load():
    global _bundle
    if _bundle is None:
        path = config.MODEL_DIR / "repeat_detector.joblib"
        _bundle = joblib.load(path) if path.exists() else False
    return _bundle


def assess(analysis: dict, transcript: str, audio: dict | None) -> dict | None:
    """analysis = NLU .analyse() output; audio = app.audio_quality features (None for typed text)."""
    b = _load()
    if not b or not audio or not analysis.get("proba"):
        return None
    p = sorted(analysis["proba"].values(), reverse=True)
    f = {**audio, "conf": p[0], "margin": p[0] - p[1], "tag_conf": analysis.get("tag_confidence", 1.0),
         "chars_per_s": len(transcript.replace(" ", "")) / max(audio.get("duration_s", 1.0), 0.5)}
    prob = float(b["model"].predict_proba([[f[k] for k in b["features"]]])[0, 1])
    noisy = (audio.get("snr_db") or 99) < LOUD_SNR_DB
    # Loud recordings only: in normal or busy-shop audio the remaining mistakes are confidently
    # misheard numbers the detector can't catch, so asking there only costs the shopkeeper taps.
    return {"p_wrong": round(prob, 3), "unsure": noisy and prob > b["threshold"], "threshold": round(b["threshold"], 3),
            "snr_db": audio.get("snr_db"), "noisy": noisy}
