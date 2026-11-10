"""Hybrid understanding: on-device NLU + Evon, merged into one ledger command.

  transcript ──► local KhataNLU (≈2 ms, always) ─┐
             └─► Evon 30B (if configured) ───────┴─► merge ─► resolve customer ─► command

Deterministic code owns the parts that must be exact: amounts (Punjabi number
parser), dates, and matching a spoken name to an existing account.
"""
import asyncio
import difflib
import re
import time

from .. import config, db, repeat_detector
from . import evon
from .ensemble import EnsembleNLU
from .translit import to_roman
from .bill import parse_bill
from .query import parse_query
from .stock_parse import parse_stock
from .punjabi import amount_conflict, date_offset, find_numbers, normalize, pick_amount, pick_quantity, surface_tokens

_nlu: EnsembleNLU | None = None
TRANSACTIONAL = {"CREDIT", "PAYMENT", "SALE", "EXPENSE"}
# Credit vs payment moves the balance in opposite directions, so a wrong guess is the
# costliest error. If the model gives the opposite direction > 25% probability we ask.
# (Rule fixed in advance; the dev set had no such confusions to tune it on.)
DIRECTION_DOUBT = 0.25
NEEDS_CUSTOMER = {"CREDIT", "PAYMENT", "BALANCE"}
SETTLE_WORDS = {normalize(w) for w in "ਪੂਰਾ ਪੂਰੇ ਸਾਰਾ ਸਾਰੇ ਸਾਫ਼ ਚੁਕਤਾ ਸਾਰਿਆਂ".split()} | set(
    "full all everything entire whole cleared settled complete pura poora sara saara".split()) | {
    normalize(w) for w in "सारा सारे पूरा पूरे साफ चुका चुकता".split()}
#  A sentence can't begin with a postposition ("ਨੇ / ਨੂੰ / को / ने …"): it needs a noun (usually the
#  customer's name) in front. Real recordings showed this whenever the first word was lost, as did an
#  English sentence starting with a bare verb ("paid 500 by UPI").
_DANGLING = {normalize(w) for w in "ਨੇ ਨੂੰ ਦੇ ਦਾ ਦੀ ਤੋਂ ਵੱਲ ਲਈ ने को के का की से पर".split()}
_BARE_VERB_EN = {"paid", "took", "gave", "sent", "owes", "cleared", "bought", "returned", "deposited"} | {
    normalize(w) for w in "ਆਇਆ ਆਈ आया आई".split()}   # "came…" with no one who came


def cut_off_start(toks: list[str]) -> bool:
    if not toks:
        return False
    return toks[0] in _DANGLING or toks[0] in _BARE_VERB_EN


# Words that can never be a customer's name (question / money / time words). Real use: "Kinne paise?"
# ("how much money?") had "Kinne" tagged as a name, so the app replied "no account found".
_NOT_NAMES = {normalize(w) for w in (
    "ਕਿੰਨੇ ਕਿੰਨਾ ਕਿੰਨੀ ਕੌਣ ਕਿਸ ਕੀ ਕਿਵੇਂ ਪੈਸੇ ਪੈਸਾ ਰੁਪਏ ਅੱਜ ਕੱਲ੍ਹ ਹਿਸਾਬ ਖਾਤਾ ਬਾਕੀ ਸਾਰੇ "
    "कितने कितना कितनी कौन किस क्या कैसे पैसे पैसा रुपये आज कल हिसाब खाता बाकी सारे "
    "kinne kinna kinni kitne kitna kitni kaun kis kya kaise paise paisa rupees aaj kal hisaab hisab khata baaki baki "
    "how much what who which money today yesterday total balance").split()}


def _not_a_name(name: str) -> bool:
    words = normalize(name).split()
    return not words or all(w in _NOT_NAMES for w in words)


CREDIT_CUES = {normalize(w) for w in "ਉਧਾਰ ਉਧਾਰੀ उधार udhaar udhar udhari credit".split()}
CASH_CUES = {normalize(w) for w in "ਨਕਦ ਕੈਸ਼ नकद कैश cash naqad nakad".split()}
# buying stock for the shop: money going out, never a sale or a customer's credit
RESTOCK = {normalize(w) for w in "ਥੋਕ ਹੋਲਸੇਲ ਮੰਡੀ ਸਪਲਾਇਰ ਡਿਸਟ੍ਰੀਬਿਊਟਰ थोक होलसेल मंडी सप्लायर डिस्ट्रीब्यूटर "
           "wholesale wholesaler wholesalers mandi supplier distributor thok".split()}
HONORIFICS = {normalize(w) for w in "ਜੀ ਸਾਹਿਬ ਸਾਬ".split()} | {"ji", "jee", "sahib", "sahab", "saab"}
_GURMUKHI = re.compile(r"[\u0900-\u097F\u0A00-\u0A7F]")   # Gurmukhi or Devanagari


