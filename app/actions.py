"""Execute an understood command against the ledger and compose the spoken reply.

Every reply carries three languages: Punjabi ("pa"), English ("en") and Hindi ("hi").
The UI shows and Timbre speaks the one the shopkeeper chose.
"""
import re
import time

from . import db, stock
from .ml import risk
from .nlu import evon
from .nlu.punjabi import rupees_text as R
from .nlu.translit import guru_to_deva, is_devanagari, to_roman

LOW_CONF = 0.45
KIND = {"CREDIT": "credit", "PAYMENT": "payment", "SALE": "sale", "EXPENSE": "expense"}
_LATIN = re.compile(r"^[\x00-\x7F]+$")


_HI_SPELLING = {"सिंघ": "सिंह", "मासटर": "मास्टर", "सटोर": "स्टोर", "डाकटर": "डॉक्टर", "करिआना": "किराना"}


def H(name: str | None) -> str:
    """A name or shop name in Devanagari for Hindi replies (Latin names stay as they are)."""
    if not name or _LATIN.match(name) or is_devanagari(name):
        return name or ""
    out = guru_to_deva(name)
    for pa_style, hi_style in _HI_SPELLING.items():   # Punjabi spellings that Hindi writes differently
        out = out.replace(pa_style, hi_style)
    return out


def E(name: str | None) -> str:
    return to_roman(name or "")


def _r(pa: str, en: str, hi: str, action: str, **data) -> dict:
    return {"pa": pa, "en": en, "hi": hi, "action": action, **data}


# ---- bills: units and line text in each language
_UNIT_GROUPS = {
    "kg": ("ਕਿੱਲੋ", "kg", "किलो", "ਕਿੱਲੋ kg kgs kilo kilos kilogram kilograms किलो"),
    "g": ("ਗ੍ਰਾਮ", "g", "ग्राम", "ਗ੍ਰਾਮ gram grams g ग्राम"),
    "l": ("ਲੀਟਰ", "litre", "लीटर", "ਲੀਟਰ litre litres liter liters l लीटर"),
    "pkt": ("ਪੈਕਟ", "packet", "पैकेट", "ਪੈਕਟ ਪੈਕਟਾਂ पैकेटों packet packets pack packs पैकेट"),
    "dz": ("ਦਰਜਨ", "dozen", "दर्जन", "ਦਰਜਨ dozen दर्जन"),
    "sack": ("ਬੋਰੀ", "sack", "बोरी", "ਬੋਰੀ ਬੋਰੀਆਂ ਗੱਟਾ ਗੱਟੇ बोरियां बोरियाँ sack sacks bag bags बोरी"),
    "pc": ("ਪੀਸ", "piece", "पीस", "ਪੀਸ piece pieces pcs पीस"),
    "box": ("ਡੱਬਾ", "box", "डिब्बा", "ਡੱਬਾ ਡੱਬੇ ਡੱਬਿਆਂ डिब्बों box boxes tin tins डिब्बा डिब्बे"),
    "crate": ("ਪੇਟੀ", "crate", "पेटी", "ਪੇਟੀ ਪੇਟੀਆਂ पेटी पेटियां पेटियाँ crate crates"),
    "btl": ("ਬੋਤਲ", "bottle", "बोतल", "ਬੋਤਲ ਬੋਤਲਾਂ bottle bottles बोतल बोतलें"),
    "cup": ("ਕੱਪ", "cup", "कप", "ਕੱਪ cup cups"),
    "thaila": ("ਥੈਲਾ", "bag", "थैला", "ਥੈਲਾ ਥੈਲੇ थैला थैले"),
}


def _unit(u: str | None) -> tuple[str, str, str]:
    if not u:
        return "", "", ""
    from .nlu.punjabi import normalize
    for pa, en, hi, words in _UNIT_GROUPS.values():
        if u in {normalize(w) for w in words.split()}:
            return pa, en, hi
    return u, E(u), H(u)


def _num(x: float) -> str:
    return str(int(x)) if x == int(x) else f"{x:g}"


def bill_lines(bill: dict) -> tuple[list[str], list[str], list[str]]:
    """'ਚੌਲ 3 ਕਿੱਲੋ × ₹60 = ₹180' for each line, in pa / en / hi."""
    pa, en, hi = [], [], []
    for ln in bill["lines"]:
        up, ue, uh = _unit(ln.get("unit"))
        item = ln.get("item") or ""
        ip, ie, ih = item or "ਸਮਾਨ", E(item) or "items", H(item) or "सामान"
        if ln.get("rate") is not None:
            q = _num(ln["qty"])
            pa.append(f"{ip} {q} {up} × {R(ln['rate'])} = {R(ln['amount'])}".replace("  ", " "))
            en.append(f"{ie} {q} {ue} × {R(ln['rate'])} = {R(ln['amount'])}".replace("  ", " "))
            hi.append(f"{ih} {q} {uh} × {R(ln['rate'])} = {R(ln['amount'])}".replace("  ", " "))
        else:
            q = f" {_num(ln['qty'])} " if ln.get("qty") else " "
            pa.append(f"{ip}{q}{up if ln.get('qty') else ''} {R(ln['amount'])}".replace("  ", " "))
            en.append(f"{ie}{q}{ue if ln.get('qty') else ''} {R(ln['amount'])}".replace("  ", " "))
            hi.append(f"{ih}{q}{uh if ln.get('qty') else ''} {R(ln['amount'])}".replace("  ", " "))
    return pa, en, hi


def bill_view(bill: dict, **extra) -> dict:
    """The bill for the screen: numbers plus each line already written in pa / en / hi."""
    p, e, h = bill_lines(bill)
    return {**bill, **extra, "text": {"pa": p, "en": e, "hi": h}}


def _bill_summary(bill: dict) -> tuple[str, str, str]:
    """Spoken list of the lines, only when there is more than one line or a computed rate."""
    if len(bill["lines"]) == 1 and bill["lines"][0].get("rate") is None:
        return "", "", ""
    p, e, h = bill_lines(bill)
    return "ਬਿੱਲ: " + ", ".join(p) + "। ", "Bill: " + ", ".join(e) + ". ", "बिल: " + ", ".join(h) + "। "


