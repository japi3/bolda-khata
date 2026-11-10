"""Smart questions about the ledger, answered exactly from the database.

    "ਪੰਜ ਹਜ਼ਾਰ ਤੋਂ ਵੱਧ ਕਿਸ ਕਿਸ ਵੱਲ ਬਾਕੀ ਹੈ?"      -> debtors_over  > ₹5,000
    "ਬਿੱਟੂ ਨੇ ਇਸ ਮਹੀਨੇ ਕਿੰਨਾ ਸਮਾਨ ਲਿਆ?"          -> total  credit, this month, Bittu
    "ਕੱਲ੍ਹ ਕਿੰਨਾ ਉਧਾਰ ਗਿਆ?"                        -> total  credit, yesterday, whole shop
    "ਮਹੀਨੇ ਤੋਂ ਕਿਸ ਨੇ ਪੈਸੇ ਨਹੀਂ ਦਿੱਤੇ?"             -> not_paid  30 days
    "ਮਾਸਟਰ ਜੀ ਨੇ ਇਸ ਮਹੀਨੇ ਕੀ ਕੀ ਲਿਆ?"             -> items  this month, Master ji

Deterministic on purpose, like the bill parser: the answer is a sum of money, so which question was asked is
decided by explicit word rules a reviewer can read (question word + what is asked about + time window).
Returns None unless the sentence clearly is one of these questions, so ordinary commands and the existing
balance / debtors / summary questions are left exactly as they were.
"""
from .punjabi import find_numbers, normalize

_N = lambda words: {normalize(w) for w in words.split()}  # noqa: E731

HOW_MUCH = _N("ਕਿੰਨਾ ਕਿੰਨੇ ਕਿੰਨੀ ਕਿੰਨੀਆਂ कितना कितने कितनी kitna kitne kitni kinna kinne kinni")
WHO = _N("ਕੌਣ ਕਿਸ ਕਿਸਨੇ ਕਿਹੜੇ ਕਿਹੜਾ ਕਿਹੜੀ ਕਿਨ੍ਹਾਂ ਕਿੰਨ੍ਹਾਂ कौन किस किसने किसका किसके किन किन्हें "
         "who whom which kaun kis kisne kiska kiske kin")
WHAT = _N("ਕੀ क्या what kya")
GT = _N("ਵੱਧ ਜ਼ਿਆਦਾ ਉੱਪਰ ਉੱਤੇ ਉਪਰ ਵਧ ज़्यादा ज्यादा अधिक ऊपर zyada jyada jada upar more above over greater")
LT = _N("ਘੱਟ ਥੱਲੇ कम नीचे kam less below under fewer")
DEBT = _N("ਬਾਕੀ ਬਕਾਇਆ ਉਧਾਰ ਦੇਣੇ ਰਹਿੰਦੇ ਖੜ੍ਹੇ बाकी बकाया उधार owe owes owed due dues balance udhaar udhar "
          "baki baaki pending outstanding")
# "what is still owed" is the existing balance / debtors question, not a total of what happened
OWED_NOW = _N("ਬਾਕੀ ਬਕਾਇਆ ਰਹਿੰਦੇ ਦੇਣੇ ਖੜ੍ਹੇ बाकी बकाया owe owes owed due dues balance baki baaki pending outstanding")
NEG = _N("ਨਹੀਂ ਨਹੀ ਨਾ नहीं नही ना nahi nahin not never hasn haven didn doesn don")
PAY = _N("ਪੈਸੇ ਜਮ੍ਹਾ ਦਿੱਤੇ ਦਿੱਤਾ ਦੇਣ ਭੁਗਤਾਨ पैसे जमा दिए दिया देने भुगतान paid pay payment paise jama diye diya")

