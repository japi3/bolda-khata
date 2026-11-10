"""Stock commands and questions, decided by explicit word rules (like bills and smart questions).

    "ਆਟੇ ਦੀਆਂ ਕਿੰਨੀਆਂ ਬੋਰੀਆਂ ਬਚੀਆਂ?"   -> stock_left  atta
    "ਕਿਹੜਾ ਮਾਲ ਮੁੱਕਣ ਵਾਲਾ ਹੈ?"          -> stock_low
    "ਸਟਾਕ ਦੱਸੋ"                         -> stock_all
    "ਸਟਾਕ: ਤੇਲ 12 ਬੋਤਲਾਂ, ਘਿਓ 5 ਕਿੱਲੋ"   -> stock_set  oil = 12 bottles, ghee = 5 kg

Returns None for everything else, so entries, bills and the other questions are untouched.
"""
from .. import stock
from .punjabi import RUPEE_WORDS, find_numbers, normalize

_N = lambda words: {normalize(w) for w in words.split()}  # noqa: E731

STOCK = _N("ਸਟਾਕ ਸਟੌਕ स्टॉक स्टाक stock inventory")
LEFT = _N("ਬਚਿਆ ਬਚੀ ਬਚੀਆਂ ਬਚੇ ਪਿਆ ਪਈ ਪਏ ਪਈਆਂ बचा बची बचे पड़ा पड़ी पड़े left remaining bacha bachi bache "
          "pada padi pade have ਰਹਿ ਰਹਿੰਦਾ ਰਹਿੰਦੀ रह रहा रही remain remains")
HOW = _N("ਕਿੰਨਾ ਕਿੰਨੇ ਕਿੰਨੀ ਕਿੰਨੀਆਂ कितना कितने कितनी kitna kitne kitni kinna kinne kinni")
LOW = _N("ਮੁੱਕਣ ਮੁੱਕ ਮੁੱਕਿਆ ਮੁੱਕੀ ਮੁੱਕਣੀ ਖਤਮ ਖ਼ਤਮ खत्म ख़त्म low running finished finishing khatam")
ORDER = _N("ਮੰਗਵਾਉਣਾ ਮੰਗਵਾਉਣੀ ਮੰਗਵਾਉਣੇ ਮੰਗਾਉਣਾ मंगवाना मंगाना मँगवाना reorder restock order mangwana")
SHOW = _N("ਦੱਸੋ ਦਿਖਾਓ ਵਿਖਾਓ बताओ बताइए दिखाओ दिखाइए show tell list")
MONEY = _N("ਪੈਸੇ ਬਾਕੀ ਉਧਾਰ ਬਕਾਇਆ पैसे बाकी उधार बकाया paise owe owes due dues udhaar money")


def parse_stock(toks: list[str]) -> dict | None:
    s = set(toks)
    nums = [n for n in find_numbers(toks) if n["role"] != "amount_explicit"
            and not (n["end"] < len(toks) and toks[n["end"]] in RUPEE_WORDS)]
    items = stock.find_items(toks)
    question = bool(s & HOW) or toks[:2] in (["how", "much"], ["how", "many"])
    if s & MONEY:
        return None   # about customers' money, not goods

    # what is running low / what to order
    if (s & LOW or s & ORDER) and not nums:
        return {"type": "stock_low"}

    # how much of an item is left
    if items and question and (s & LEFT or s & STOCK) and not nums:
        return {"type": "stock_left", "item": items[0][1]}

    # counted stock: "ਸਟਾਕ ਵਿੱਚ 50 ਕਿੱਲੋ ਖੰਡ ਹੈ", "Stock: oil 12 bottles, ghee 5 kg"
    if s & STOCK and items and nums and not question:
        pairs, used = [], set()
        for n in nums:
            unit = toks[n["end"]] if n["role"] == "quantity" else None
            best = min(((abs(pos - n["start"]) if pos < n["start"] else pos - n["end"] + 1, pos, key)
                        for pos, key in items if pos not in used), default=None)
            if best is None or best[0] > 4:
                continue
            c = stock.canon(n["value"], unit)
            if not c:
                continue
            used.add(best[1])
            pairs.append((best[2], c[0], c[1]))
        if pairs:
            return {"type": "stock_set", "items": pairs}

    # the whole stock
    if s & STOCK and not items and not nums and (s & SHOW or question or len(toks) <= 3):
        return {"type": "stock_all"}
    return None
