"""Answers to smart ledger questions (the spec comes from app/nlu/query.py).

Every number is computed from the ledger with plain SQL sums, never by a language model, and every answer
comes in Punjabi, English and Hindi, plus a list of rows the screen shows (tap a row to open that account).
"""
import time

from . import db
from .actions import E, H, R, _r

SPOKEN_MAX = 5   # names read aloud; the screen lists all of them


def _wlabel(q: dict) -> tuple[str, str, str]:
    w, n = q.get("window"), q.get("n")
    return {
        "today": ("ਅੱਜ", "Today", "आज"),
        "yesterday": ("ਕੱਲ੍ਹ", "Yesterday", "कल"),
        "day_before": ("ਪਰਸੋਂ", "The day before yesterday", "परसों"),
        "this_week": ("ਇਸ ਹਫ਼ਤੇ", "This week", "इस हफ़्ते"),
        "last_week": ("ਪਿਛਲੇ ਹਫ਼ਤੇ", "Last week", "पिछले हफ़्ते"),
        "this_month": ("ਇਸ ਮਹੀਨੇ", "This month", "इस महीने"),
        "last_month": ("ਪਿਛਲੇ ਮਹੀਨੇ", "Last month", "पिछले महीने"),
        "days": (f"ਪਿਛਲੇ {n} ਦਿਨਾਂ ਵਿੱਚ", f"In the last {n} days", f"पिछले {n} दिनों में"),
    }.get(w, ("ਹੁਣ ਤੱਕ", "So far", "अब तक"))