SALE = _N("ਵਿਕਰੀ ਵਿਕਿਆ ਵਿਕੀ ਵਿਕੇ ਵੇਚਿਆ ਵੇਚੇ बिक्री बिका बिकी बिके बेचा बेचे sale sales sold sell bikri vikri")
EXPENSE = _N("ਖਰਚਾ ਖਰਚ ਖਰਚੇ ਖ਼ਰਚਾ खर्चा खर्च खर्चे expense expenses spent spend kharcha kharch")
CREDIT = _N("ਉਧਾਰ ਉਧਾਰੀ उधार credit udhaar udhar")
COLLECT = _N("ਜਮ੍ਹਾ ਵਾਪਸ ਉਗਰਾਹੀ ਵਸੂਲੀ ਭੁਗਤਾਨ ਭਰੇ ਭਰਿਆ भरे भरा भरी bhare bhara जमा वापस वसूली भुगतान collect collected collection received "
             "paid pay payment payments jama vasooli wapas vapas")
CAME = _N("ਆਏ ਆਇਆ आए आया aaye aaya came")
MONEY = _N("ਪੈਸੇ ਪੈਸਾ पैसे पैसा paise paisa money")
GAVE = _N("ਦਿੱਤੇ ਦਿੱਤਾ ਦਿੱਤੀ दिए दिया दी diye diya gave give")
TOOK = _N("ਲਿਆ ਲਏ ਲਈ ਲੈ ਸਮਾਨ ਸਾਮਾਨ लिया लिए ली ले सामान liya liye le saman samaan took take taken "
          "buy bought purchase purchased")

DAY_UNIT = _N("ਦਿਨ ਦਿਨਾਂ ਦਿਨਾਂ दिन दिनों day days din dino")
WEEK_UNIT = _N("ਹਫ਼ਤੇ ਹਫ਼ਤਾ ਹਫ਼ਤਿਆਂ हफ़्ते हफ़्ता हफ़्तों week weeks hafte hafta hafton")
MONTH_UNIT = _N("ਮਹੀਨੇ ਮਹੀਨਾ ਮਹੀਨਿਆਂ महीने महीना महीनों month months mahine mahina mahino")
LAST = _N("ਪਿਛਲੇ ਪਿਛਲਾ ਪਿਛਲੀ पिछले पिछला पिछली last previous pichle pichhle pichla pichhla")
SO_FAR = _N("ਕੁੱਲ कुल kul ever")   # plus the phrases checked in _window ("ਹੁਣ ਤੱਕ", "so far", ...)
TODAY = _N("ਅੱਜ आज aaj today")
YESTERDAY = _N("ਕੱਲ੍ਹ ਕੱਲ कल kal yesterday")
DAY_BEFORE = _N("ਪਰਸੋਂ परसों parson parso")
ONE = _N("ਇੱਕ ਇਕ एक ek a an one")
# "दो" alone is skipped as a number (it also means "give"), but before a time word it is always "two"
TWO = _N("दो do")


def _count_before(toks, i, nums) -> float | None:
    """Number right before token i ("ਦੋ ਹਫ਼ਤਿਆਂ", "15 days"), 1 for "a / ਇੱਕ / ek", else None."""
    for n in nums:
        if n["end"] == i:
            return n["value"]
    if i > 0 and toks[i - 1] in ONE:
        return 1.0
    if i > 0 and toks[i - 1] in TWO:
        return 2.0
    return None


def _durations(toks, nums):
    """[(start_token, end_token, days)] for "2 weeks", "a month", "10 ਦਿਨਾਂ"."""
    out = []
    for i, t in enumerate(toks):
        mult = 1 if t in DAY_UNIT else 7 if t in WEEK_UNIT else 30 if t in MONTH_UNIT else None
        if mult:
            c = _count_before(toks, i, nums)
            out.append((i - (1 if c is not None else 0), i + 1, (c or 1) * mult, c is not None, mult))
    return out


def _window(toks, nums, default):
    s, joined = set(toks), " ".join(toks)
    for start, end, days, counted, mult in _durations(toks, nums):
        if mult == 1 and counted:          # "ਪਿਛਲੇ 10 ਦਿਨਾਂ", "last 7 days"
            return {"window": "days", "n": int(days)}
    last = bool(s & LAST)
    if s & WEEK_UNIT:
        return {"window": "last_week" if last else "this_week"}
    if s & MONTH_UNIT:
        return {"window": "last_month" if last else "this_month"}
    if "day before yesterday" in joined or s & DAY_BEFORE:
        return {"window": "day_before"}
    if s & YESTERDAY:
        return {"window": "yesterday"}
    if s & TODAY:
        return {"window": "today"}
    if s & SO_FAR or any(p in joined for p in ("so far", "till now", "ab tak", normalize("ਹੁਣ ਤੱਕ"),
                                                  normalize("अब तक"))):
        return {"window": "all"}
    return {"window": default}


