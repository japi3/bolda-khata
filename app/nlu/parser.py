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
from .punjabi import amount_conflict, date_offset, find_numbers, normalize, pick_amount, pick_quantity

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


CREDIT_CUES = {normalize(w) for w in "ਉਧਾਰ ਉਧਾਰੀ उधार udhaar udhar udhari credit".split()}
CASH_CUES = {normalize(w) for w in "ਨਕਦ ਕੈਸ਼ नकद कैश cash naqad nakad".split()}
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
        spoken = local["names"][0] if local["names"] else None
        item = local["items"][0] if local["items"] else None
        day = date_offset(toks)
        period = _period(toks)
        settle = intent == "PAYMENT" and amount is None and bool(set(toks) & SETTLE_WORDS)
        engine = nlu().name

    # "udhaar" means credit, so it can never be a cash sale. Found on real recordings: when the customer's
    # name was lost at the start ("(Bittu) ko 320 udhaar diya"), the model guessed SALE and would have
    # silently booked credit as cash. As CREDIT with no name, the app asks "whose account?" instead.
    if intent == "SALE" and set(toks) & CREDIT_CUES and not set(toks) & CASH_CUES:
        intent = "CREDIT"

    doubt = False
    if engine != "evon" and intent in ("CREDIT", "PAYMENT"):
        p = local.get("proba", {})
        doubt = p.get("PAYMENT" if intent == "CREDIT" else "CREDIT", 0.0) > DIRECTION_DOUBT

    if intent in ("SALE", "EXPENSE", "SUMMARY", "DEBTORS", "UNDO", "OTHER"):
        cust = {"status": "none", "id": None, "name": None, "candidates": []}
    else:
        cust = resolve_customer(spoken, transcript, customers)

    return {
        "intent": intent, "confidence": round(conf, 3), "engine": engine,
        "customer": cust, "amount": amount, "item": item, "quantity": qty, "unit": unit,
        "day_offset": day, "period": period, "settle_all": settle, "direction_doubt": doubt,
        "cut_start": cut_off_start(toks),
        "amount_options": amount_conflict(nums) if engine != "evon" and intent in TRANSACTIONAL else [],
        "audio_check": repeat_detector.assess(local, transcript, audio) if intent in TRANSACTIONAL else None,
        "local": {k: local[k] for k in ("intent", "confidence", "alternatives", "names", "items", "masked",
                                         "tokens", "tags", "tag_confidence")}
                 | {"ms": local_ms},
        "evon": ({k: v for k, v in ev.items()} if ev else None), "evon_error": ev_err,
    }