def phonetic(s: str) -> str:
    """Script-independent sound key, so "Bittu", "Bittoo" and "ਬਿੱਟੂ" all match.
    Gurmukhi is romanised first, then common spelling variants are collapsed."""
    s = to_roman(s) if _GURMUKHI.search(s or "") else (s or "")
    s = re.sub(r"[^a-z ]", "", normalize(s))
    for a, b in (("oo", "u"), ("ee", "i"), ("aa", "a"), ("ph", "f"), ("w", "v"), ("z", "j"), ("q", "k"),
                 ("ck", "k"), ("y ", "i "), ("bh", "b")):
        s = (s + " ").replace(a, b).strip()
    s = re.sub(r"(.)\1+", r"\1", s)            # double letters
    s = re.sub(r"y$", "i", s)
    return s


def nlu() -> EnsembleNLU:
    """MuRIL + MEMM ensemble (MEMM alone if the transformer weights are absent)."""
    global _nlu
    if _nlu is None:
        _nlu = EnsembleNLU.load()
    return _nlu


def _sim(a: str, b: str) -> float:
    direct = difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()
    sound = difflib.SequenceMatcher(None, phonetic(a), phonetic(b)).ratio()
    return max(direct, sound)


def resolve_customer(spoken: str | None, transcript: str, customers: list[dict]) -> dict:
    """Match a spoken name to an existing account.
    Returns {status: 'match'|'new'|'ambiguous'|'none', id, name, candidates}."""
    norm_t = " " + normalize(transcript) + " "
    if not spoken:
        # tagger may have missed it: look for any known name inside the transcript
        ph_t = " " + phonetic(transcript) + " "
        hits = [c for c in customers if " " + normalize(c["name"]) + " " in norm_t
                or " " + normalize(c["name"]).split()[0] + " " in norm_t
                or (len(phonetic(c["name"]).split()[0]) > 3 and " " + phonetic(c["name"]).split()[0] + " " in ph_t)]
        if len(hits) == 1:
            return {"status": "match", "id": hits[0]["id"], "name": hits[0]["name"], "candidates": []}
        return {"status": "none", "id": None, "name": None, "candidates": []}

    words = [w for w in normalize(spoken).split() if w not in HONORIFICS] or normalize(spoken).split()
    core = " ".join(words)
    scored = []
    for c in customers:
        cn = normalize(c["name"])
        cw = [w for w in cn.split() if w not in HONORIFICS] or cn.split()
        s_full = _sim(core, " ".join(cw))
        s_first = _sim(words[0], cw[0])
        # "ਗੁਰਪ੍ਰੀਤ" said, account is "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ" -> strong first-name match
        s = max(s_full, s_first * (0.97 if len(words) == 1 else 0.85))
        scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    good = [(s, c) for s, c in scored if s >= 0.82]
    if not good:
        return {"status": "new", "id": None, "name": spoken.strip(), "candidates":
                [c["name"] for s, c in scored[:2] if s >= 0.6]}
    top = good[0][0]
    tied = [c for s, c in good if top - s < 0.03]
    exact = [c for c in tied if normalize(c["name"]) == normalize(spoken)]
    if exact:
        return {"status": "match", "id": exact[0]["id"], "name": exact[0]["name"], "candidates": []}
    if len(tied) > 1:
        return {"status": "ambiguous", "id": None, "name": spoken.strip(),
                "candidates": [{"id": c["id"], "name": c["name"]} for c in tied[:4]]}
    c = good[0][1]
    return {"status": "match", "id": c["id"], "name": c["name"], "candidates": []}


def _period(toks: list[str]) -> str:
    s = set(toks)
    if s & {normalize("ਹਫ਼ਤੇ"), normalize("ਹਫਤੇ"), normalize("ਹਫ਼ਤਾ"), "week", "weekly", "hafte", "hafta"}:
        return "week"
    if s & {normalize("ਮਹੀਨੇ"), normalize("ਮਹੀਨਾ"), "month", "monthly", "mahine", "mahina"}:
        return "month"
    return "today"


