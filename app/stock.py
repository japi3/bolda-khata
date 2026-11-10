"""Stock (ਸਟਾਕ / माल): how much of each item the shop has, kept up to date by the entries it already makes.

    restocking expense  "ਥੋਕ ਤੋਂ 10 ਬੋਰੀਆਂ ਆਟਾ ..."        -> atta  +10 sack
    sale / credit       "ਪਿੰਕੀ ਨੂੰ 3 ਕਿੱਲੋ ਖੰਡ ... ਉਧਾਰ"     -> sugar  -3 kg
    counted stock       "ਖੰਡ ਦਾ ਸਟਾਕ 50 ਕਿੱਲੋ ਹੈ"           -> sugar  = 50 kg

Every move is tied to the ledger entry that caused it, so undoing an entry undoes its stock change too.
Items are matched through a small catalogue across Punjabi, Hindi and English/Hinglish (ਖੰਡ = चीनी = sugar
= chini), so stock bought in one language and sold in another is the same item.

Honest limit: units only convert where the conversion is fixed (g -> kg, ml -> l, dozen -> pieces). A sack of
flour sold by the kilo is kept as two separate counts (sacks and kg), because a sack's weight varies.
"""
import time

from . import db
from .nlu.punjabi import normalize

# key: (Punjabi, English, Hindi, other spellings / inflections / Hinglish)
CATALOG = {
    "atta": ("ਆਟਾ", "flour (atta)", "आटा", "ਆਟਾ ਆਟੇ आटा आटे atta aata ata flour"),
    "rice": ("ਚੌਲ", "rice", "चावल", "ਚੌਲ ਚੌਲਾਂ ਚਾਵਲ चावल चावलों chawal chaawal chaval rice basmati ਬਾਸਮਤੀ बासमती"),
    "dal": ("ਦਾਲ", "dal", "दाल", "ਦਾਲ ਦਾਲਾਂ दाल दालें dal daal lentils"),
    "sugar": ("ਖੰਡ", "sugar", "चीनी", "ਖੰਡ ਚੀਨੀ चीनी शक्कर sugar chini cheeni khand shakkar"),
    "tea": ("ਚਾਹ ਪੱਤੀ", "tea leaves", "चाय पत्ती", "ਪੱਤੀ ਚਾਹਪੱਤੀ पत्ती चायपत्ती tea patti chaipatti"),
    "oil": ("ਤੇਲ", "oil", "तेल", "ਤੇਲ ਰਿਫਾਇੰਡ तेल रिफाइंड oil tel refined"),
    "ghee": ("ਘਿਓ", "ghee", "घी", "ਘਿਓ ਘਿਉ घी ghee ghi"),
    "soap": ("ਸਾਬਣ", "soap", "साबुन", "ਸਾਬਣ साबुन soap soaps sabun"),
    "milk": ("ਦੁੱਧ", "milk", "दूध", "ਦੁੱਧ दूध milk doodh dudh"),
    "salt": ("ਲੂਣ", "salt", "नमक", "ਲੂਣ ਨਮਕ नमक salt namak"),
    "biscuit": ("ਬਿਸਕੁਟ", "biscuits", "बिस्किट", "ਬਿਸਕੁਟ बिस्किट बिस्कुट biscuit biscuits biskut"),
    "maida": ("ਮੈਦਾ", "maida", "मैदा", "ਮੈਦਾ मैदा maida"),
    "besan": ("ਬੇਸਣ", "besan", "बेसन", "ਬੇਸਣ ਵੇਸਣ बेसन besan"),
    "paneer": ("ਪਨੀਰ", "paneer", "पनीर", "ਪਨੀਰ पनीर paneer"),
    "curd": ("ਦਹੀਂ", "curd", "दही", "ਦਹੀਂ दही curd dahi"),
    "eggs": ("ਅੰਡੇ", "eggs", "अंडे", "ਅੰਡੇ ਆਂਡੇ ਅੰਡਾ अंडे अंडा egg eggs ande anda"),
    "potato": ("ਆਲੂ", "potatoes", "आलू", "ਆਲੂ आलू potato potatoes aloo alu"),
    "onion": ("ਪਿਆਜ਼", "onions", "प्याज", "ਪਿਆਜ਼ ਗੰਢੇ प्याज onion onions pyaz pyaaz"),
    "tomato": ("ਟਮਾਟਰ", "tomatoes", "टमाटर", "ਟਮਾਟਰ टमाटर tomato tomatoes tamatar"),
    "maggi": ("ਮੈਗੀ", "Maggi", "मैगी", "ਮੈਗੀ मैगी maggi noodles"),
    "bread": ("ਡਬਲ ਰੋਟੀ", "bread", "ब्रेड", "ਬਰੈੱਡ ब्रेड bread"),
    "colddrink": ("ਕੋਲਡ ਡਰਿੰਕ", "cold drinks", "कोल्ड ड्रिंक", "ਡਰਿੰਕ ड्रिंक drink drinks coke pepsi"),
    "shampoo": ("ਸ਼ੈਂਪੂ", "shampoo", "शैम्पू", "ਸ਼ੈਂਪੂ शैम्पू शैंपू shampoo"),
    "surf": ("ਸਰਫ਼", "detergent", "सर्फ", "ਸਰਫ਼ ਸਰਫ सर्फ़ सर्फ surf detergent"),
    "cylinder": ("ਗੈਸ ਸਿਲੰਡਰ", "gas cylinders", "गैस सिलेंडर", "ਸਿਲੰਡਰ सिलेंडर cylinder cylinders"),
    "chilli": ("ਮਿਰਚ", "chilli", "मिर्च", "ਮਿਰਚ ਮਿਰਚਾਂ मिर्च mirch chilli chili"),
    "haldi": ("ਹਲਦੀ", "turmeric", "हल्दी", "ਹਲਦੀ हल्दी haldi turmeric"),
    "gur": ("ਗੁੜ", "jaggery", "गुड़", "ਗੁੜ गुड़ gur gud jaggery"),
    "namkeen": ("ਨਮਕੀਨ", "namkeen", "नमकीन", "ਨਮਕੀਨ नमकीन namkeen"),
    "banana": ("ਕੇਲੇ", "bananas", "केले", "ਕੇਲੇ ਕੇਲਾ केले केला banana bananas kele kela"),
    "matches": ("ਮਾਚਿਸ", "matchboxes", "माचिस", "ਮਾਚਿਸ माचिस matches matchbox"),
    "toothpaste": ("ਟੁੱਥਪੇਸਟ", "toothpaste", "टूथपेस्ट", "ਟੁੱਥਪੇਸਟ टूथपेस्ट toothpaste"),
}
_WORD2KEY = {}
for _k, (_pa, _en, _hi, _more) in CATALOG.items():
    for _w in (_pa + " " + _hi + " " + _more).split():
        _WORD2KEY.setdefault(normalize(_w), _k)
    _WORD2KEY.setdefault(normalize(_pa), _k)