def entry_ts(cmd: dict) -> float | None:
    """When the entry happened. A recording sent later from the phone's offline queue carries the time it was
    spoken (recorded_at), so it lands on the right day; "ਕੱਲ੍ਹ" (yesterday) shifts from that time, not from now."""
    ra = cmd.get("recorded_at")
    if not ra:
        return None
    return ra + (cmd.get("day_offset") or 0) * 86400


def _days_ago(ts: float | None) -> int | None:
    return None if ts is None else max(0, int((time.time() - ts) // 86400))


def _ask_repeat(cmd) -> dict:
    return _r("ਮਾਫ਼ ਕਰਨਾ, ਪੂਰੀ ਗੱਲ ਸਮਝ ਨਹੀਂ ਆਈ। ਇੱਕ ਵਾਰ ਫਿਰ ਬੋਲੋ, ਜਿਵੇਂ: ਰਮੇਸ਼ ਨੂੰ ਪੰਜ ਸੌ ਉਧਾਰ ਦਿੱਤਾ।",
              "Sorry, I didn't catch that fully. Please say it again, e.g. 'Gave Ramesh 500 on credit.'",
              "माफ़ कीजिए, पूरी बात समझ नहीं आई। एक बार फिर बोलिए, जैसे: रमेश को पांच सौ उधार दिया।",
              "clarify")


def reminder_text(name: str, bal: float, days: int | None, firm: bool, shop: str,
                  shop_en: str = "", shop_hi: str = "") -> tuple[str, str, str]:
    shop_en, shop_hi = shop_en or E(shop), shop_hi or H(shop)
    if firm:
        d = f" {days} ਦਿਨਾਂ ਤੋਂ" if days else ""
        pa = (f"ਸਤ ਸ੍ਰੀ ਅਕਾਲ {name} ਜੀ। {shop} ਵੱਲੋਂ ਯਾਦ ਦਿਵਾ ਰਹੇ ਹਾਂ ਕਿ ਤੁਹਾਡਾ {R(bal)} ਦਾ ਬਕਾਇਆ{d} ਖੜ੍ਹਾ ਹੈ। "
              f"ਕਿਰਪਾ ਕਰਕੇ ਇਸ ਹਫ਼ਤੇ ਭੁਗਤਾਨ ਕਰ ਦਿਓ। ਧੰਨਵਾਦ ਜੀ।")
        en = (f"Sat Sri Akal {E(name)} ji. A reminder from {shop_en} that your balance of "
              f"{R(bal)} has been pending{' for ' + str(days) + ' days' if days else ''}. Please pay this week. Thank you.")
        hi = (f"नमस्ते {H(name)} जी। {shop_hi} की तरफ़ से याद दिला रहे हैं कि आपका {R(bal)} का बकाया"
              f"{' ' + str(days) + ' दिनों से' if days else ''} बाकी है। कृपया इस हफ़्ते भुगतान कर दीजिए। धन्यवाद।")
    else:
        pa = (f"ਸਤ ਸ੍ਰੀ ਅਕਾਲ {name} ਜੀ। {shop} ਵੱਲੋਂ ਨਿੱਘੀ ਯਾਦ, ਤੁਹਾਡੇ ਖਾਤੇ ਵਿੱਚ {R(bal)} ਬਾਕੀ ਹਨ। "
              f"ਜਦੋਂ ਸਮਾਂ ਮਿਲੇ, ਹਿਸਾਬ ਕਰ ਜਾਣਾ। ਧੰਨਵਾਦ ਜੀ।")
        en = (f"Sat Sri Akal {E(name)} ji. A gentle reminder from {shop_en}: {R(bal)} is due on "
              f"your account. Please settle whenever convenient. Thank you.")
        hi = (f"नमस्ते {H(name)} जी। {shop_hi} की तरफ़ से एक याद, आपके खाते में {R(bal)} बाकी हैं। "
              f"जब समय मिले, हिसाब कर जाइए। धन्यवाद जी।")
    return pa, en, hi


def build_reminder(cid: int) -> dict | None:
    c = db.customer(cid)
    if not c or c["balance"] <= 0:
        return None
    s = risk.score_customer(cid)
    firm = s["band"]["key"] == "risky" or (s.get("oldest_unpaid_days") or 0) > 30
    st = db.get_settings()
    pa, en, hi = reminder_text(c["name"], c["balance"], int(s.get("oldest_unpaid_days") or 0) or None, firm,
                               st["shop_name"], st.get("shop_name_en", ""), st.get("shop_name_hi", ""))
    return {"customer_id": cid, "name": c["name"], "phone": c["phone"], "balance": c["balance"],
            "tone": "firm" if firm else "gentle", "pa": pa, "en": en, "hi": hi}


def ledger_context() -> str:
    """Compact, factual snapshot for Evon's grounded answers."""
    lines = []
    for label, (s, e) in {"ਅੱਜ": db.period_bounds("today"), "ਇਸ ਹਫ਼ਤੇ": db.period_bounds("week"),
                          "ਇਸ ਮਹੀਨੇ": db.period_bounds("month")}.items():
        x = db.summary(s, e)
        lines.append(f"{label}: ਨਕਦ ਵਿਕਰੀ {R(x['sale'])}, ਉਧਾਰ ਦਿੱਤਾ {R(x['credit'])}, "
                     f"ਉਧਾਰ ਵਾਪਸ ਆਇਆ {R(x['payment'])}, ਖਰਚਾ {R(x['expense'])}")
    owed = [c for c in db.customers() if c["balance"] > 0]
    lines.append(f"ਕੁੱਲ ਬਕਾਇਆ {R(sum(c['balance'] for c in owed))}, {len(owed)} ਗਾਹਕ")
    for c in owed[:15]:
        s = risk.score_customer(c["id"])
        lines.append(f"- {c['name']}: ਬਕਾਇਆ {R(c['balance'])}, ਭਰੋਸਾ ਸਕੋਰ {s['trust']}/100")
    return "\n".join(lines)


def precheck(cmd: dict) -> tuple[dict | None, float | None]:
    """Every question the app asks *before* acting, in order. Returns (question reply or None, amount).
    Shared by execute() and the evaluations, so reports measure exactly what the app does."""
    intent = cmd["intent"]
    cust = cmd["customer"]
    amount = cmd.get("amount")
    if intent in KIND:
        if cmd["confidence"] < LOW_CONF and cmd["engine"] != "evon":
            return _ask_repeat(cmd), amount
        if cmd.get("direction_doubt") and not cmd.get("direction_confirmed"):
            who = cust.get("name") or ""
            amt = f" {R(cmd['amount'])}" if cmd.get("amount") else ""
            return _r(f"{who}{amt}: ਇਹ ਪੈਸੇ ਮਿਲੇ ਹਨ (ਜਮ੍ਹਾ) ਜਾਂ ਉਧਾਰ ਦਿੱਤਾ ਹੈ?",
                      f"{E(who)}{amt}: did you receive this money, or give it on credit?",
                      f"{H(who)}{amt}: ये पैसे मिले हैं (जमा) या उधार दिया है?",
                      "confirm_direction", pending={**cmd, "awaiting": "direction"}), amount
        if cust["status"] == "ambiguous":
            cands = cust["candidates"]
            return _r(f"ਕਿਹੜੇ {cust['name']}? " + " ਜਾਂ ".join(c["name"] for c in cands) + "?",
                      f"Which {E(cust['name'])}? " + " or ".join(E(c['name']) for c in cands) + "?",
                      f"कौन से {H(cust['name'])}? " + " या ".join(H(c['name']) for c in cands) + "?",
                      "choose_customer", candidates=cands, pending=cmd), amount
        if intent == "PAYMENT" and amount is None and cmd.get("settle_all") and cust["id"]:
            amount = db.balance(cust["id"])
        opts = cmd.get("amount_options") or []
        if len(opts) > 1:
            return _r(f"ਕਿੰਨੇ ਪੈਸੇ ਲਿਖਾਂ: {' ਜਾਂ '.join(R(v) for v in opts)}?",
                      f"Which amount should I write: {' or '.join(R(v) for v in opts)}?",
                      f"कितने पैसे लिखूं: {' या '.join(R(v) for v in opts)}?", "ask_amount",
                      amount_choices=opts, pending={**cmd, "amount": None, "amount_options": []}), amount
        if not amount or amount <= 0:
            return _r("ਕਿੰਨੇ ਪੈਸੇ? ਰਕਮ ਦੱਸੋ ਜੀ।", "How much? Please say the amount.", "कितने पैसे? रकम बताइए।",
                      "ask_amount", pending=cmd), amount
        if intent in ("CREDIT", "PAYMENT") and (cust["status"] == "none" or not cust["name"]):
            return _ask_customer(cmd), amount
        bill = cmd.get("bill")
        if (intent == "CREDIT" and bill and bill.get("paid") is not None and bill["paid"] > bill["total"]
                and not cmd.get("extra_choice")):
            return _ask_change(cmd, bill), amount
        check = cmd.get("audio_check") or {}
        if check.get("unsure") and not cmd.get("heard_confirmed"):
            return _confirm_heard(cmd, intent, amount, check), amount
        # read back before writing when the start was cut off, or a new account would be created
        if not cmd.get("heard_confirmed"):
            if cmd.get("cut_start"):
                return _confirm_heard(cmd, intent, amount, {"reason": "cut"}), amount
            if intent in ("CREDIT", "PAYMENT") and cust["status"] == "new":
                return _confirm_heard(cmd, intent, amount, {"reason": "new"}), amount
        return None, amount
    # questions about one customer whose name was cut off: ask, don't answer for "everyone"
    if intent in ("BALANCE", "RISK", "REMIND") and cmd.get("cut_start") and not cust["id"]:
        return _ask_customer(cmd), amount
    return None, amount


async def execute(cmd: dict, voice_id: int | None = None) -> dict:
    intent = cmd["intent"]
    cust = cmd["customer"]
    if intent == "STOCK" and cmd.get("stock"):
        from .ledger_queries import stock_answer   # stock: counted, left, running low
        return stock_answer(cmd)
    if intent == "QUERY" and cmd.get("query"):
        from .ledger_queries import answer   # smart questions, answered exactly from the ledger
        return answer(cmd)
    question, amount = precheck(cmd)
    if question:
        return question
    if intent in KIND:
        if intent in ("CREDIT", "PAYMENT"):
            reply = await _customer_txn(cmd, intent, amount, voice_id)
        else:
            reply = _shop_txn(cmd, intent, amount, voice_id)
        return _with_stock(reply, KIND[intent], cmd)

    if intent == "BALANCE":
        if cust["status"] == "none":   # no name said ("ਕਿੰਨੇ ਪੈਸੇ?"): ask whose, don't claim it wasn't found
            return _r("ਕਿਸ ਦਾ ਹਿਸਾਬ? ਗਾਹਕ ਦਾ ਨਾਮ ਦੱਸੋ।", "Whose account? Please say the name.",
                      "किसका हिसाब? ग्राहक का नाम बताइए।", "ask_customer", pending=cmd)
        if not cust["id"]:
            return _r(f"'{cust['name']}' ਨਾਮ ਦਾ ਕੋਈ ਖਾਤਾ ਨਹੀਂ ਮਿਲਿਆ।", f"No account found for '{E(cust['name'])}'.",
                      f"'{H(cust['name'])}' नाम का कोई खाता नहीं मिला।", "not_found")
        c = db.customer(cust["id"])
        n, b = c["name"], c["balance"]
        last_pay = next((t for t in db.txns(cust["id"], 200) if t["kind"] == "payment"), None)
        if b > 0:
            pa, en, hi = f"{n} ਵੱਲ {R(b)} ਬਾਕੀ ਹਨ।", f"{E(n)} owes {R(b)}.", f"{H(n)} पर {R(b)} बाकी हैं।"
        elif b < 0:
            pa, en, hi = (f"{n} ਦੇ {R(-b)} ਐਡਵਾਂਸ ਜਮ੍ਹਾ ਹਨ।", f"{E(n)} has {R(-b)} in advance.",
                          f"{H(n)} के {R(-b)} एडवांस जमा हैं।")
        else:
            pa, en, hi = f"{n} ਦਾ ਖਾਤਾ ਸਾਫ਼ ਹੈ।", f"{E(n)}'s account is clear.", f"{H(n)} का खाता साफ़ है।"
        if last_pay and b > 0:
            d = _days_ago(last_pay["ts"])
            pa += f" ਆਖਰੀ ਭੁਗਤਾਨ {d} ਦਿਨ ਪਹਿਲਾਂ ਆਇਆ ਸੀ।" if d else " ਅੱਜ ਭੁਗਤਾਨ ਆਇਆ ਸੀ।"
            en += f" Last payment {d} days ago." if d else " Paid today."
            hi += f" आख़िरी भुगतान {d} दिन पहले आया था।" if d else " आज भुगतान आया था।"
        return _r(pa, en, hi, "show_customer", customer_id=c["id"])

    if intent == "DEBTORS":
        owed = [c for c in db.customers() if c["balance"] > 0]
        if not owed:
            return _r("ਕਿਸੇ ਵੱਲ ਵੀ ਕੋਈ ਬਕਾਇਆ ਨਹੀਂ ਹੈ।", "Nobody owes anything.", "किसी पर भी कोई बकाया नहीं है।",
                      "show_customers")
        total, top = sum(c["balance"] for c in owed), owed[:3]
        pa = (f"ਕੁੱਲ {R(total)} ਬਾਕੀ ਹਨ, {len(owed)} ਗਾਹਕਾਂ ਵੱਲ। ਸਭ ਤੋਂ ਵੱਧ: "
              + ", ".join(f"{c['name']} {R(c['balance'])}" for c in top) + "।")
        en = (f"{R(total)} outstanding across {len(owed)} customers. Highest: "
              + ", ".join(f"{E(c['name'])} {R(c['balance'])}" for c in top) + ".")
        hi = (f"कुल {R(total)} बाकी हैं, {len(owed)} ग्राहकों पर। सबसे ज़्यादा: "
              + ", ".join(f"{H(c['name'])} {R(c['balance'])}" for c in top) + "।")
        return _r(pa, en, hi, "show_customers")

    if intent == "SUMMARY":
        period = cmd.get("period") or "today"
        day = cmd.get("day_offset") or 0
        s, e = db.period_bounds(period, day)
        x = db.summary(s, e)
        lp = {"today": "ਅੱਜ" if day == 0 else "ਕੱਲ੍ਹ", "week": "ਇਸ ਹਫ਼ਤੇ", "month": "ਇਸ ਮਹੀਨੇ"}[period]
        le = {"today": "Today" if day == 0 else "Yesterday", "week": "This week", "month": "This month"}[period]
        lh = {"today": "आज" if day == 0 else "कल", "week": "इस हफ़्ते", "month": "इस महीने"}[period]
        pa = (f"{lp}: ਨਕਦ ਵਿਕਰੀ {R(x['sale'])}, ਉਧਾਰ ਦਿੱਤਾ {R(x['credit'])}, ਉਧਾਰ ਵਾਪਸ ਆਇਆ {R(x['payment'])}, "
              f"ਖਰਚਾ {R(x['expense'])}। ਗੱਲੇ ਵਿੱਚ ਕੁੱਲ {R(x['net_cash'])} ਆਏ।")
        en = (f"{le}: cash sales {R(x['sale'])}, credit given {R(x['credit'])}, collected {R(x['payment'])}, "
              f"expenses {R(x['expense'])}. Net cash {R(x['net_cash'])}.")
        hi = (f"{lh}: नकद बिक्री {R(x['sale'])}, उधार दिया {R(x['credit'])}, उधार वापस आया {R(x['payment'])}, "
              f"खर्चा {R(x['expense'])}। गल्ले में कुल {R(x['net_cash'])} आए।")
        return _r(pa, en, hi, "show_summary", period=period, summary=x)

    if intent == "UNDO":
        t = db.last_txn()
        ls = stock.last_set()
        if ls and (not t or ls["created_at"] > t["created_at"]):   # the last thing said was a stock count
            stock.undo_set(ls["id"])
            p, e, h = stock.names(ls["item_key"]) if ls["item_key"] in stock.CATALOG else (ls["item_key"],) * 3
            return _r(f"ਸਟਾਕ ਦੀ ਪਿਛਲੀ ਗਿਣਤੀ ({p}) ਕੱਟ ਦਿੱਤੀ।", f"Removed the last stock count ({e}).",
                      f"स्टॉक की पिछली गिनती ({h}) हटा दी।", "undone")
        if not t:
            return _r("ਕੱਟਣ ਲਈ ਕੋਈ ਐਂਟਰੀ ਨਹੀਂ ਹੈ।", "There is no entry to undo.", "हटाने के लिए कोई एंट्री नहीं है।", "none")
        db.set_deleted(t["id"], True)
        if t.get("group_id"):
            g = db.group_txns(t["group_id"])
            bill = next((x for x in g if x["kind"] == "credit"), t)
            got = sum(x["amount"] for x in g if x["kind"] == "payment")
            c = bill["customer"]
            gp = f", {R(got)} ਜਮ੍ਹਾ" if got else ""
            ge = f", {R(got)} received" if got else ""
            gh = f", {R(got)} जमा" if got else ""
            return _r(f"ਪਿਛਲਾ ਪੂਰਾ ਬਿੱਲ ({c}, {R(bill['amount'])} ਉਧਾਰ{gp}) ਕੱਟ ਦਿੱਤਾ।",
                      f"Removed the whole last bill ({E(c)}, {R(bill['amount'])} credit{ge}).",
                      f"पिछला पूरा बिल ({H(c)}, {R(bill['amount'])} उधार{gh}) हटा दिया।",
                      "undone", txn_id=t["id"], group_id=t["group_id"])
        k = t["kind"]
        kp = {"credit": "ਉਧਾਰ", "payment": "ਜਮ੍ਹਾ", "sale": "ਵਿਕਰੀ", "expense": "ਖਰਚਾ"}[k]
        kh = {"credit": "उधार", "payment": "जमा", "sale": "बिक्री", "expense": "खर्चा"}[k]
        c = t["customer"]
        return _r(f"ਪਿਛਲੀ ਐਂਟਰੀ ({c + ', ' if c else ''}{R(t['amount'])} {kp}) ਕੱਟ ਦਿੱਤੀ।",
                  f"Removed the last entry ({E(c) + ', ' if c else ''}{R(t['amount'])} {k}).",
                  f"पिछली एंट्री ({H(c) + ', ' if c else ''}{R(t['amount'])} {kh}) हटा दी।",
                  "undone", txn_id=t["id"])

    if intent == "RISK":
        if cust["id"]:
            return _risk_reply(cust["id"])
        p = risk.portfolio()
        risky = [r for r in p["customers"] if r["balance"] > 0 and r["score"]["band"]["key"] == "risky"][:3]
        if not risky:
            return _r("ਇਸ ਵੇਲੇ ਕੋਈ ਵੀ ਗਾਹਕ ਖਤਰੇ ਵਾਲਾ ਨਹੀਂ ਲੱਗਦਾ।", "No customer looks risky right now.",
                      "इस समय कोई भी ग्राहक ख़तरे वाला नहीं लगता।", "show_insights")
        return _r("ਧਿਆਨ ਰੱਖੋ: " + ", ".join(f"{r['name']} (ਸਕੋਰ {r['score']['trust']})" for r in risky) + "।",
                  "Be careful with: " + ", ".join(f"{E(r['name'])} (score {r['score']['trust']})" for r in risky) + ".",
                  "ध्यान रखें: " + ", ".join(f"{H(r['name'])} (स्कोर {r['score']['trust']})" for r in risky) + "।",
                  "show_insights")

    if intent == "REMIND":
        if cust["id"]:
            rem = build_reminder(cust["id"])
            n = cust["name"]
            if not rem:
                return _r(f"{n} ਵੱਲ ਕੋਈ ਬਕਾਇਆ ਨਹੀਂ, ਯਾਦ ਕਰਵਾਉਣ ਦੀ ਲੋੜ ਨਹੀਂ।", f"{E(n)} owes nothing, no reminder needed.",
                          f"{H(n)} पर कोई बकाया नहीं, याद दिलाने की ज़रूरत नहीं।", "none")
            return _r(f"{n} ਲਈ ਯਾਦ-ਸੁਨੇਹਾ ਤਿਆਰ ਹੈ। ਸੁਣ ਕੇ ਵਟਸਐਪ ਤੇ ਭੇਜ ਦਿਓ।",
                      f"Reminder voice note for {E(n)} is ready. Listen, then send it on WhatsApp.",
                      f"{H(n)} के लिए याद-संदेश तैयार है। सुनकर व्हाट्सएप पर भेज दीजिए।",
                      "reminder", reminders=[rem])
        owed = [c for c in db.customers() if c["balance"] > 0]
        rems = [r for r in (build_reminder(c["id"]) for c in owed[:5]) if r]
        if not rems:
            return _r("ਕਿਸੇ ਵੱਲ ਬਕਾਇਆ ਨਹੀਂ ਹੈ।", "Nobody owes anything.", "किसी पर बकाया नहीं है।", "none")
        return _r(f"{len(rems)} ਗਾਹਕਾਂ ਲਈ ਯਾਦ-ਸੁਨੇਹੇ ਤਿਆਰ ਹਨ।", f"Reminders ready for {len(rems)} customers.",
                  f"{len(rems)} ग्राहकों के लिए याद-संदेश तैयार हैं।", "reminder", reminders=rems)

    if cmd.get("cancelled"):
        return _r("ਠੀਕ ਹੈ, ਨਹੀਂ ਲਿਖਿਆ। ਦੁਬਾਰਾ ਬੋਲੋ ਜੀ।", "OK, nothing written. Please say it again.",
                  "ठीक है, नहीं लिखा। दोबारा बोलिए।", "cancelled")

    # OTHER: grounded free-form answer from Evon, or a friendly fallback
    if evon.enabled():
        try:
            ans = await evon.answer(cmd.get("transcript", ""), ledger_context(), db.get_settings()["shop_name"])
            if ans:
                return _r(ans, "(Evon answered in Punjabi)", ans, "answer")
        except Exception:
            pass
    t = cmd.get("transcript", "")
    if any(w in t.lower() for w in ("ਅਕਾਲ", "ਨਮਸਤੇ", "नमस्ते", "hello", "namaste", "good morning")):
        return _r("ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜੀ! ਦੱਸੋ ਅੱਜ ਕੀ ਲਿਖਣਾ ਹੈ?", "Hello! What should I write today?",
                  "नमस्ते जी! बताइए आज क्या लिखना है?", "greet")
    return _r("ਮੈਂ ਹਿਸਾਬ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ। ਜਿਵੇਂ ਕਹੋ: ਰਮੇਸ਼ ਨੂੰ ਪੰਜ ਸੌ ਉਧਾਰ ਦਿੱਤਾ, ਜਾਂ ਅੱਜ ਦੀ ਵਿਕਰੀ ਦੱਸੋ।",
              "I can help with the ledger. Try: 'Gave Ramesh 500 on credit' or 'Tell me today's sales'.",
              "मैं हिसाब में मदद कर सकता हूं। जैसे बोलिए: रमेश को पांच सौ उधार दिया, या आज की बिक्री बताओ।", "help")


def _ask_customer(cmd) -> dict:
    if cmd.get("cut_start"):
        return _r("ਸ਼ੁਰੂ ਦੀ ਗੱਲ ਪੂਰੀ ਨਹੀਂ ਸੁਣੀ। ਕਿਸ ਗਾਹਕ ਦੀ ਗੱਲ ਹੈ? ਨਾਮ ਦੱਸੋ।",
                  "I didn't catch the beginning. Which customer? Please say the name.",
                  "शुरू की बात पूरी नहीं सुनी। किस ग्राहक की बात है? नाम बताइए।", "ask_customer",
                  pending={**cmd, "cut_start": False, "heard_confirmed": True})
    bill = cmd.get("bill")
    if bill and bill.get("paid") and bill["due"] > 0:   # part paid, rest must go on someone's account
        return _r(f"{R(bill['total'])} ਦੇ ਬਿੱਲ ਵਿੱਚੋਂ {R(bill['paid'])} ਮਿਲੇ, {R(bill['due'])} ਬਾਕੀ। ਕਿਸ ਦੇ ਖਾਤੇ ਵਿੱਚ ਲਿਖਾਂ?",
                  f"{R(bill['paid'])} received on a {R(bill['total'])} bill, {R(bill['due'])} left. "
                  f"Whose account should I write it to?",
                  f"{R(bill['total'])} के बिल में से {R(bill['paid'])} मिले, {R(bill['due'])} बाकी। किसके खाते में लिखूं?",
                  "ask_customer", bill=bill_view(bill), pending=cmd)
    return _r("ਕਿਸ ਦੇ ਖਾਤੇ ਵਿੱਚ? ਗਾਹਕ ਦਾ ਨਾਮ ਦੱਸੋ।", "Which customer's account? Please say the name.",
              "किसके खाते में? ग्राहक का नाम बताइए।", "ask_customer", pending=cmd)


def _ask_change(cmd, bill) -> dict:
    """Paid more than the bill: give the extra back now, or keep it on the account as advance?
    The question repeats the name, bill and money given, so answering it also confirms what was heard."""
    n = cmd["customer"]["name"]
    paid, total = bill["paid"], bill["total"]
    extra = round(paid - total, 2)
    return _r(f"{n} ਨੇ {R(paid)} ਦਿੱਤੇ, ਬਿੱਲ {R(total)} ਦਾ ਹੈ। {R(extra)} ਵਾਪਸ ਦੇਣੇ ਹਨ ਜਾਂ ਐਡਵਾਂਸ ਰੱਖਣੇ ਹਨ?",
              f"{E(n)} gave {R(paid)} for a {R(total)} bill. Give {R(extra)} back as change, or keep it as advance?",
              f"{H(n)} ने {R(paid)} दिए, बिल {R(total)} का है। {R(extra)} वापस देने हैं या एडवांस रखने हैं?",
              "ask_change", extra=extra, bill=bill_view(bill), pending={**cmd, "awaiting": "change"})


def _confirm_heard(cmd, intent, amount, check) -> dict:
    """The repeat-detector thinks this may be misheard: read it back, write only on a yes."""
    n = (cmd["customer"] or {}).get("name") or ""
    wp = {"CREDIT": f"{n} ਨੂੰ {R(amount)} ਉਧਾਰ", "PAYMENT": f"{n} ਤੋਂ {R(amount)} ਜਮ੍ਹਾ",
          "SALE": f"{R(amount)} ਨਕਦ ਵਿਕਰੀ", "EXPENSE": f"{R(amount)} ਖਰਚਾ"}[intent]
    we = {"CREDIT": f"{R(amount)} credit to {E(n)}", "PAYMENT": f"{R(amount)} received from {E(n)}",
          "SALE": f"{R(amount)} cash sale", "EXPENSE": f"{R(amount)} expense"}[intent]
    wh = {"CREDIT": f"{H(n)} को {R(amount)} उधार", "PAYMENT": f"{H(n)} से {R(amount)} जमा",
          "SALE": f"{R(amount)} नकद बिक्री", "EXPENSE": f"{R(amount)} खर्चा"}[intent]
    bill = cmd.get("bill")
    if intent == "CREDIT" and bill and bill.get("paid"):
        p = R(bill["paid"])
        wp += f", {p} ਮਿਲੇ"
        we += f", {p} received now"
        wh += f", {p} मिले"
    pa, en, hi = f"ਮੈਂ ਸੁਣਿਆ: {wp}। ਠੀਕ ਹੈ?", f"I heard: {we}. Is that right?", f"मैंने सुना: {wh}। ठीक है?"
    if check.get("noisy"):
        pa += " ਰੌਲਾ ਬਹੁਤ ਹੈ, ਫ਼ੋਨ ਮੂੰਹ ਦੇ ਨੇੜੇ ਰੱਖੋ।"
        en += " It's very noisy, hold the phone closer."
        hi += " बहुत शोर है, फ़ोन मुंह के पास रखिए।"
    if check.get("reason") == "cut":
        pa = "ਸ਼ੁਰੂ ਦੀ ਗੱਲ ਪੂਰੀ ਨਹੀਂ ਸੁਣੀ। " + pa
        en = "I didn't catch the beginning. " + en
        hi = "शुरू की बात पूरी नहीं सुनी। " + hi
    if check.get("reason") == "new":
        pa += " ਇਹ ਨਵਾਂ ਖਾਤਾ ਖੁੱਲ੍ਹੇਗਾ।"
        en += " This opens a new account."
        hi += " यह नया खाता खुलेगा।"
    return _r(pa, en, hi, "confirm_heard", pending={**cmd, "amount": amount, "awaiting": "heard"}, audio_check=check)


async def _customer_txn(cmd, intent, amount, voice_id) -> dict:
    cust = cmd["customer"]
    cid, is_new = (cust["id"], False) if cust["id"] else db.get_or_create_customer(cust["name"])
    kind = KIND[intent]
    before = risk.score_customer(cid) if (intent == "CREDIT" and not is_new) else None
    if intent == "CREDIT" and cmd.get("bill"):
        return _bill_credit(cmd, cid, is_new, before, voice_id)
    tid = db.add_txn(kind, amount, customer_id=cid, item=cmd.get("item"), quantity=cmd.get("quantity"),
                     unit=cmd.get("unit"), day_offset=cmd.get("day_offset") or 0, voice_id=voice_id, ts=entry_ts(cmd))
    c = db.customer(cid)
    n, bal = c["name"], c["balance"]
    off = cmd.get("day_offset") or 0
    wp = {-1: "ਕੱਲ੍ਹ ਦੀ ਤਾਰੀਖ਼ ਵਿੱਚ ", -2: "ਪਰਸੋਂ ਦੀ ਤਾਰੀਖ਼ ਵਿੱਚ "}.get(off, "")
    wh = {-1: "कल की तारीख़ में ", -2: "परसों की तारीख़ में "}.get(off, "")
    if intent == "CREDIT":
        item = f" ({cmd['item']})" if cmd.get("item") else ""
        pa = f"{n} ਦੇ ਖਾਤੇ ਵਿੱਚ {wp}{R(amount)}{item} ਉਧਾਰ ਲਿਖ ਦਿੱਤਾ। ਕੁੱਲ ਬਕਾਇਆ {R(bal)}।"
        en = f"Added {R(amount)} credit to {E(n)}'s account. Total due {R(bal)}."
        hi = f"{H(n)} के खाते में {wh}{R(amount)}{item} उधार लिख दिया। कुल बकाया {R(bal)}।"
        if is_new:
            pa, en, hi = (f"{n} ਦਾ ਨਵਾਂ ਖਾਤਾ ਖੋਲ੍ਹਿਆ। " + pa, f"Opened a new account for {E(n)}. " + en,
                          f"{H(n)} का नया खाता खोला। " + hi)
        warning = None
        if before and before["trust"] is not None and before["band"]["key"] == "risky" and not before["low_data"]:
            pa += f" ਧਿਆਨ ਦਿਓ, {n} ਦਾ ਭਰੋਸਾ ਸਕੋਰ {before['trust']} ਹੈ।"
            en += f" Careful: {E(n)}'s trust score is {before['trust']}."
            hi += f" ध्यान दीजिए, {H(n)} का भरोसा स्कोर {before['trust']} है।"
            warning = before
        return _r(pa, en, hi, "txn", txn_id=tid, customer_id=cid, new_customer=is_new, risk_warning=warning)
    # PAYMENT
    if bal > 0:
        tp, te, th = f"ਹੁਣ {R(bal)} ਬਾਕੀ ਹਨ।", f"{R(bal)} still due.", f"अब {R(bal)} बाकी हैं।"
    elif bal == 0:
        tp, te, th = "ਖਾਤਾ ਪੂਰਾ ਸਾਫ਼ ਹੋ ਗਿਆ।", "Account fully settled.", "खाता पूरा साफ़ हो गया।"
    else:
        tp, te, th = f"{R(-bal)} ਐਡਵਾਂਸ ਜਮ੍ਹਾ ਹਨ।", f"{R(-bal)} held as advance.", f"{R(-bal)} एडवांस जमा हैं।"
    pa = f"{n} ਤੋਂ {wp}{R(amount)} ਜਮ੍ਹਾ ਹੋ ਗਏ। {tp}"
    en = f"Received {R(amount)} from {E(n)}. {te}"
    hi = f"{H(n)} से {wh}{R(amount)} जमा हो गए। {th}"
    if is_new:
        pa, en, hi = (f"{n} ਦਾ ਨਵਾਂ ਖਾਤਾ ਖੋਲ੍ਹਿਆ। " + pa, f"Opened a new account for {E(n)}. " + en,
                      f"{H(n)} का नया खाता खोला। " + hi)
    return _r(pa, en, hi, "txn", txn_id=tid, customer_id=cid, new_customer=is_new)


def _with_stock(reply: dict, kind: str, cmd: dict) -> dict:
    """Stock follows the ledger: restocking adds, sales and credit take away (tied to the entry, so undo
    reverses it). The reply mentions the new level after restocking, or a warning when an item runs low."""
    if not reply.get("txn_id") or kind == "payment":
        return reply
    changes = stock.record_entry(reply["txn_id"], kind, cmd)
    if not changes:
        return reply
    p, e, h = _stock_note(changes)
    return {**reply, "pa": reply["pa"] + p, "en": reply["en"] + e, "hi": reply["hi"] + h, "stock_changes": changes}


def _stock_note(changes: list[dict]) -> tuple[str, str, str]:
    """After an entry: restocked items say their new level; sold items say so only when running low."""
    pa = en = hi = ""
    for ch in changes:
        p, e, h = stock.names(ch["key"])
        qp, qe, qh = stock.qty_text(ch["qty_now"], ch["unit"])
        if ch["in"]:
            pa += f" ਸਟਾਕ: {p} ਹੁਣ {qp}।"
            en += f" Stock: {e} now {qe}."
            hi += f" स्टॉक: {h} अब {qh}।"
        elif ch["qty_now"] <= 0:
            pa += f" ਧਿਆਨ ਦਿਓ: {p} ਮੁੱਕ ਗਿਆ।"
            en += f" Note: out of {e}."
            hi += f" ध्यान दें: {h} ख़त्म हो गया।"
        elif ch["low"]:
            pa += f" ਧਿਆਨ ਦਿਓ: {p} ਸਿਰਫ਼ {qp} ਬਚਿਆ।"
            en += f" Note: only {qe} of {e} left."
            hi += f" ध्यान दें: {h} सिर्फ़ {qh} बचा।"
    return pa, en, hi


def _bill_note(bill: dict) -> str:
    return "; ".join(bill_lines(bill)[0])


def _bill_credit(cmd, cid, is_new, before, voice_id) -> dict:
    """A whole bill on a customer's account: the bill as credit, money given now as a payment.
    Both entries share one group id, so a single undo removes the whole bill."""
    import uuid
    bill = cmd["bill"]
    total, paid = bill["total"], bill.get("paid") or 0
    extra = round(paid - total, 2) if paid > total else 0
    keep_advance = extra > 0 and cmd.get("extra_choice") == "advance"
    paid_in = paid if (extra == 0 or keep_advance) else total
    group = uuid.uuid4().hex[:12]
    off = cmd.get("day_offset") or 0
    tid = db.add_txn("credit", total, customer_id=cid, item=cmd.get("item"), note=_bill_note(bill),
                     day_offset=off, voice_id=voice_id, group_id=group, ts=entry_ts(cmd))
    pay_id = None
    if paid_in > 0:
        pay_id = db.add_txn("payment", paid_in, customer_id=cid, note="ਬਿੱਲ ਵੇਲੇ ਮਿਲੇ", day_offset=off,
                            voice_id=voice_id, group_id=group, ts=entry_ts(cmd))
    c = db.customer(cid)
    n, bal = c["name"], c["balance"]
    sp, se, sh = _bill_summary(bill)
    pa = f"{sp}{n} ਦੇ ਖਾਤੇ ਵਿੱਚ {R(total)} ਦਾ ਬਿੱਲ ਲਿਖਿਆ"
    en = f"{se}Wrote a {R(total)} bill to {E(n)}'s account"
    hi = f"{sh}{H(n)} के खाते में {R(total)} का बिल लिखा"
    if paid_in > 0:
        pa += f", {R(paid_in)} ਮਿਲੇ"
        en += f", {R(paid_in)} received"
        hi += f", {R(paid_in)} मिले"
    pa, en, hi = pa + "।", en + ".", hi + "।"
    if extra > 0 and not keep_advance:
        pa += f" {R(extra)} ਵਾਪਸ ਦੇਣੇ ਹਨ।"
        en += f" Give {R(extra)} back as change."
        hi += f" {R(extra)} वापस देने हैं।"
    if bal > 0:
        pa += f" ਕੁੱਲ ਬਕਾਇਆ {R(bal)}।"
        en += f" Total due {R(bal)}."
        hi += f" कुल बकाया {R(bal)}।"
    elif bal == 0:
        pa += " ਖਾਤਾ ਸਾਫ਼ ਹੈ।"
        en += " Account is clear."
        hi += " खाता साफ़ है।"
    else:
        pa += f" {R(-bal)} ਐਡਵਾਂਸ ਜਮ੍ਹਾ ਹਨ।"
        en += f" {R(-bal)} held as advance."
        hi += f" {R(-bal)} एडवांस जमा हैं।"
    if is_new:
        pa, en, hi = (f"{n} ਦਾ ਨਵਾਂ ਖਾਤਾ ਖੋਲ੍ਹਿਆ। " + pa, f"Opened a new account for {E(n)}. " + en,
                      f"{H(n)} का नया खाता खोला। " + hi)
    warning = None
    on_credit = total - paid_in
    if (on_credit > 0 and before and before["trust"] is not None and before["band"]["key"] == "risky"
            and not before["low_data"]):
        pa += f" ਧਿਆਨ ਦਿਓ, {n} ਦਾ ਭਰੋਸਾ ਸਕੋਰ {before['trust']} ਹੈ।"
        en += f" Careful: {E(n)}'s trust score is {before['trust']}."
        hi += f" ध्यान दीजिए, {H(n)} का भरोसा स्कोर {before['trust']} है।"
        warning = before
    return _r(pa, en, hi, "txn", txn_id=tid, payment_id=pay_id, group_id=group, customer_id=cid,
              new_customer=is_new, risk_warning=warning,
              bill=bill_view(bill, paid_in=paid_in, change=extra if not keep_advance else 0, balance=bal))


def _shop_txn(cmd, intent, amount, voice_id) -> dict:
    kind = KIND[intent]
    bill = cmd.get("bill")
    tid = db.add_txn(kind, amount, item=cmd.get("item"), quantity=None if bill else cmd.get("quantity"),
                     unit=None if bill else cmd.get("unit"), note=_bill_note(bill) if bill else None,
                     day_offset=cmd.get("day_offset") or 0, voice_id=voice_id, ts=entry_ts(cmd))
    s, e = db.period_bounds("today")
    today = db.summary(s, e)
    sp, se, sh = _bill_summary(bill) if bill else ("", "", "")
    extra = round(bill["paid"] - bill["total"], 2) if bill and bill.get("paid") and bill["paid"] > bill["total"] else 0
    cp = f" {R(extra)} ਵਾਪਸ ਦੇਣੇ ਹਨ।" if extra else ""
    ce = f" Give {R(extra)} back as change." if extra else ""
    ch = f" {R(extra)} वापस देने हैं।" if extra else ""
    # a cash sale's bill shows the money received; a restocking bill is money paid out, so no "received" line
    data = ({"bill": bill_view(bill, paid_in=min(bill.get("paid") or amount, amount) if intent == "SALE" else 0,
                               change=extra if intent == "SALE" else 0, paid=None if intent != "SALE" else bill.get("paid"))}
            if bill else {})
    if intent == "SALE":
        return _r(f"{sp}{R(amount)} ਦੀ ਨਕਦ ਵਿਕਰੀ ਲਿਖ ਲਈ।{cp} ਅੱਜ ਦੀ ਕੁੱਲ ਵਿਕਰੀ {R(today['sale'])}।",
                  f"{se}Recorded a cash sale of {R(amount)}.{ce} Today's sales: {R(today['sale'])}.",
                  f"{sh}{R(amount)} की नकद बिक्री लिख ली।{ch} आज की कुल बिक्री {R(today['sale'])}।", "txn",
                  txn_id=tid, **data)
    item = cmd.get("item")
    return _r(f"{sp}{R(amount)} ਦਾ ਖਰਚਾ{f' ({item})' if item and not bill else ''} ਲਿਖ ਲਿਆ।",
              f"{se}Recorded an expense of {R(amount)}{f' ({E(item)})' if item and not bill else ''}.",
              f"{sh}{R(amount)} का खर्चा{f' ({H(item)})' if item and not bill else ''} लिख लिया।", "txn",
              txn_id=tid, **data)


def _risk_reply(cid: int) -> dict:
    c = db.customer(cid)
    s = risk.score_customer(cid)
    n = c["name"]
    if s["trust"] is None:
        return _r(f"{n} ਦਾ ਹਾਲੇ ਕੋਈ ਹਿਸਾਬ ਨਹੀਂ, ਸਕੋਰ ਨਹੀਂ ਬਣ ਸਕਦਾ।", f"No history for {E(n)} yet, so no score.",
                  f"{H(n)} का अभी कोई हिसाब नहीं, स्कोर नहीं बन सकता।", "show_customer", customer_id=cid)
    b = s["band"]
    pa = f"{n} ਦਾ ਭਰੋਸਾ ਸਕੋਰ {s['trust']} ਹੈ, {b['pa']}।"
    en = f"{E(n)}'s trust score is {s['trust']}/100 ({b['en']})."
    hi = f"{H(n)} का भरोसा स्कोर {s['trust']} है, {b['hi']}।"
    if s["reasons"] and b["key"] != "good":
        top = s["reasons"][:2]
        pa += " ਕਾਰਨ: " + ", ".join(r["pa"] for r in top) + "।"
        en += " Why: " + ", ".join(r["en"] for r in top) + "."
        hi += " कारण: " + ", ".join(r["hi"] for r in top) + "।"
    elif s["strengths"]:
        top = s["strengths"][:2]
        pa += " " + ", ".join(r["pa"] for r in top) + "।"
        en += " " + ", ".join(r["en"] for r in top).capitalize() + "."
        hi += " " + ", ".join(r["hi"] for r in top) + "।"
    if b["key"] != "good":
        if s["suggested_limit"]:
            lim = R(s["suggested_limit"])
            pa += f" ਸੁਝਾਅ: {lim} ਤੋਂ ਵੱਧ ਹੋਰ ਉਧਾਰ ਨਾ ਦਿਓ।"
            en += f" Suggestion: don't extend more than {lim} further credit."
            hi += f" सुझाव: {lim} से ज़्यादा और उधार मत दीजिए।"
        else:
            pa += " ਸੁਝਾਅ: ਪਹਿਲਾਂ ਪੁਰਾਣਾ ਹਿਸਾਬ ਲਓ, ਫਿਰ ਹੋਰ ਉਧਾਰ ਦਿਓ।"
            en += " Suggestion: collect the old dues before giving more credit."
            hi += " सुझाव: पहले पुराना हिसाब लीजिए, फिर और उधार दीजिए।"
    if s["low_data"]:
        pa += " ਹਾਲੇ ਡਾਟਾ ਥੋੜ੍ਹਾ ਹੈ।"
        en += " (Limited history so far.)"
        hi += " अभी डेटा कम है।"
    return _r(pa, en, hi, "show_customer", customer_id=cid, score=s)
