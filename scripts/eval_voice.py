"""Voice evaluation on the hard set, clean and in a noisy shop.

  1. Timbre speaks each of the 122 hard-set commands (alternating female/male Punjabi voices)
  2. A noisy copy is mixed: background chatter (other speech clips) + low rumble, at SNR_DB
  3. Prisma v3.0 transcribes both; transcripts are cached in eval/voice_transcripts.json
  4. Every NLU model is scored on the same transcripts

    python scripts/eval_voice.py --transcribe        # API calls (~370), once
    python scripts/eval_voice.py --model ensemble    # scoring only, no API calls
"""
import argparse
import asyncio
import difflib
import io
import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config, gnani  # noqa: E402
from app.main import KHATA_TERMS, STT_TOPIC  # noqa: E402
from app.nlu.datagen import ITEMS  # noqa: E402
from app.nlu.punjabi import normalize  # noqa: E402
from eval.hard_test import CASES, CUSTOMERS  # noqa: E402
from scripts.eval_hard import load, score  # noqa: E402

CACHE = ROOT / "eval" / "voice_transcripts.json"
VOICES = ["Mehuli", "Zayan"]
SNR_DB = 8.0          # "noisy": busy shop
SNR_LOUD_DB = 0.0     # "loud": chatter as loud as the speaker


def read_wav(b: bytes):
    with wave.open(io.BytesIO(b)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768, w.getframerate()


def write_wav(x: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def shop_noise(n: int, others: list[np.ndarray], rng) -> np.ndarray:
    babble = np.zeros(n, np.float32)
    for o in rng.choice(len(others), size=3, replace=False):
        clip = np.tile(others[o], n // len(others[o]) + 2)
        off = rng.integers(0, len(others[o]))
        babble += clip[off:off + n] * rng.uniform(0.6, 1.0)
    brown = np.cumsum(rng.normal(0, 1, n)).astype(np.float32)
    brown -= np.convolve(brown, np.ones(2000) / 2000, mode="same")   # remove drift
    brown /= np.abs(brown).max() + 1e-9
    return babble / (np.abs(babble).max() + 1e-9) + 0.5 * brown


def mix(speech: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    ps, pn = np.mean(speech ** 2), np.mean(noise ** 2) + 1e-12
    y = speech + noise * np.sqrt(ps / (pn * 10 ** (snr_db / 10)))
    return y / max(1.0, np.abs(y).max())


async def transcribe_all():
    rng = np.random.default_rng(0)
    keyterms = CUSTOMERS + KHATA_TERMS + ITEMS[:40]
    clips = []
    for i, (text, *_rest) in enumerate(CASES):
        _, wav = await gnani.synthesize(text, voice=VOICES[i % 2])
        clips.append(read_wav(wav))
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    for i, ((x, sr), (text, *_rest)) in enumerate(zip(clips, CASES)):
        others = [c[0] for j, c in enumerate(clips) if j != i]
        noise = shop_noise(len(x), others, rng)
        out = cache.get(str(i), {}) if cache.get(str(i), {}).get("text") == text else {}
        out.update({"text": text, "voice": VOICES[i % 2]})
        conds = [("clean", x), ("noisy", mix(x, noise, SNR_DB)), ("loud", mix(x, noise, SNR_LOUD_DB))]
        if all(c in out for c, _ in conds):
            continue
        for cond, audio in conds:
            if cond in out:
                continue
            r = await gnani.transcribe(write_wav(audio, sr), keyterms=keyterms, topic=STT_TOPIC)
            out[cond] = r.get("transcript", "")
        cache[str(i)] = out
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
        print(f"{i:3d} clean: {out['clean']}\n    loud:  {out['loud']}", flush=True)
    if i == len(CASES) - 1:
        noisy_path = ROOT / "eval" / "noisy_example.wav"
        noisy_path.write_bytes(write_wav(mix(clips[0][0], shop_noise(len(clips[0][0]), [c[0] for c in clips[1:]], rng),
                                             SNR_DB), clips[0][1]))


def cer(ref: str, hyp: str) -> float:
    a, b = normalize(ref).replace(" ", ""), normalize(hyp).replace(" ", "")
    sm = difflib.SequenceMatcher(None, a, b)
    edits = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return edits / max(1, len(a))


def score_all(model_name: str):
    cache = json.loads(CACHE.read_text())
    model = load(model_name)
    out = {}
    for cond in ("clean", "noisy", "loud"):
        if any(cond not in cache[str(i)] for i in range(len(CASES))):
            continue
        cases = [(cache[str(i)][cond], *c[1:]) for i, c in enumerate(CASES)]
        r = score(model, cases, label=f"{model_name}/{cond}")
        r["prisma_char_error_rate"] = round(float(np.mean([cer(c[0], cache[str(i)][cond])
                                                             for i, c in enumerate(CASES)])), 4)
        out[cond] = r
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--model", default="memm")
    a = ap.parse_args()
    if a.transcribe:
        asyncio.run(transcribe_all())
    else:
        res = score_all(a.model)
        for cond, r in res.items():
            print(f"{a.model:9s} {cond:5s} fully correct {r['fully_correct']:.3f}  intent {r['intent_acc']:.3f}  "
                  f"amount {r['amount_acc']:.3f}  customer {r['customer_acc']:.3f}  Prisma CER {r['prisma_char_error_rate']:.3f}")
