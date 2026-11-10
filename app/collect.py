"""Real-voice testing: collect labelled recordings from real people and score the app on them.

Two prompt modes per test case (taken from the hard test sets, whose answers are known):
  read  - the speaker reads the exact sentence
  free  - the speaker only sees the situation ("Bittu took ₹320 of goods on credit") and says it
          in their own words; the honest test of the language model
Each recording is transcribed by Prisma and interpreted exactly as the app would, but nothing is
written to the ledger. Audio + results are stored locally in data/real/ (never committed).
"""
import json
import time
import uuid

from . import audio_quality, config, gnani
from .actions import H
from .nlu import parser
from .nlu.parser import SETTLE_WORDS, resolve_customer
from .nlu.punjabi import find_numbers, pick_amount
from .nlu.translit import to_roman

REAL_DIR = config.DATA_DIR / "real"
AUDIO_DIR = REAL_DIR / "audio"
LOG = REAL_DIR / "recordings.jsonl"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

TRANSACTIONAL = {"CREDIT", "PAYMENT", "SALE", "EXPENSE"}
NO_CUSTOMER = {"SALE", "EXPENSE", "SUMMARY", "DEBTORS", "UNDO", "OTHER"}
STT = {"pa": ("pa-IN", None), "hi": ("hi-IN", None), "en": ("en-IN", None)}


def _cases(lang: str):
    if lang == "hi":
        from eval.hard_test_hi import CASES
    elif lang == "en":
        from eval.hard_test_en import CASES
    else:
        from eval.hard_test import CASES
    return CASES


def _customers(lang: str) -> list[dict]:
    from eval.hard_test import CUSTOMERS
    names = CUSTOMERS + (["Lakhvir"] if lang != "pa" else [])
    return [{"id": i + 1, "name": n} for i, n in enumerate(names)]


def _name(n: str | None, lang: str) -> str:
    if not n:
        return ""
    return {"hi": H(n), "en": to_roman(n)}.get(lang, n)


def situation(intent: str, amount, cust: str | None, lang: str) -> str:
    """Describe what to say, without dictating the words."""
    n, A = _name(cust, lang), (f"₹{int(amount):,}" if amount else "")
    T = {
        "pa": {"CREDIT": f"{n} ਨੇ {A} ਦਾ ਸਮਾਨ ਉਧਾਰ ਲਿਆ। ਖਾਤੇ ਵਿੱਚ ਲਿਖਵਾਓ।",
               "PAYMENT": f"{n} ਨੇ {A} ਦੇ ਦਿੱਤੇ। ਜਮ੍ਹਾ ਕਰਵਾਓ।" if A else f"{n} ਨੇ ਪੂਰਾ ਖਾਤਾ ਸਾਫ਼ ਕਰ ਦਿੱਤਾ। ਦੱਸੋ।",
               "SALE": f"ਤੁਸੀਂ {A} ਦਾ ਸਮਾਨ ਨਕਦ ਵੇਚਿਆ। ਲਿਖਵਾਓ।", "EXPENSE": f"ਦੁਕਾਨ ਦਾ {A} ਦਾ ਖਰਚਾ ਹੋਇਆ (ਬਿੱਲ, ਕਿਰਾਇਆ ਜਾਂ ਤਨਖਾਹ)। ਲਿਖਵਾਓ।",
               "BALANCE": f"ਪੁੱਛੋ ਕਿ {n} ਵੱਲ ਕਿੰਨੇ ਪੈਸੇ ਬਾਕੀ ਹਨ।", "DEBTORS": "ਪੁੱਛੋ ਕਿ ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਬਾਕੀ ਹਨ।",
               "SUMMARY": "ਅੱਜ ਜਾਂ ਇਸ ਮਹੀਨੇ ਦਾ ਹਿਸਾਬ ਪੁੱਛੋ।",
               "REMIND": f"{n} ਨੂੰ ਪੈਸਿਆਂ ਦੀ ਯਾਦ ਕਰਵਾਉਣ ਲਈ ਕਹੋ।" if n else "ਬਕਾਏ ਵਾਲੇ ਸਾਰਿਆਂ ਨੂੰ ਯਾਦ ਕਰਵਾਉਣ ਲਈ ਕਹੋ।",
               "UNDO": "ਪਿਛਲੀ ਐਂਟਰੀ ਹਟਾਉਣ ਲਈ ਕਹੋ।",
               "RISK": f"ਪੁੱਛੋ ਕਿ ਕੀ {n} ਨੂੰ ਹੋਰ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਹੈ।" if n else "ਪੁੱਛੋ ਕਿ ਕਿਹੜੇ ਗਾਹਕ ਖਤਰੇ ਵਾਲੇ ਹਨ।",
               "OTHER": "ਹਿਸਾਬ ਤੋਂ ਇਲਾਵਾ ਕੁਝ ਵੀ ਕਹੋ (ਜਿਵੇਂ ਸਤ ਸ੍ਰੀ ਅਕਾਲ)।"},
        "hi": {"CREDIT": f"{n} ने {A} का सामान उधार लिया। खाते में लिखवाइए।",
               "PAYMENT": f"{n} ने {A} दे दिए। जमा करवाइए।" if A else f"{n} ने पूरा खाता साफ़ कर दिया। बताइए।",
               "SALE": f"आपने {A} का सामान नकद बेचा। लिखवाइए।", "EXPENSE": f"दुकान का {A} का खर्चा हुआ (बिल, किराया या तनख्वाह)। लिखवाइए।",
               "BALANCE": f"पूछिए कि {n} पर कितने पैसे बाकी हैं।", "DEBTORS": "पूछिए कि किस-किस के पैसे बाकी हैं।",
               "SUMMARY": "आज का या इस महीने का हिसाब पूछिए।",
               "REMIND": f"{n} को पैसों की याद दिलाने को कहिए।" if n else "बकाये वाले सबको याद दिलाने को कहिए।",
               "UNDO": "पिछली एंट्री हटाने को कहिए।",
               "RISK": f"पूछिए कि क्या {n} को और उधार देना ठीक है।" if n else "पूछिए कि कौन से ग्राहक ख़तरे वाले हैं।",
               "OTHER": "हिसाब के अलावा कुछ भी कहिए (जैसे नमस्ते)।"},
        "en": {"CREDIT": f"{n} took {A} of goods on credit. Get it written down.",
               "PAYMENT": f"{n} paid you {A}. Record it." if A else f"{n} cleared their whole account. Record it.",
               "SALE": f"You sold {A} of goods for cash. Record it.", "EXPENSE": f"The shop spent {A} (a bill, rent or salary). Record it.",
               "BALANCE": f"Ask how much {n} owes.", "DEBTORS": "Ask who all owe you money.",
               "SUMMARY": "Ask for today's or this month's totals.",
               "REMIND": f"Ask the app to remind {n} to pay." if n else "Ask the app to remind everyone who owes.",
               "UNDO": "Ask the app to delete the last entry.",
               "RISK": f"Ask whether it's safe to give {n} more credit." if n else "Ask which customers are risky.",
               "OTHER": "Say something that isn't about the ledger (e.g. good morning)."},
    }
    return T[lang][intent]


