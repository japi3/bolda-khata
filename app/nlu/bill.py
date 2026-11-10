"""Multi-part bills in one sentence: quantity × rate, several priced items, and money paid now.

    "Ramesh ko 2 kilo chini 40 rupaye kilo udhaar diya aur 100 nagad liya"
      -> line: chini 2 kilo × ₹40 = ₹80;  total ₹80;  paid now ₹100  (₹20 extra: change or advance?)
    "ਬਿੱਟੂ ਨੇ 500 ਦਾ ਸਮਾਨ ਲਿਆ, 200 ਦੇ ਗਿਆ"            -> total ₹500, paid ₹200, ₹300 on credit
    "ਖੰਡ 90 ਦੀ ਤੇ ਤੇਲ 150 ਦਾ, ਨਕਦ"                     -> two items, total ₹240, cash sale

Deterministic on purpose: this is arithmetic on money, so every number's role is decided by explicit
rules a shopkeeper (or a reviewer) can check, using the item tags from the language model only to
label lines. Returns None unless the sentence really is a bill, so ordinary one-amount commands are
untouched.
"""
from .punjabi import RUPEE_WORDS, UNIT_WORDS, find_numbers, normalize

_N = lambda words: {normalize(w) for w in words.split()}  # noqa: E731

PER = _N("per prati ਪ੍ਰਤੀ प्रति har ਹਰ हर")
RATE_WORDS = _N("ਭਾਅ भाव bhaav bhav bhao rate ਰੇਟ रेट")
EACH = _N("ਵਾਲਾ ਵਾਲੇ ਵਾਲੀ ਵਾਲੀਆਂ वाला वाले वाली wala wale wali each ea")
# money received right now (not "gave goods"): cash words, deposit words, "gave [money] and left", "we took"
PAID = _N("ਨਕਦ ਕੈਸ਼ नकद कैश cash nagad naqad ਜਮ੍ਹਾ जमा jama ਮਿਲੇ मिले mile received got paid "
          "ਲਏ लिए liye liya ਫੜਾਏ ਦੇ_ਗਿਆ "
          # paying by app counts as money paid now
          "ਗੂਗਲ गूगल google ਪੇ पे pay upi ਯੂਪੀਆਈ यूपीआई phonepe ਫੋਨਪੇ फोनपे paytm ਪੇਟੀਐਮ online ਆਨਲਾਈਨ ऑनलाइन")
PAID_PAIRS = {(normalize(a), normalize(b)) for a, b in (
    ("ਦੇ", "ਗਿਆ"), ("ਦੇ", "ਗਈ"), ("ਦੇ", "ਗਏ"), ("दे", "गया"), ("दे", "गई"), ("de", "gaya"), ("de", "gayi"),
    ("ਦਿੱਤੇ", ""), ("दिए", ""), ("diye", ""))}
NOTE = _N("ਨੋਟ नोट note")
GAVE_EN = {"gave", "give", "given", "handed"}
PRICE_BEFORE = _N("for worth")
TOTAL_WORDS = _N("ਕੁੱਲ कुल kul total ਟੋਟਲ टोटल")
PRICE_OF = _N("ਦਾ ਦੀ ਦੇ ਦੀਆਂ का की के ka ki ke worth")


def _is_rate(toks, n) -> tuple[bool, str | None]:
    """'40 ਰੁਪਏ ਕਿੱਲੋ', '45 per kg', '₹40 kg', '10 ਵਾਲੇ', '60 ਦੇ ਭਾਅ' -> rate (per unit)."""
    i = n["end"]
    prev = toks[n["start"] - 1] if n["start"] > 0 else ""
    had_rupee = prev in ("₹", "rs")
    if i < len(toks) and toks[i] in RUPEE_WORDS:
        had_rupee, i = True, i + 1
    nxt = toks[i] if i < len(toks) else ""
    nxt2 = toks[i + 1] if i + 1 < len(toks) else ""
    if nxt in PER and nxt2 in UNIT_WORDS:
        return True, nxt2
    if had_rupee and nxt in UNIT_WORDS:
        return True, nxt
    if nxt in EACH or nxt in RATE_WORDS or (nxt in PRICE_OF and nxt2 in RATE_WORDS):
        return True, None
    if nxt in PRICE_OF and nxt2 in UNIT_WORDS:   # "56 ਦਾ ਲੀਟਰ" = 56 a litre
        return True, nxt2
    return False, None