# canonical unit, and the factor to convert a spoken unit into it
UNIT_CANON = {}
for _canon, _factor, _words in (
        ("kg", 1, "ਕਿੱਲੋ kg kgs kilo kilos kilogram kilograms किलो"),
        ("kg", 0.001, "ਗ੍ਰਾਮ gram grams g ग्राम"),
        ("l", 1, "ਲੀਟਰ litre litres liter liters l लीटर"),
        ("pkt", 1, "ਪੈਕਟ ਪੈਕਟਾਂ packet packets pack packs पैकेट पैकेटों"),
        ("pc", 12, "ਦਰਜਨ dozen दर्जन"),
        ("pc", 1, "ਪੀਸ piece pieces pcs पीस"),
        ("sack", 1, "ਬੋਰੀ ਬੋਰੀਆਂ ਗੱਟਾ ਗੱਟੇ sack sacks bag bags बोरी बोरियां बोरियाँ"),
        ("box", 1, "ਡੱਬਾ ਡੱਬੇ ਡੱਬਿਆਂ box boxes tin tins डिब्बा डिब्बे डिब्बों"),
        ("crate", 1, "ਪੇਟੀ ਪੇਟੀਆਂ crate crates पेटी पेटियां पेटियाँ"),
        ("btl", 1, "ਬੋਤਲ ਬੋਤਲਾਂ bottle bottles बोतल बोतलें"),
        ("cup", 1, "ਕੱਪ cup cups"),
        ("thaila", 1, "ਥੈਲਾ ਥੈਲੇ थैला थैले")):
    for _w in _words.split():
        UNIT_CANON[normalize(_w)] = (_canon, _factor)