async def understand(transcript: str, audio: dict | None = None, customers: list[dict] | None = None) -> dict:
    customers = db.customers() if customers is None else customers
    names = [c["name"] for c in customers]
    t0 = time.perf_counter()
    local = nlu().analyse(transcript)
    local_ms = round((time.perf_counter() - t0) * 1000, 1)

    ev, ev_err = None, None
    if evon.enabled():
        try:
            ev = await asyncio.wait_for(evon.extract(transcript, names), timeout=config.EVON_TIMEOUT)
        except Exception as e:  # Evon down/slow -> on-device model carries on
            ev_err = f"{type(e).__name__}: {e}"[:200]

    toks = local["tokens"]
    nums = find_numbers(toks)
    amount = pick_amount(nums)
    qty, unit = pick_quantity(nums)

    if ev:
        intent = ev.get("intent", local["intent"])
        conf = float(ev.get("confidence") or 0.8)
        spoken = ev.get("customer") or (local["names"][0] if local["names"] else None)
        item = ev.get("item") or (local["items"][0] if local["items"] else None)
        if ev.get("amount") is not None:
            try:
                amount = float(ev["amount"])
            except (TypeError, ValueError):
                pass
        qty = ev.get("quantity") or qty
        unit = ev.get("unit") or unit
        day = int(ev.get("day_offset") or 0)
        period = ev.get("period") or _period(toks)
        settle = bool(ev.get("settle_all"))
        engine = "evon"
    else:
        intent, conf = local["intent"], local["confidence"]
        spoken = next((n for n in local["names"] if not _not_a_name(n)), None)
        item = local["items"][0] if local["items"] else None
        day = date_offset(toks)
        period = _period(toks)
        settle = intent == "PAYMENT" and amount is None and bool(set(toks) & SETTLE_WORDS)
        engine = nlu().name

    # Smart questions about the ledger ("who owes more than 5000?", "how much did Bittu take this month?",
    # "who hasn't paid for a month?"): see nlu/query.py. Decided by explicit rules, answered from the database.
    # Stock ("ਆਟੇ ਦੀਆਂ ਕਿੰਨੀਆਂ ਬੋਰੀਆਂ ਬਚੀਆਂ?", "ਸਟਾਕ ਵਿੱਚ 50 ਕਿੱਲੋ ਖੰਡ ਹੈ", "ਕਿਹੜਾ ਮਾਲ ਮੁੱਕਣ ਵਾਲਾ ਹੈ?"): nlu/stock_parse.py
    stock_cmd = parse_stock(toks) if engine != "evon" and intent not in ("UNDO", "REMIND") else None
    if stock_cmd:
        intent = "STOCK"
    query = None
    if engine != "evon" and intent not in ("UNDO", "REMIND", "STOCK"):
        query = parse_query(toks, resolve_customer(spoken, transcript, customers))
        if query:
            intent = "QUERY"

    # "udhaar" means credit, so it can never be a cash sale. Found on real recordings: when the customer's
    # name was lost at the start ("(Bittu) ko 320 udhaar diya"), the model guessed SALE and would have
    # silently booked credit as cash. As CREDIT with no name, the app asks "whose account?" instead.
    if intent == "SALE" and set(toks) & CREDIT_CUES and not set(toks) & CASH_CUES:
        intent = "CREDIT"

    # Restocking ("10 sacks of flour from the wholesaler", "थोक से 20 पेटी तेल"): "bought" here is the shop
    # buying, so it is an expense, not a sale, unless a saved customer is named.
    restock = bool(set(toks) & RESTOCK) and intent in ("SALE", "CREDIT", "PAYMENT")
    if restock and resolve_customer(spoken, transcript, customers)["status"] != "match":
        intent = "EXPENSE"
    else:
        restock = False

    # Multi-part bill in one sentence (qty × rate, several items, money paid now): see nlu/bill.py.
    # The bill decides the amount; a named customer means it goes on their account (anything paid now
    # becomes a linked payment), no customer means a cash sale, unless part of it was left unpaid.
    bill = None
    if engine != "evon" and intent in TRANSACTIONAL:
        bill = parse_bill(toks, local["tags"], surface_tokens(transcript))
    if bill:
        amount = bill["total"]
        names_in_bill = [ln["item"] for ln in bill["lines"] if ln["item"]]
        item = ", ".join(dict.fromkeys(names_in_bill)) or item
        if intent != "EXPENSE":   # restocking from a wholesaler stays an expense, with the computed total
            who = resolve_customer(spoken, transcript, customers)
            unpaid = bill["paid"] is None or bill["paid"] < bill["total"]
            if who["status"] != "none":
                intent = "CREDIT"
            elif unpaid and (bill["paid"] is not None or set(toks) & CREDIT_CUES) and not (
                    bill["paid"] is None and set(toks) & CASH_CUES):
                intent = "CREDIT"   # part or all left unpaid, but no name: ask whose account
            else:
                intent = "SALE"

    doubt = False
    if engine != "evon" and intent in ("CREDIT", "PAYMENT") and not bill:
        p = local.get("proba", {})
        doubt = p.get("PAYMENT" if intent == "CREDIT" else "CREDIT", 0.0) > DIRECTION_DOUBT

    if intent in ("SALE", "EXPENSE", "SUMMARY", "DEBTORS", "UNDO", "OTHER", "STOCK") or (
            intent == "QUERY" and query.get("customer_status") in (None, "none")):
        cust = {"status": "none", "id": None, "name": None, "candidates": []}
    else:
        cust = resolve_customer(spoken, transcript, customers)

    return {
        "intent": intent, "confidence": round(conf, 3), "engine": engine,
        "customer": cust, "amount": amount, "item": item, "quantity": qty, "unit": unit,
        "day_offset": day, "period": period, "settle_all": settle, "direction_doubt": doubt,
        "cut_start": cut_off_start(toks) and not restock, "bill": bill, "query": query, "stock": stock_cmd,
        "amount_options": amount_conflict(nums) if engine != "evon" and intent in TRANSACTIONAL and not bill else [],
        "audio_check": repeat_detector.assess(local, transcript, audio) if intent in TRANSACTIONAL else None,
        "local": {k: local[k] for k in ("intent", "confidence", "alternatives", "names", "items", "masked",
                                         "tokens", "tags", "tag_confidence")}
                 | {"ms": local_ms},
        "evon": ({k: v for k, v in ev.items()} if ev else None), "evon_error": ev_err,
    }