def _is_paid(toks, n) -> bool:
    nxt = toks[n["end"]] if n["end"] < len(toks) else ""
    nxt2 = toks[n["end"] + 1] if n["end"] + 1 < len(toks) else ""
    prev = toks[n["start"] - 1] if n["start"] > 0 else ""
    if (nxt, nxt2) in PAID_PAIRS:          # "100 ਦੇ ਗਿਆ": ਦੇ here is "gave", not "of"
        return True
    if prev in GAVE_EN:                     # "gave 200": money handed over ("gave Ramesh 200" has a name between)
        return True
    if nxt in PRICE_OF and nxt2 in NOTE:    # "500 का नोट दिया" = handed over a 500 note
        return True
    if nxt in PRICE_OF or prev in PRICE_BEFORE:   # "150 ਦਾ", "for 150": an item's price, not money paid
        return False
    lo, hi = max(0, n["start"] - 2), min(len(toks), n["end"] + 3)
    window = toks[lo:n["start"]] + toks[n["end"]:hi]
    if set(window) & PAID:
        return True
    after = toks[n["end"]:hi] + [""]
    return any((a, b) in PAID_PAIRS or (a, "") in PAID_PAIRS for a, b in zip(after, after[1:]))


def _item_near(tags, toks, start, end, items_by_pos):
    """Item span closest to [start, end) within 4 tokens (left preferred), else None."""
    best, dist = None, 99
    for pos, name in items_by_pos:
        if start <= pos < end:   # "2 kilo CHINI 40 rupaye": item between quantity and rate
            return name
        d = start - pos if pos < start else pos - end + 1
        if 0 <= d <= 4 and d < dist:
            best, dist = name, d
    return best


def parse_bill(toks: list[str], tags: list[str] | None = None, surf: list[str] | None = None) -> dict | None:
    nums = find_numbers(toks)
    if len(nums) < 2:
        return None
    tags = tags or ["O"] * len(toks)
    surf = surf if surf and len(surf) == len(toks) else toks
    items_by_pos, cur = [], None
    for i, t in enumerate(tags):
        if t == "B-ITEM":
            cur = [i, [surf[i]]]
            items_by_pos.append(cur)
        elif t == "I-ITEM" and cur is not None:
            cur[1].append(surf[i])
        else:
            cur = None
    items_by_pos = [(p, " ".join(ws)) for p, ws in items_by_pos]

    lines, prices, paid, total_explicit, last_qty = [], [], None, None, None
    item_starts = {p for p, _ in items_by_pos}
    for k, n in enumerate(nums):
        if n["role"] == "quantity":
            rate, unit = _is_rate(toks, n)
            if not rate:   # "2 ਕਿੱਲੋ" is a quantity waiting for its rate
                last_qty = n
                continue
        # a count with no unit: "आठ अंडे 7 रुपये वाले" (eight eggs at 7 each) - number right before an
        # item name, followed by a rate
        nxt_is_rate = k + 1 < len(nums) and _is_rate(toks, nums[k + 1])[0]
        if n["end"] in item_starts and nxt_is_rate and not _is_rate(toks, n)[0]:
            last_qty = {**n, "unit": None}
            continue
        rate, unit = _is_rate(toks, n)
        prev = toks[n["start"] - 1] if n["start"] > 0 else ""
        if rate:
            q = last_qty
            qty = q["value"] if q else 1.0
            item = _item_near(tags, toks, (q or n)["start"], n["end"], items_by_pos)
            lines.append({"item": item, "qty": qty, "unit": (q["unit"] if q else unit), "rate": n["value"],
                          "amount": round(qty * n["value"], 2)})
            last_qty = None
        elif prev in TOTAL_WORDS:
            total_explicit = n["value"]
        elif _is_paid(toks, n) and paid is None:
            paid = n["value"]
        else:
            item = _item_near(tags, toks, n["start"], n["end"], items_by_pos)
            q = last_qty if last_qty and n["start"] - last_qty["end"] <= 4 else None
            prices.append({"item": item, "qty": q["value"] if q else None, "unit": q["unit"] if q else None,
                           "rate": None, "amount": n["value"]})
            last_qty = None

    priced_items = [p for p in prices if p["item"]]
    is_bill = bool(lines) or (paid is not None and (prices or total_explicit)) or len(priced_items) >= 2
    if not is_bill:
        return None
    # When the sentence is a list of items, every price belongs to the bill; with no item names,
    # only one plain price can be the bill amount (the others would be ambiguous, so not a bill).
    if not lines and len(prices) > 1 and len(priced_items) < len(prices):
        return None
    all_lines = lines + prices
    total = total_explicit if total_explicit is not None else round(sum(x["amount"] for x in all_lines), 2)
    if total <= 0:
        return None
    return {"lines": all_lines, "total": total, "paid": paid,
            "due": round(total - (paid or 0), 2)}   # negative = paid more than the bill