UNIT_NAMES = {"kg": ("ਕਿੱਲੋ", "kg", "किलो"), "l": ("ਲੀਟਰ", "litres", "लीटर"), "pkt": ("ਪੈਕਟ", "packets", "पैकेट"),
              "pc": ("", "", ""), "sack": ("ਬੋਰੀਆਂ", "sacks", "बोरियां"), "box": ("ਡੱਬੇ", "boxes", "डिब्बे"),
              "crate": ("ਪੇਟੀਆਂ", "crates", "पेटियां"), "btl": ("ਬੋਤਲਾਂ", "bottles", "बोतलें"),
              "cup": ("ਕੱਪ", "cups", "कप"), "thaila": ("ਥੈਲੇ", "bags", "थैले")}
LOW_SHARE = 0.2   # running low = at or below 20% of the last restock / count of that item (or none left)


def item_key(text: str | None) -> str | None:
    """Catalogue key for an item name in any script ("ਖੰਡ", "चीनी", "chini" -> "sugar")."""
    if not text:
        return None
    for w in normalize(text).split():
        if w in _WORD2KEY:
            return _WORD2KEY[w]
    return None


def find_items(toks: list[str]) -> list[tuple[int, str]]:
    """[(token position, key)] for every catalogue item mentioned in a sentence."""
    return [(i, _WORD2KEY[t]) for i, t in enumerate(toks) if t in _WORD2KEY]


def canon(qty: float | None, unit: str | None) -> tuple[float, str] | None:
    if qty is None:
        return None
    if not unit:
        return float(qty), "pc"
    c = UNIT_CANON.get(normalize(unit))
    if not c:
        return None
    return round(qty * c[1], 4), c[0]


def names(key: str) -> tuple[str, str, str]:
    pa, en, hi, _ = CATALOG[key]
    return pa, en, hi


def qty_text(q: float, unit: str) -> tuple[str, str, str]:
    n = str(int(q)) if q == int(q) else f"{q:g}"
    up, ue, uh = UNIT_NAMES.get(unit, (unit, unit, unit))
    return (f"{n} {up}".strip(), f"{n} {ue}".strip(), f"{n} {uh}".strip())


# ------------------------------------------------------------------ database
_ACTIVE = ("FROM stock_moves m LEFT JOIN txns t ON t.id = m.txn_id "
           "WHERE m.deleted = 0 AND (m.txn_id IS NULL OR t.deleted = 0)")


def tracked(key: str, unit: str) -> bool:
    """An item counts once it has been restocked or counted in that unit (sales alone don't start tracking)."""
    return db.con().execute(f"SELECT 1 {_ACTIVE} AND m.item_key=? AND m.unit=? AND m.kind IN ('in','set') LIMIT 1",
                            (key, unit)).fetchone() is not None


def level(key: str, unit: str) -> float:
    r = db.con().execute(f"SELECT COALESCE(SUM(m.qty),0) s {_ACTIVE} AND m.item_key=? AND m.unit=?",
                         (key, unit)).fetchone()
    return round(r["s"], 4)