def prompts(lang: str) -> list[dict]:
    return [{"case": i, "intent": intent, "amount": amount, "customer": cust, "text": text,
             "situation": situation(intent, amount, cust, lang), "customer_display": _name(cust, lang)}
            for i, (text, intent, amount, cust) in enumerate(_cases(lang))]


async def score(transcript: str, intent: str, amount, cust, lang: str, audio: dict | None = None) -> dict:
    """Run the app's real pipeline (understand + the pre-action questions) and compare to the truth.
    outcome: 'correct' (acted right, no question), 'asked' (asked back first; safe), or
    'wrong_silent' (would have acted wrongly without asking: the dangerous case)."""
    from .actions import precheck
    cmd = await parser.understand(transcript, audio if lang == "pa" else None, customers=_customers(lang))
    got_i = cmd["intent"]
    c = cmd["customer"]
    got_c = c.get("name") if c.get("status") in ("match", "new") else None
    amt = cmd["amount"]
    ok_i = got_i == intent
    ok_a = True
    if intent in TRANSACTIONAL:
        ok_a = (amt == amount) if amount is not None else (amt is None and cmd.get("settle_all"))
    ok_c = cust is None or got_c == cust
    correct = ok_i and ok_a and ok_c
    question, _ = precheck(cmd)
    outcome = "asked" if question else ("correct" if correct else "wrong_silent")
    return {"intent": got_i, "amount": amt, "customer": got_c, "confidence": round(cmd["confidence"], 3),
            "ok_intent": ok_i, "ok_amount": bool(ok_a), "ok_customer": ok_c, "correct": correct,
            "asked": question["action"] if question else None, "outcome": outcome}


async def record(audio: bytes, lang: str, case: int, mode: str, env: str, speaker: str) -> dict:
    p = prompts(lang)[case]
    code = STT[lang][0]
    names = [c["name"] for c in _customers(lang)]
    keyterms = {"hi": [H(n) for n in names], "en": [to_roman(n) for n in names]}.get(lang, names)
    stt = await gnani.transcribe(audio_quality.pad_wav(audio), language=code, keyterms=keyterms)
    transcript = (stt.get("transcript") or "").strip()
    feats = audio_quality.from_wav(audio)
    res = await score(transcript, p["intent"], p["amount"], p["customer"], lang, feats) if transcript else \
        {"correct": False, "intent": None, "empty": True, "outcome": "asked"}
    rid = uuid.uuid4().hex[:12]
    (AUDIO_DIR / f"{rid}.wav").write_bytes(audio)
    row = {"id": rid, "ts": time.time(), "lang": lang, "mode": mode, "env": env, "speaker": speaker[:40],
           "case": case, "expected": {k: p[k] for k in ("intent", "amount", "customer", "text")},
           "transcript": transcript, "stt_ms": stt.get("latency_ms"), "audio": feats,
           "result": res}
    with LOG.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def rows() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]


def stats() -> dict:
    rs = rows()
    out = {"n": len(rs), "by": {}}
    for key in ("lang", "env", "mode", "speaker"):
        groups: dict = {}
        for r in rs:
            g = groups.setdefault(r.get(key) or "-", [0, 0])
            g[0] += 1
            g[1] += bool(r["result"].get("correct"))
        out["by"][key] = {k: {"n": v[0], "correct": v[1]} for k, v in groups.items()}
    out["correct"] = sum(bool(r["result"].get("correct")) for r in rs)
    return out


def delete(rid: str) -> bool:
    rs = rows()
    keep = [r for r in rs if r["id"] != rid]
    if len(keep) == len(rs):
        return False
    LOG.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep))
    (AUDIO_DIR / f"{rid}.wav").unlink(missing_ok=True)
    return True
