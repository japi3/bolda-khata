"""Score an NLU model on the hard held-out set (eval/hard_test.py), using the same
deterministic amount parsing and customer matching as the app, so models are compared fairly.

    python scripts/eval_hard.py               # current on-device model (models/nlu.joblib)
    python scripts/eval_hard.py --model muril # fine-tuned transformer (models/muril/)
    python scripts/eval_hard.py --errors      # print every mistake
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.nlu.parser import SETTLE_WORDS, resolve_customer  # noqa: E402
from app.nlu.punjabi import find_numbers, pick_amount  # noqa: E402
from eval.hard_test import CASES, CUSTOMERS  # noqa: E402
from eval.hard_test_en import CASES as CASES_EN  # noqa: E402
from eval.hard_test_hi import CASES as CASES_HI  # noqa: E402

TRANSACTIONAL = {"CREDIT", "PAYMENT", "SALE", "EXPENSE"}
NO_CUSTOMER = {"SALE", "EXPENSE", "SUMMARY", "DEBTORS", "UNDO", "OTHER"}


def load(kind: str):
    if kind == "memm":
        from app.nlu.model import KhataNLU
        return KhataNLU.load(config.MODEL_DIR / "nlu.joblib")
    if kind == "muril":
        from app.nlu.transformer import TransformerNLU
        return TransformerNLU.load(config.MODEL_DIR / "muril")
    if kind == "ensemble":
        from app.nlu.ensemble import EnsembleNLU
        return EnsembleNLU.load()
    raise SystemExit(f"unknown model {kind}")


def command(model, text: str, customers: list[dict]) -> dict:
    r = model.analyse(text)
    toks = r["tokens"]
    amount = pick_amount(find_numbers(toks))
    intent = r["intent"]
    spoken = r["names"][0] if r["names"] else None
    cust = {"status": "none", "name": None} if intent in NO_CUSTOMER else resolve_customer(spoken, text, customers)
    settle = intent == "PAYMENT" and amount is None and bool(set(toks) & SETTLE_WORDS)
    return {"intent": intent, "amount": amount, "customer": cust, "settle": settle, "raw": r}


def score(model, cases=CASES, show_errors=False, label=""):
    # "Lakhvir" is an existing account only in the English/Hindi tests; in the Punjabi test ਲਖਵੀਰ is a new customer
    extra = [] if cases is CASES or any("\u0A00" <= ch <= "\u0A7F" for ch in cases[0][0]) else ["Lakhvir"]
    customers = [{"id": i + 1, "name": n} for i, n in enumerate(CUSTOMERS + extra)]
    per = defaultdict(Counter)
    n_int = n_amt = n_amt_tot = n_cust = n_cust_tot = n_full = 0
    t0 = time.perf_counter()
    errors = []
    for text, intent, amount, cust in cases:
        c = command(model, text, customers)
        ok_i = c["intent"] == intent
        ok_a = True
        if intent in TRANSACTIONAL:
            n_amt_tot += 1
            ok_a = (c["amount"] == amount) if amount is not None else (c["amount"] is None and c["settle"])
            n_amt += ok_a
        ok_c = True
        if cust is not None:
            n_cust_tot += 1
            got = c["customer"].get("name") if c["customer"]["status"] in ("match", "new") else None
            ok_c = got == cust
            n_cust += ok_c
        n_int += ok_i
        full = ok_i and ok_a and ok_c
        n_full += full
        per[intent]["n"] += 1
        per[intent]["ok"] += full
        if not full:
            errors.append((text, intent, amount, cust, c))
    ms = (time.perf_counter() - t0) * 1000 / len(cases)
    n = len(cases)
    res = {"model": label, "n": n, "intent_acc": round(n_int / n, 3), "amount_acc": round(n_amt / n_amt_tot, 3),
           "customer_acc": round(n_cust / n_cust_tot, 3), "fully_correct": round(n_full / n, 3),
           "ms_per_utterance": round(ms, 1),
           "per_intent_full": {k: round(v["ok"] / v["n"], 2) for k, v in sorted(per.items())}}
    if show_errors:
        for text, intent, amount, cust, c in errors:
            got = c["customer"].get("name") if c["customer"]["status"] in ("match", "new") else None
            print(f"  ✗ {text}\n      want {intent} {amount} {cust}  got {c['intent']} {c['amount']} {got}"
                  f"  names={c['raw']['names']}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="memm")
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--lang", default="pa", choices=["pa", "en", "hi"])
    a = ap.parse_args()
    res = score(load(a.model), {"en": CASES_EN, "hi": CASES_HI}.get(a.lang, CASES), show_errors=a.errors, label=a.model)
    print(json.dumps(res, ensure_ascii=False, indent=1))