def add_move(key: str, unit: str, qty: float, kind: str, txn_id: int | None = None) -> int:
    with db.tx() as c:
        return c.execute("INSERT INTO stock_moves(item_key, unit, qty, kind, txn_id, created_at) VALUES(?,?,?,?,?,?)",
                         (key, unit, qty, kind, txn_id, time.time())).lastrowid


def set_count(key: str, unit: str, qty: float) -> int:
    """Counted stock: store the difference from what the ledger thought, so later moves keep adding up."""
    return add_move(key, unit, round(qty - level(key, unit), 4), "set")


def undo_set(move_id: int, deleted: bool = True):
    with db.tx() as c:
        c.execute("UPDATE stock_moves SET deleted=? WHERE id=? AND kind='set'", (1 if deleted else 0, move_id))


def last_set() -> dict | None:
    r = db.con().execute("SELECT * FROM stock_moves WHERE kind='set' AND deleted=0 ORDER BY id DESC LIMIT 1").fetchone()
    return dict(r) if r else None


def levels() -> list[dict]:
    """Every tracked (item, unit): quantity now, last restock/count size, and whether it is running low."""
    out = []
    rows = db.con().execute(f"SELECT m.item_key k, m.unit u, SUM(m.qty) q {_ACTIVE} GROUP BY m.item_key, m.unit").fetchall()
    for r in rows:
        if not tracked(r["k"], r["u"]):
            continue
        ref = db.con().execute(
            f"SELECT m.kind, m.qty, m.id {_ACTIVE} AND m.item_key=? AND m.unit=? AND m.kind IN ('in','set') "
            "ORDER BY m.id DESC LIMIT 1", (r["k"], r["u"])).fetchone()
        q = round(r["q"], 4)
        # size of the last restock, or for a count the level it set
        ref_size = ref["qty"] if ref["kind"] == "in" else _level_after(r["k"], r["u"], ref["id"])
        low = q <= 0 or (ref_size > 0 and q <= LOW_SHARE * ref_size)
        out.append({"key": r["k"], "unit": r["u"], "qty": q, "ref": ref_size, "low": low})
    out.sort(key=lambda x: (not x["low"], names(x["key"])[1] if x["key"] in CATALOG else x["key"]))
    return out


def _level_after(key, unit, move_id) -> float:
    r = db.con().execute(f"SELECT COALESCE(SUM(m.qty),0) s {_ACTIVE} AND m.item_key=? AND m.unit=? AND m.id<=?",
                         (key, unit, move_id)).fetchone()
    return round(r["s"], 4)


def record_entry(txn_id: int, kind: str, cmd: dict) -> list[dict]:
    """Stock moves for a ledger entry just written. Restocking (expense) adds; a sale or credit takes away,
    but only for items already tracked. Returns [{key, unit, qty_now, low}] for items that changed."""
    if kind not in ("expense", "sale", "credit"):
        return []
    lines = []
    bill = cmd.get("bill")
    if bill:
        for ln in bill["lines"]:
            if ln.get("qty") is not None and ln.get("item"):
                lines.append((ln["item"], ln["qty"], ln.get("unit")))
    elif cmd.get("item") and cmd.get("quantity"):
        lines.append((cmd["item"], cmd["quantity"], cmd.get("unit")))
    changed = []
    for item, qty, unit in lines:
        key, c = item_key(item), canon(qty, unit)
        if not key or not c or c[0] <= 0:
            continue
        q, u = c
        if kind == "expense":
            add_move(key, u, q, "in", txn_id)
        elif tracked(key, u):
            add_move(key, u, -q, "out", txn_id)
        else:
            continue
        now = level(key, u)
        lv = next((x for x in levels() if x["key"] == key and x["unit"] == u), None)
        changed.append({"key": key, "unit": u, "qty_now": now, "low": bool(lv and lv["low"]), "in": kind == "expense"})
    return changed