def _days_ago(ts: float | None) -> int | None:
    return None if ts is None else max(0, int((time.time() - ts) // 86400))


def _date(ts: float) -> str:
    return time.strftime("%d %b", time.localtime(ts))


def _row(cid, name, amount, sub=("", "", "")) -> dict:
    return {"customer_id": cid, "name": {"pa": name, "en": E(name), "hi": H(name)}, "amount": amount,
            "sub": {"pa": sub[0], "en": sub[1], "hi": sub[2]}}


def _names(rows, lang) -> str:
    sep = {"pa": ", ", "en": ", ", "hi": ", "}[lang]
    parts = [f"{r['name'][lang]} {R(r['amount'])}" for r in rows[:SPOKEN_MAX]]
    more = len(rows) - SPOKEN_MAX
    if more > 0:
        parts.append({"pa": f"ਅਤੇ {more} ਹੋਰ", "en": f"and {more} more", "hi": f"और {more} और"}[lang])
    return sep.join(parts)


def answer(cmd: dict) -> dict:
    q = cmd["query"]
    t = q["type"]
    if t == "debtors_over":
        return _debtors_over(q)
    if t == "not_paid":
        return _not_paid(q)
    if q.get("customer_status") not in (None, "none"):   # about one customer: make sure we know which one
        cust = cmd["customer"]
        if cust["status"] == "ambiguous":
            cands = cust["candidates"]
            return _r(f"ਕਿਹੜੇ {cust['name']}? " + " ਜਾਂ ".join(c["name"] for c in cands) + "?",
                      f"Which {E(cust['name'])}? " + " or ".join(E(c['name']) for c in cands) + "?",
                      f"कौन से {H(cust['name'])}? " + " या ".join(H(c['name']) for c in cands) + "?",
                      "choose_customer", candidates=cands, pending=cmd)
        if not cust.get("id"):
            n = cust.get("name") or ""
            return _r(f"'{n}' ਨਾਮ ਦਾ ਕੋਈ ਖਾਤਾ ਨਹੀਂ ਮਿਲਿਆ।", f"No account found for '{E(n)}'.",
                      f"'{H(n)}' नाम का कोई खाता नहीं मिला।", "not_found")
        q = {**q, "customer_id": cust["id"], "customer": cust["name"]}
    if t == "items":
        return _items(q)
    return _total(q)


def _debtors_over(q) -> dict:
    v, gt = q["value"], q["op"] == ">"
    owed = [c for c in db.customers() if c["balance"] > 0 and (c["balance"] > v if gt else c["balance"] < v)]
    owed.sort(key=lambda c: -c["balance"])
    rows = [_row(c["id"], c["name"], c["balance"]) for c in owed]
    cp, ce, ch = ("ਤੋਂ ਵੱਧ", "more than", "से ज़्यादा") if gt else ("ਤੋਂ ਘੱਟ", "less than", "से कम")
    if not rows:
        return _r(f"{R(v)} {cp} ਕਿਸੇ ਵੱਲ ਬਾਕੀ ਨਹੀਂ।", f"Nobody owes {ce} {R(v)}.", f"{R(v)} {ch} किसी पर बाकी नहीं।",
                  "show_list", rows=[], query=q)
    tot, k = sum(r["amount"] for r in rows), len(rows)
    return _r(f"{R(v)} {cp} ਬਕਾਇਆ {k} {"ਗਾਹਕਾਂ" if k > 1 else "ਗਾਹਕ"} ਵੱਲ ਹੈ, ਕੁੱਲ {R(tot)}: {_names(rows, 'pa')}।",
              f"{k} customer{'s' if k > 1 else ''} owe{'' if k > 1 else 's'} {ce} {R(v)}, {R(tot)} in all: "
              f"{_names(rows, 'en')}.",
              f"{R(v)} {ch} बकाया {k} {"ग्राहकों" if k > 1 else "ग्राहक"} पर है, कुल {R(tot)}: {_names(rows, 'hi')}।",
              "show_list", rows=rows, total=tot, query=q)


def _not_paid(q) -> dict:
    days = q["days"]
    cutoff = time.time() - days * 86400
    act = db.customer_activity()
    late = []
    for c in db.customers():
        a = act.get(c["id"])
        if c["balance"] <= 0 or not a or a["first_ts"] > cutoff:
            continue   # nothing due, or the account is newer than the period asked about
        if a["last_payment_ts"] is None or a["last_payment_ts"] < cutoff:
            late.append((c, a["last_payment_ts"]))
    late.sort(key=lambda x: -x[0]["balance"])
    rows = []
    for c, lp in late:
        d = _days_ago(lp)
        sub = (("ਕਦੇ ਕੁਝ ਨਹੀਂ ਦਿੱਤਾ", "never paid", "कभी कुछ नहीं दिया") if d is None else
               (f"ਆਖਰੀ ਭੁਗਤਾਨ {d} ਦਿਨ ਪਹਿਲਾਂ", f"last paid {d} days ago", f"आख़िरी भुगतान {d} दिन पहले"))
        rows.append(_row(c["id"], c["name"], c["balance"], sub))
    if not rows:
        return _r(f"ਸਭ ਨੇ ਪਿਛਲੇ {days} ਦਿਨਾਂ ਵਿੱਚ ਕੁਝ ਨਾ ਕੁਝ ਦਿੱਤਾ ਹੈ।",
                  f"Everyone who owes has paid something in the last {days} days.",
                  f"सबने पिछले {days} दिनों में कुछ न कुछ दिया है।", "show_list", rows=[], query=q)
    tot, k = sum(r["amount"] for r in rows), len(rows)
    return _r(f"{days} ਦਿਨਾਂ ਤੋਂ {k} {"ਗਾਹਕਾਂ" if k > 1 else "ਗਾਹਕ"} ਨੇ ਕੁਝ ਨਹੀਂ ਦਿੱਤਾ, ਕੁੱਲ ਬਕਾਇਆ {R(tot)}: {_names(rows, 'pa')}।",
              f"{k} customer{'s' if k > 1 else ''} {'have' if k > 1 else 'has'} paid nothing in {days} days, "
              f"{R(tot)} due: {_names(rows, 'en')}.",
              f"{days} दिनों से {k} {"ग्राहकों" if k > 1 else "ग्राहक"} ने कुछ नहीं दिया, कुल बकाया {R(tot)}: {_names(rows, 'hi')}।",
              "show_list", rows=rows, total=tot, query=q)


def _total(q) -> dict:
    kind, cid = q["kind"], q.get("customer_id")
    s, e = db.window_bounds(q["window"], q.get("n"))
    tx = db.txns_between(s, e, kind, cid)
    tot, k = round(sum(x["amount"] for x in tx), 2), len(tx)
    wp, we, wh = _wlabel(q)
    if cid:
        n = q["customer"]
        rows = [{"customer_id": cid, "name": {"pa": x["item"] or ("ਉਧਾਰ" if kind == "credit" else "ਜਮ੍ਹਾ"),
                                             "en": E(x["item"]) if x["item"] else ("credit" if kind == "credit" else "payment"),
                                             "hi": H(x["item"]) if x["item"] else ("उधार" if kind == "credit" else "जमा")},
                 "amount": x["amount"], "sub": {"pa": _date(x["ts"]), "en": _date(x["ts"]), "hi": _date(x["ts"])}}
                for x in tx]
        bal = db.balance(cid)
        bp, be, bh = f" ਹੁਣ ਬਕਾਇਆ {R(bal)}।", f" Now due: {R(bal)}.", f" अब बकाया {R(bal)}।"
        if bal <= 0:
            bp, be, bh = " ਖਾਤਾ ਸਾਫ਼ ਹੈ।", " Account is clear.", " खाता साफ़ है।"
        if kind == "credit":
            if not tx:
                return _r(f"{wp} {n} ਨੇ ਕੋਈ ਉਧਾਰ ਨਹੀਂ ਲਿਆ।{bp}", f"{we}, {E(n)} took nothing on credit.{be}",
                          f"{wh} {H(n)} ने कोई उधार नहीं लिया।{bh}", "show_list", rows=[], customer_id=cid, query=q)
            return _r(f"{wp} {n} ਨੇ {R(tot)} ਦਾ ਸਮਾਨ ਉਧਾਰ ਲਿਆ, {k} ਵਾਰ।{bp}",
                      f"{we}, {E(n)} took {R(tot)} on credit ({k} entr{'ies' if k > 1 else 'y'}).{be}",
                      f"{wh} {H(n)} ने {R(tot)} का सामान उधार लिया, {k} बार।{bh}",
                      "show_list", rows=rows, total=tot, customer_id=cid, query=q)
        if not tx:
            return _r(f"{wp} {n} ਨੇ ਕੋਈ ਪੈਸੇ ਜਮ੍ਹਾ ਨਹੀਂ ਕਰਵਾਏ।{bp}", f"{we}, {E(n)} paid nothing.{be}",
                      f"{wh} {H(n)} ने कोई पैसे जमा नहीं किए।{bh}", "show_list", rows=[], customer_id=cid, query=q)
        return _r(f"{wp} {n} ਨੇ {R(tot)} ਜਮ੍ਹਾ ਕਰਵਾਏ, {k} ਵਾਰ।{bp}",
                  f"{we}, {E(n)} paid {R(tot)} ({k} payment{'s' if k > 1 else ''}).{be}",
                  f"{wh} {H(n)} ने {R(tot)} जमा किए, {k} बार।{bh}",
                  "show_list", rows=rows, total=tot, customer_id=cid, query=q)

    # whole shop
    if kind in ("credit", "payment"):
        per: dict[int, list] = {}
        for x in tx:
            if x["customer_id"]:
                per.setdefault(x["customer_id"], [x["customer"], 0.0])[1] += x["amount"]
        rows = sorted((_row(c, v[0], round(v[1], 2)) for c, v in per.items()), key=lambda r: -r["amount"])
    else:
        rows = [{"customer_id": None, "name": {"pa": x["item"] or ("ਵਿਕਰੀ" if kind == "sale" else "ਖਰਚਾ"),
                                               "en": E(x["item"]) if x["item"] else kind,
                                               "hi": H(x["item"]) if x["item"] else ("बिक्री" if kind == "sale" else "खर्चा")},
                 "amount": x["amount"], "sub": {"pa": _date(x["ts"]), "en": _date(x["ts"]), "hi": _date(x["ts"])}}
                for x in tx]
    what = {"credit": ("ਉਧਾਰ ਗਿਆ", "given on credit", "उधार गया"),
            "payment": ("ਉਧਾਰ ਵਾਪਸ ਆਇਆ", "collected from customers", "उधार वापस आया"),
            "sale": ("ਦੀ ਨਕਦ ਵਿਕਰੀ ਹੋਈ", "in cash sales", "की नकद बिक्री हुई"),
            "expense": ("ਦਾ ਖਰਚਾ ਹੋਇਆ", "spent", "का खर्चा हुआ")}[kind]
    if not tx:
        none = {"credit": ("ਕੋਈ ਉਧਾਰ ਨਹੀਂ ਗਿਆ", "nothing was given on credit", "कोई उधार नहीं गया"),
                "payment": ("ਕੋਈ ਪੈਸਾ ਵਾਪਸ ਨਹੀਂ ਆਇਆ", "nothing was collected", "कोई पैसा वापस नहीं आया"),
                "sale": ("ਕੋਈ ਨਕਦ ਵਿਕਰੀ ਨਹੀਂ ਲਿਖੀ", "no cash sales were written", "कोई नकद बिक्री नहीं लिखी"),
                "expense": ("ਕੋਈ ਖਰਚਾ ਨਹੀਂ ਲਿਖਿਆ", "no expenses were written", "कोई खर्चा नहीं लिखा")}[kind]
        return _r(f"{wp} {none[0]}।", f"{we}, {none[1]}.", f"{wh} {none[2]}।", "show_list", rows=[], query=q)
    pa = f"{wp} {R(tot)} {what[0]}, {k} {"ਐਂਟਰੀਆਂ" if k > 1 else "ਐਂਟਰੀ"}।"
    en = f"{we}: {R(tot)} {what[1]}, {k} entr{'ies' if k > 1 else 'y'}."
    hi = f"{wh} {R(tot)} {what[2]}, {k} एंट्री।"
    if kind in ("credit", "payment") and rows:
        pa += f" ਸਭ ਤੋਂ ਵੱਧ: {_names(rows[:3], 'pa')}।"
        en += f" Most: {_names(rows[:3], 'en')}."
        hi += f" सबसे ज़्यादा: {_names(rows[:3], 'hi')}।"
    return _r(pa, en, hi, "show_list", rows=rows, total=tot, query=q)


def _items(q) -> dict:
    cid, n = q["customer_id"], q["customer"]
    s, e = db.window_bounds(q["window"], q.get("n"))
    tx = db.txns_between(s, e, "credit", cid)
    wp, we, wh = _wlabel(q)
    if not tx:
        return _r(f"{wp} {n} ਨੇ ਖਾਤੇ ਵਿੱਚ ਕੁਝ ਨਹੀਂ ਲਿਆ।", f"{we}, {E(n)} took nothing on the account.",
                  f"{wh} {H(n)} ने खाते में कुछ नहीं लिया।", "show_list", rows=[], customer_id=cid, query=q)
    rows = []
    for x in tx:
        lines = (x["note"] or "").split("; ") if x["note"] and "₹" in (x["note"] or "") else []
        label = "; ".join(lines) if lines else (x["item"] or "ਸਮਾਨ")
        rows.append({"customer_id": cid, "amount": x["amount"],
                     "name": {"pa": label, "en": E(x["item"]) if x["item"] else "items",
                              "hi": H(x["item"]) if x["item"] else "सामान"},
                     "sub": {"pa": _date(x["ts"]), "en": _date(x["ts"]), "hi": _date(x["ts"])}})
    tot = round(sum(x["amount"] for x in tx), 2)

    def spoken(lang):
        return ", ".join(f"{r['name'][lang] if lang != 'pa' else (tx[i]['item'] or 'ਸਮਾਨ')} {R(r['amount'])}"
                         for i, r in enumerate(rows[:6]))
    return _r(f"{wp} {n} ਨੇ ਲਿਆ: {spoken('pa')}। ਕੁੱਲ {R(tot)}।",
              f"{we}, {E(n)} took: {spoken('en')}. Total {R(tot)}.",
              f"{wh} {H(n)} ने लिया: {spoken('hi')}। कुल {R(tot)}।",
              "show_list", rows=rows, total=tot, customer_id=cid, query=q)


# ------------------------------------------------------------------ stock
def _stock_row(lv) -> dict:
    from . import stock
    p, e, h = stock.names(lv["key"])
    qp, qe, qh = stock.qty_text(lv["qty"], lv["unit"])
    sub = ("ਘੱਟ ਹੈ", "running low", "कम है") if lv["low"] else ("", "", "")
    return {"customer_id": None, "name": {"pa": p, "en": e, "hi": h}, "qty": {"pa": qp, "en": qe, "hi": qh},
            "sub": {"pa": sub[0], "en": sub[1], "hi": sub[2]}, "low": lv["low"], "amount": lv["qty"]}


def _stock_list(rows, lang) -> str:
    return ", ".join(f"{r['name'][lang]} {r['qty'][lang]}" for r in rows[:6]) + (
        {"pa": f" ਅਤੇ {len(rows) - 6} ਹੋਰ", "en": f" and {len(rows) - 6} more", "hi": f" और {len(rows) - 6} और"}[lang]
        if len(rows) > 6 else "")


_NO_STOCK = ("ਹਾਲੇ ਕੋਈ ਸਟਾਕ ਨਹੀਂ ਲਿਖਿਆ। ਜਿਵੇਂ ਦੱਸੋ: ਆਟੇ ਦਾ ਸਟਾਕ 20 ਬੋਰੀਆਂ ਹੈ। ਥੋਕ ਤੋਂ ਆਇਆ ਮਾਲ ਵੀ ਆਪੇ ਜੁੜ ਜਾਂਦਾ ਹੈ।",
             "No stock written yet. Say for example: 'stock of flour is 20 sacks'. Goods bought from the "
             "wholesaler are added by themselves.",
             "अभी कोई स्टॉक नहीं लिखा। जैसे बोलिए: आटे का स्टॉक 20 बोरियां है। थोक से आया माल भी अपने आप जुड़ जाता है।")


def stock_answer(cmd: dict) -> dict:
    from . import stock
    sp = cmd["stock"]
    t = sp["type"]
    if t == "stock_set":
        ids, rows = [], []
        for key, q, u in sp["items"]:
            ids.append(stock.set_count(key, u, q))
            rows.append(_stock_row({"key": key, "unit": u, "qty": stock.level(key, u), "low": False}))
        return _r(f"ਸਟਾਕ ਲਿਖ ਲਿਆ: {_stock_list(rows, 'pa')}।", f"Stock written: {_stock_list(rows, 'en')}.",
                  f"स्टॉक लिख लिया: {_stock_list(rows, 'hi')}।", "stock_set", rows=rows, stock_move_ids=ids)
    levels = stock.levels()
    if not levels:
        return _r(*_NO_STOCK, "show_list", rows=[])
    if t == "stock_left":
        key = sp["item"]
        mine = [lv for lv in levels if lv["key"] == key]
        p, e, h = stock.names(key)
        if not mine:
            return _r(f"{p} ਦਾ ਸਟਾਕ ਹਾਲੇ ਨਹੀਂ ਲਿਖਿਆ। ਜਿਵੇਂ ਦੱਸੋ: {p} ਦਾ ਸਟਾਕ 20 ਕਿੱਲੋ ਹੈ।",
                      f"No stock written for {e} yet. Say for example: 'stock of {e} is 20 kg'.",
                      f"{h} का स्टॉक अभी नहीं लिखा। जैसे बोलिए: {h} का स्टॉक 20 किलो है।", "show_list", rows=[])
        rows = [_stock_row(lv) for lv in mine]
        qp = " ਅਤੇ ".join(r["qty"]["pa"] for r in rows)
        qe = " and ".join(r["qty"]["en"] for r in rows)
        qh = " और ".join(r["qty"]["hi"] for r in rows)
        pa, en, hi = f"{p}: {qp} ਬਾਕੀ।", f"{e}: {qe} left.", f"{h}: {qh} बाकी।"
        if all(lv["qty"] <= 0 for lv in mine):
            pa, en, hi = f"{p} ਮੁੱਕ ਗਿਆ ਹੈ।", f"Out of {e}.", f"{h} ख़त्म हो गया है।"
        elif any(lv["low"] for lv in mine):
            pa += " ਘੱਟ ਹੈ, ਮੰਗਵਾ ਲਓ।"
            en += " Running low, time to reorder."
            hi += " कम है, मंगवा लीजिए।"
        return _r(pa, en, hi, "show_list", rows=rows)
    if t == "stock_low":
        low = [_stock_row(lv) for lv in levels if lv["low"]]
        if not low:
            return _r("ਕੁਝ ਵੀ ਮੁੱਕਣ ਵਾਲਾ ਨਹੀਂ, ਸਾਰਾ ਮਾਲ ਠੀਕ ਹੈ।", "Nothing is running low.",
                      "कुछ भी ख़त्म होने वाला नहीं, सारा माल ठीक है।", "show_list", rows=[_stock_row(lv) for lv in levels])
        return _r(f"ਇਹ ਮੰਗਵਾ ਲਓ, ਘੱਟ ਹਨ: {_stock_list(low, 'pa')}।", f"Running low, reorder: {_stock_list(low, 'en')}.",
                  f"ये मंगवा लीजिए, कम हैं: {_stock_list(low, 'hi')}।", "show_list", rows=low)
    rows = [_stock_row(lv) for lv in levels]
    nlow = sum(r["low"] for r in rows)
    tail = (f" {nlow} ਚੀਜ਼ਾਂ ਘੱਟ ਹਨ।", f" {nlow} running low.", f" {nlow} चीज़ें कम हैं।") if nlow else ("", "", "")
    return _r(f"ਸਟਾਕ: {_stock_list(rows, 'pa')}।{tail[0]}", f"Stock: {_stock_list(rows, 'en')}.{tail[1]}",
              f"स्टॉक: {_stock_list(rows, 'hi')}।{tail[2]}", "show_list", rows=rows)
