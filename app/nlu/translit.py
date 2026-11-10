"""Approximate Gurmukhi -> Roman transliteration for display ("ਗੁਰਪ੍ਰੀਤ" -> "Gurpreet").

Each consonant carries an inherent "a" unless it has a vowel sign or virama.
Schwa deletion (right to left): drop the word-final inherent "a", and drop a
medial one when it sits between a vowel and a consonant group that is followed
by a vowel ("ਹਰਪ੍ਰੀਤ" ha-ra-p-ree-ta -> Harpreet). Good enough for subtitles.
"""
import unicodedata

CONS = {
    "ਕ": "k", "ਖ": "kh", "ਗ": "g", "ਘ": "gh", "ਙ": "ng", "ਚ": "ch", "ਛ": "chh", "ਜ": "j", "ਝ": "jh",
    "ਞ": "ny", "ਟ": "t", "ਠ": "th", "ਡ": "d", "ਢ": "dh", "ਣ": "n", "ਤ": "t", "ਥ": "th", "ਦ": "d",
    "ਧ": "dh", "ਨ": "n", "ਪ": "p", "ਫ": "ph", "ਬ": "b", "ਭ": "bh", "ਮ": "m", "ਯ": "y", "ਰ": "r",
    "ਲ": "l", "ਵ": "v", "ੜ": "r", "ਸ": "s", "ਹ": "h", "ਸ਼": "sh", "ਖ਼": "kh", "ਗ਼": "gh", "ਜ਼": "z",
    "ਫ਼": "f", "ਲ਼": "l",
}
VOWELS = {"ਅ": "a", "ਆ": "aa", "ਇ": "i", "ਈ": "ee", "ਉ": "u", "ਊ": "oo", "ਏ": "e", "ਐ": "ai",
          "ਓ": "o", "ਔ": "au"}
SIGNS = {"ਾ": "aa", "ਿ": "i", "ੀ": "ee", "ੁ": "u", "ੂ": "oo", "ੇ": "e", "ੈ": "ai", "ੋ": "o", "ੌ": "au"}
NASAL = {"ਂ", "ੰ"}
VIRAMA, ADDAK, NUKTA = "੍", "ੱ", "਼"


def _units(word: str) -> list[dict]:
    """[{'c': consonant roman or '', 'v': vowel roman, 'inh': inherent?, 'nas': bool, 'gem': bool}]"""
    units, i, ch = [], 0, list(word)
    gem = False
    while i < len(ch):
        c = ch[i]
        if i + 1 < len(ch) and ch[i + 1] == NUKTA and c + NUKTA in CONS:
            c = c + NUKTA; i += 1
        if c in CONS:
            u = {"c": CONS[c], "v": "a", "inh": True, "nas": False, "gem": gem}
            gem = False
            nxt = ch[i + 1] if i + 1 < len(ch) else ""
            if nxt in SIGNS:
                u["v"], u["inh"] = SIGNS[nxt], False; i += 1
            elif nxt == VIRAMA:
                u["v"], u["inh"] = "", False; i += 1
            units.append(u)
        elif c in VOWELS:
            units.append({"c": "", "v": VOWELS[c], "inh": False, "nas": False, "gem": False})
        elif c in NASAL and units:
            units[-1]["nas"] = True
        elif c == ADDAK:
            gem = True
        elif c in (VIRAMA, NUKTA):
            pass
        else:
            units.append({"c": c, "v": "", "inh": False, "nas": False, "gem": False})
        i += 1
    return units


def _word(word: str) -> str:
    u = _units(word)
    if not u:
        return word
    if u[-1]["inh"] and len(u) > 1:
        u[-1]["v"] = ""
    for k in range(len(u) - 2, 0, -1):
        if not u[k]["inh"] or u[k]["nas"]:
            continue
        if not u[k - 1]["v"]:
            continue
        j = k + 1
        while j < len(u) and not u[j]["v"]:
            j += 1
        if j < len(u) and j - k <= 2:   # next consonant group is followed by a vowel
            u[k]["v"] = ""
    out = []
    for k, x in enumerate(u):
        if x["gem"] and x["c"]:
            out.append(x["c"][0])
        out.append(x["c"] + x["v"])
        if x["nas"] and not (k == len(u) - 1 and x["v"] in ("oo", "ee", "aa", "o", "e")):
            out.append("n")
    w = "".join(out)
    if w.endswith("aa") and len(w) > 3:
        w = w[:-1]
    return w[:1].upper() + w[1:]


# ---- Devanagari <-> Gurmukhi. Unicode lays both scripts out in parallel (offset 0x100), so most
# letters map directly; the exceptions are handled explicitly.
_D2G_SPECIAL = {"ष": "ਸ਼", "ऋ": "ਰਿ", "ृ": "੍ਰਿ", "ॉ": "ੋ", "ऑ": "ਓ", "ॅ": "ੇ", "ऍ": "ਏ", "ं": "ਂ",
                "ँ": "ਂ", "ऽ": "", "ॐ": "ਓਮ", "क़": "ਕ", "ड़": "ੜ", "ढ़": "ੜ", "फ़": "ਫ਼"}


def deva_to_guru(text: str) -> str:
    out = []
    for ch in text or "":
        if ch in _D2G_SPECIAL:
            out.append(_D2G_SPECIAL[ch])
        elif "\u0900" <= ch <= "\u097F":
            g = chr(ord(ch) + 0x100)
            out.append(g if g.isprintable() and unicodedata.name(g, "") else ch)
        else:
            out.append(ch)
    return unicodedata.normalize("NFD", "".join(out))   # e.g. ਸ਼ as ਸ + nukta, as the tables expect


def guru_to_deva(text: str) -> str:
    """For Hindi keyterms: ਬਿੱਟੂ -> बिट्टू (addak doubles the next consonant, tippi/bindi -> anusvara)."""
    out, chars = [], list(text or "")
    i = 0
    while i < len(chars):
        ch = chars[i]
        if ch == NUKTA and out and out[-1] == "स":   # ਸ਼ -> श (other nukta letters map 1:1)
            out[-1] = "श"
        elif ch == ADDAK and i + 1 < len(chars):
            nxt = chr(ord(chars[i + 1]) - 0x100)
            out.append(nxt + "्")
        elif ch in ("ੰ", "ਂ"):
            out.append("ं")
        elif "\u0A00" <= ch <= "\u0A7F":
            d = chr(ord(ch) - 0x100)
            out.append(d if unicodedata.name(d, "") else ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def is_devanagari(text: str) -> bool:
    return any("\u0900" <= c <= "\u097F" for c in text or "")


def to_roman(text: str) -> str:
    if is_devanagari(text):
        text = deva_to_guru(unicodedata.normalize("NFD", text))
    return " ".join(_word(w) for w in (text or "").split())
