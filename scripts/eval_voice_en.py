"""English/Hinglish (or Hindi) voice evaluation: Timbre speaks eval/hard_test_en.py
(or hard_test_hi.py), optionally mixed with shop noise (8 dB); Prisma transcribes in
en-IN (or hi-IN) mode.

    python scripts/eval_voice_en.py [--lang hi] --transcribe     # API calls (~130), cached
    python scripts/eval_voice_en.py [--lang hi] --model ensemble # scoring only
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import audio_quality as aq, gnani  # noqa: E402
from app.actions import H  # noqa: E402
from app.main import KHATA_TERMS_EN, KHATA_TERMS_HI, STT_TOPIC_EN, STT_TOPIC_HI  # noqa: E402
from app.nlu.translit import to_roman  # noqa: E402
from eval.hard_test import CUSTOMERS  # noqa: E402
from eval.hard_test_en import CASES as CASES_EN  # noqa: E402
from eval.hard_test_hi import CASES as CASES_HI  # noqa: E402
from scripts.eval_hard import load, score  # noqa: E402
from scripts.eval_voice import SNR_DB, mix, shop_noise, write_wav  # noqa: E402

CFG = {
    "en": dict(cases=CASES_EN, cache=ROOT / "eval" / "voice_transcripts_en.json", voices=["Trupti", "Shlok"],
               code="en-IN", terms=KHATA_TERMS_EN, topic=STT_TOPIC_EN, name=to_roman),
    "hi": dict(cases=CASES_HI, cache=ROOT / "eval" / "voice_transcripts_hi.json", voices=["Bhavna", "Vikrant"],
               code="hi-IN", terms=KHATA_TERMS_HI, topic=STT_TOPIC_HI, name=H),
}


async def transcribe_all(lang):
    c = CFG[lang]
    CASES, CACHE = c["cases"], c["cache"]
    keyterms = [c["name"](n) for n in CUSTOMERS] + ["Lakhvir"] + c["terms"]
    clips = [aq.read_wav((await gnani.synthesize(t, voice=c["voices"][i % 2], language=c["code"]))[1])
             for i, (t, *_r) in enumerate(CASES)]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rng = np.random.default_rng(3)
    for i, ((x, sr), (text, *_r)) in enumerate(zip(clips, CASES)):
        out = cache.get(str(i), {}) if cache.get(str(i), {}).get("text") == text else {}
        out["text"] = text
        noise = shop_noise(len(x), [c[0] for j, c in enumerate(clips) if j != i], rng)
        for cond, audio in (("clean", x), ("noisy", mix(x, noise, SNR_DB))):
            if cond in out:
                continue
            r = await gnani.transcribe(write_wav(audio, sr), language=c["code"], keyterms=keyterms, topic=c["topic"])
            out[cond] = r.get("transcript", "")
        cache[str(i)] = out
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
        print(f"{i:2d} {out['clean']}  |  {out['noisy']}", flush=True)


def score_all(model_name, lang):
    CASES = CFG[lang]["cases"]
    cache = json.loads(CFG[lang]["cache"].read_text())
    m = load(model_name)
    res = {"text": score(m, CASES, label=model_name)}
    for cond in ("clean", "noisy"):
        res[cond] = score(m, [(cache[str(i)][cond], *c[1:]) for i, c in enumerate(CASES)], label=model_name)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--model", default="ensemble")
    ap.add_argument("--lang", default="en", choices=["en", "hi"])
    a = ap.parse_args()
    if a.transcribe:
        asyncio.run(transcribe_all(a.lang))
    else:
        for cond, r in score_all(a.model, a.lang).items():
            print(f"{a.model:9s} {cond:5s} fully correct {r['fully_correct']:.3f}  intent {r['intent_acc']:.3f}  "
                  f"amount {r['amount_acc']:.3f}  customer {r['customer_acc']:.3f}")