def _kind(s: set, has_customer: bool) -> str | None:
    if s & EXPENSE:
        return "expense"
    if s & SALE:
        return "sale"
    if s & CREDIT:
        return "credit"
    if s & COLLECT or (s & MONEY and s & CAME):
        return "payment"
    if has_customer and s & GAVE and (s & MONEY or not s & TOOK):
        return "payment"   # "ਕੁਲਦੀਪ ਨੇ ਕਿੰਨੇ ਪੈਸੇ ਦਿੱਤੇ" = how much did Kuldeep pay
    if s & TOOK:
        return "credit"    # "ਬਿੱਟੂ ਨੇ ਕਿੰਨਾ ਸਮਾਨ ਲਿਆ" = how much did Bittu take (on his account)
    return None


def parse_query(toks: list[str], customer: dict) -> dict | None:
    """customer: the resolved customer dict ({status, id, name, candidates}) for any name in the sentence."""
    s = set(toks)
    nums = find_numbers(toks)
    durations = _durations(toks, nums)
    in_duration = {k for st, en, *_ in durations for k in range(st, en)}
    has_cust = customer.get("status") in ("match", "ambiguous", "new") and bool(customer.get("name"))
    cust = {"customer": customer.get("name") if customer.get("status") == "match" else None,
            "customer_id": customer.get("id") if customer.get("status") == "match" else None,
            "customer_status": customer.get("status"), "customer_spoken": customer.get("name"),
            "candidates": customer.get("candidates") or []}
    question = bool(s & (WHO | HOW_MUCH | WHAT)) or (toks[:2] == ["how", "much"])

    # 1. who has not paid for a while
    if s & NEG and s & PAY and s & WHO:
        days = next((d for st, en, d, *_ in durations), 30)
        return {"type": "not_paid", "days": int(days)}

    # 2. dues above / below an amount
    if s & WHO and s & (GT | LT):
        for n in nums:
            if n["start"] in in_duration:
                continue
            near = set(toks[max(0, n["start"] - 3):n["end"] + 3])
            if near & (GT | LT):
                return {"type": "debtors_over", "op": ">" if near & GT else "<", "value": n["value"]}

    if not question or s & OWED_NOW:
        return None
    if any(n["role"] in ("amount_explicit",) or (n["start"] not in in_duration and n["role"] == "amount")
           for n in nums):
        return None   # an amount in the sentence makes it an entry, not a question about the past

    # 3. what did a customer take
    if has_cust and s & WHAT and s & TOOK and not s & HOW_MUCH:
        return {"type": "items", **_window(toks, nums, "all"), **cust}

    # 4. how much (credit / payments / sales / expenses), for one customer or the whole shop
    if s & HOW_MUCH or toks[:2] == ["how", "much"]:
        kind = _kind(s, has_cust)
        if kind is None:
            return None
        if kind in ("sale", "expense"):
            has_cust = False
        # "ਰਮੇਸ਼ ਦੀ ਉਧਾਰੀ ਕਿੰਨੀ ਹੋ ਗਈ?", "ਟੋਟਲ ਉਧਾਰ ਕਿੰਨਾ ਗਿਆ ਹੋਇਆ?": credit with no time and no "took" asks what
        # is owed NOW, which the existing balance / debtors answers give; a history total needs a time or a verb
        if kind == "credit" and not s & TOOK and _window(toks, nums, None)["window"] in (None, "all"):
            return None
        return {"type": "total", "kind": kind, **_window(toks, nums, "all" if has_cust else "today"),
                **(cust if has_cust else {"customer": None, "customer_id": None, "customer_status": "none"})}
    return None
