"""End-to-end voice evaluation through the real Gnani stack:

   hand-written Punjabi command ──Timbre TTS──► audio ──Prisma STT──► transcript ──NLU──► command

The 25 commands are new phrasings (not copied from the training templates), with
amounts spoken as Punjabi number words. Reads customers from the demo DB, never
writes to it. Saves models/e2e_report.json.  (~50 API calls)
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db, gnani  # noqa: E402
from app.main import KHATA_TERMS, STT_TOPIC  # noqa: E402
from app.nlu import parser  # noqa: E402
from app.nlu.datagen import ITEMS  # noqa: E402

CASES = [  # text, intent, amount, customer (saved spelling or new name)
    ("ਗੁਰਪ੍ਰੀਤ ਨੂੰ ਤਿੰਨ ਸੌ ਦੀ ਦਾਲ ਉਧਾਰ ਦੇ ਦਿੱਤੀ", "CREDIT", 300, "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"),
    ("ਹਰਪ੍ਰੀਤ ਕੌਰ ਨੇ ਪੰਜ ਸੌ ਰੁਪਏ ਜਮ੍ਹਾ ਕਰਵਾ ਦਿੱਤੇ", "PAYMENT", 500, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    ("ਬਿੱਟੂ ਦੇ ਖਾਤੇ ਵਿੱਚ ਸਾਢੇ ਚਾਰ ਸੌ ਲਿਖ ਲਓ", "CREDIT", 450, "ਬਿੱਟੂ"),
    ("ਮਾਸਟਰ ਜੀ ਨੇ ਦੋ ਹਜ਼ਾਰ ਗੂਗਲ ਪੇ ਕਰ ਦਿੱਤੇ", "PAYMENT", 2000, "ਮਾਸਟਰ ਜੀ"),
    ("ਅੱਜ ਸੱਤ ਸੌ ਰੁਪਏ ਦੀ ਨਕਦ ਵਿਕਰੀ ਹੋਈ", "SALE", 700, None),
    ("ਦੁਕਾਨ ਦਾ ਕਿਰਾਇਆ ਅੱਠ ਹਜ਼ਾਰ ਦੇ ਦਿੱਤਾ", "EXPENSE", 8000, None),
    ("ਕੁਲਦੀਪ ਵੱਲ ਕਿੰਨੇ ਪੈਸੇ ਖੜ੍ਹੇ ਨੇ", "BALANCE", None, "ਕੁਲਦੀਪ"),
    ("ਸਾਰਿਆਂ ਦਾ ਕੁੱਲ ਬਕਾਇਆ ਕਿੰਨਾ ਹੈ", "DEBTORS", None, None),
    ("ਇਸ ਹਫ਼ਤੇ ਦੀ ਵਿਕਰੀ ਦੱਸੋ", "SUMMARY", None, None),
    ("ਸੁਖਵਿੰਦਰ ਨੂੰ ਪੈਸਿਆਂ ਦੀ ਯਾਦ ਦਿਵਾ ਦਿਓ", "REMIND", None, "ਸੁਖਵਿੰਦਰ"),
    ("ਹੁਣੇ ਵਾਲੀ ਐਂਟਰੀ ਕੱਟ ਦਿਓ", "UNDO", None, None),
    ("ਪਿੰਕੀ ਨੂੰ ਹੋਰ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਰਹੇਗਾ", "RISK", None, "ਪਿੰਕੀ"),
    ("ਜਸਵੀਰ ਦੋ ਕਿੱਲੋ ਖੰਡ ਲੈ ਗਿਆ ਇੱਕ ਸੌ ਦਸ ਰੁਪਏ ਦੀ", "CREDIT", 110, "ਜਸਵੀਰ"),
    ("ਰਮੇਸ਼ ਨੇ ਸਾਰਾ ਹਿਸਾਬ ਚੁਕਤਾ ਕਰ ਦਿੱਤਾ", "PAYMENT", None, "ਰਮੇਸ਼ ਕੁਮਾਰ"),
    ("ਸਿਮਰਨ ਤੋਂ ਡੇਢ ਸੌ ਰੁਪਏ ਮਿਲੇ", "PAYMENT", 150, "ਸਿਮਰਨ"),
    ("ਨਵਜੋਤ ਨੂੰ ਬਾਰਾਂ ਸੌ ਦਾ ਸਮਾਨ ਉਧਾਰ ਦਿੱਤਾ", "CREDIT", 1200, "ਨਵਜੋਤ"),
    ("ਬਿਜਲੀ ਦਾ ਬਿੱਲ ਪੱਚੀ ਸੌ ਭਰ ਦਿੱਤਾ", "EXPENSE", 2500, None),
    ("ਕਿਹੜੇ ਗਾਹਕ ਪੈਸੇ ਨਹੀਂ ਮੋੜਦੇ", "RISK", None, None),
    ("ਕੱਲ੍ਹ ਕਿੰਨਾ ਖਰਚਾ ਹੋਇਆ ਸੀ", "SUMMARY", None, None),
    ("ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ ਦਾ ਖਾਤਾ ਦਿਖਾਓ", "BALANCE", None, "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"),
    ("ਪੰਜ ਸੌ ਪੰਜਾਹ ਨਕਦ ਆਏ ਸਮਾਨ ਵੇਚ ਕੇ", "SALE", 550, None),
    ("ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜੀ ਕੀ ਹਾਲ ਹੈ", "OTHER", None, None),
    ("ਹਰਪ੍ਰੀਤ ਨੂੰ ਇੱਕ ਹਜ਼ਾਰ ਉਧਾਰ ਦਿੱਤਾ", "CREDIT", 1000, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    ("ਕੁਲਦੀਪ ਨੂੰ ਸੁਨੇਹਾ ਭੇਜੋ ਕਿ ਪੈਸੇ ਦੇ ਜਾਵੇ", "REMIND", None, "ਕੁਲਦੀਪ"),
    ("ਬਿੱਟੂ ਤੇ ਭਰੋਸਾ ਕਰਾਂ", "RISK", None, "ਬਿੱਟੂ"),
]
VOICES = ["Mehuli", "Zayan"]   # female + male Punjabi Timbre voices


async def main():
    names = [c["name"] for c in db.customers()]
    rows, t0 = [], time.time()
    for i, (text, intent, amount, cust) in enumerate(CASES):
        voice = VOICES[i % 2]
        _, wav = await gnani.synthesize(text, voice=voice)
        stt = await gnani.transcribe(wav, keyterms=names + KHATA_TERMS + ITEMS[:40], topic=STT_TOPIC)
        cmd = await parser.understand(stt["transcript"])
        got_c = cmd["customer"]["name"] if cmd["customer"]["status"] in ("match", "new") else None
        ok_i = cmd["intent"] == intent
        ok_a = (amount is None) or (cmd["amount"] is not None and abs(cmd["amount"] - amount) < 0.01)
        ok_c = (cust is None) or (got_c == cust)
        rows.append({"text": text, "voice": voice, "transcript": stt["transcript"], "stt_ms": stt["latency_ms"],
                     "intent": cmd["intent"], "expected_intent": intent, "amount": cmd["amount"],
                     "expected_amount": amount, "customer": got_c, "expected_customer": cust,
                     "ok_intent": ok_i, "ok_amount": ok_a, "ok_customer": ok_c, "all_ok": ok_i and ok_a and ok_c})
        flag = "✓" if ok_i and ok_a and ok_c else "✗"
        print(f"{flag} [{voice}] {stt['transcript']}  -> {cmd['intent']} amt={cmd['amount']} cust={got_c}")
    n = len(rows)
    with_amt = [r for r in rows if r["expected_amount"] is not None]
    with_cust = [r for r in rows if r["expected_customer"] is not None]
    rep = {
        "n": n, "intent_accuracy": round(sum(r["ok_intent"] for r in rows) / n, 3),
        "amount_accuracy": round(sum(r["ok_amount"] for r in with_amt) / len(with_amt), 3),
        "customer_accuracy": round(sum(r["ok_customer"] for r in with_cust) / len(with_cust), 3),
        "fully_correct": round(sum(r["all_ok"] for r in rows) / n, 3),
        "median_stt_ms": sorted(r["stt_ms"] for r in rows)[n // 2],
        "engine": "evon" if parser.evon.enabled() else "on-device",
        "seconds": round(time.time() - t0, 1), "rows": rows,
    }
    (config.MODEL_DIR / "e2e_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    print({k: v for k, v in rep.items() if k != "rows"})


if __name__ == "__main__":
    asyncio.run(main())
