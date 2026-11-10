"""Punjabi (Gurmukhi) text utilities: normalisation, tokenisation, numbers.

Prisma's ITN usually gives digits ("500"), but speakers also say things like
"ਡੇਢ ਸੌ" (150), "ਸਾਢੇ ਤਿੰਨ ਸੌ" (350) or "ਢਾਈ ਹਜ਼ਾਰ" (2500) and ITN does not always
catch them, so we parse Punjabi number words too.
"""
import re
import unicodedata

NUKTA = "਼"
DEVA_NUKTA = "\u093c"
GURMUKHI_DIGITS = str.maketrans("੦੧੨੩੪੫੬੭੮੯०१२३४५६७८९", "01234567890123456789")
POSSESSIVE = re.compile(r"(?<=[A-Za-z])['’]s\b")
PUNCT = re.compile(r"[।॥,.!?;:\"'“”‘’()\[\]{}…\-–—/]+")

# Common spelling variants seen in ASR output -> canonical form.
_VARIANTS = {
    "ਕਿਲੋ": "ਕਿੱਲੋ", "ਕਿੱਲੋਗ੍ਰਾਮ": "ਕਿੱਲੋ", "ਕੇਜੀ": "ਕਿੱਲੋ",
    "ਰੁਪਈਏ": "ਰੁਪਏ", "ਰੁਪਿਆ": "ਰੁਪਏ", "ਰੁਪਈਆ": "ਰੁਪਏ", "ਰੁਪਏਂ": "ਰੁਪਏ", "ਰੁਪਿਏ": "ਰੁਪਏ",
    "ਉਦਾਰ": "ਉਧਾਰ", "ਉਧਾਰੀ": "ਉਧਾਰ",
    "ਜਮਾ": "ਜਮ੍ਹਾ", "ਜਮਾਂ": "ਜਮ੍ਹਾ",
    "ਕੱਲ": "ਕੱਲ੍ਹ", "ਕਲ": "ਕੱਲ੍ਹ", "ਕਲ੍ਹ": "ਕੱਲ੍ਹ",
    "ਹਜਾਰ": "ਹਜ਼ਾਰ",
}


def normalize(text: str) -> str:
    """NFC, strip nukta (ASR is inconsistent with ਜ਼/ਜ), unify digits, drop punctuation."""
    t = unicodedata.normalize("NFC", text or "")
    t = t.translate(GURMUKHI_DIGITS)
    t = POSSESSIVE.sub("", t)                      # English "Ramesh's" -> "Ramesh"
    t = t.replace("₹", " ₹ ")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)          # 1,250 -> 1250
    t = PUNCT.sub(" ", t)
    t = t.replace(NUKTA, "").replace(DEVA_NUKTA, "")
    toks = [_VARIANTS.get(w, w) for w in t.lower().split()]
    toks = [w.replace(NUKTA, "").replace(DEVA_NUKTA, "") for w in toks]
    return " ".join(toks)


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def surface_tokens(text: str) -> list[str]:
    """Same token boundaries as normalize(), but keeps the original spelling
    (nukta, case) so names are saved exactly as spoken: "ਰਮੇਸ਼" not "ਰਮੇਸ"."""
    t = unicodedata.normalize("NFC", text or "")
    t = t.translate(GURMUKHI_DIGITS)
    t = POSSESSIVE.sub("", t)
    t = t.replace("₹", " ₹ ")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    t = PUNCT.sub(" ", t)
    return t.split()


# ---------------------------------------------------------------- numbers
_UNITS = (
    "ਸਿਫ਼ਰ ਇੱਕ ਦੋ ਤਿੰਨ ਚਾਰ ਪੰਜ ਛੇ ਸੱਤ ਅੱਠ ਨੌਂ ਦਸ ਗਿਆਰਾਂ ਬਾਰਾਂ ਤੇਰਾਂ ਚੌਦਾਂ ਪੰਦਰਾਂ ਸੋਲਾਂ "
    "ਸਤਾਰਾਂ ਅਠਾਰਾਂ ਉੱਨੀ ਵੀਹ ਇੱਕੀ ਬਾਈ ਤੇਈ ਚੌਵੀ ਪੱਚੀ ਛੱਬੀ ਸਤਾਈ ਅਠਾਈ ਉਣੱਤੀ ਤੀਹ ਇਕੱਤੀ "
    "ਬੱਤੀ ਤੇਤੀ ਚੌਂਤੀ ਪੈਂਤੀ ਛੱਤੀ ਸੈਂਤੀ ਅਠੱਤੀ ਉਣਤਾਲੀ ਚਾਲੀ ਇਕਤਾਲੀ ਬਤਾਲੀ ਤਰਤਾਲੀ ਚੁਤਾਲੀ "
    "ਪੰਤਾਲੀ ਛਿਆਲੀ ਸੰਤਾਲੀ ਅਠਤਾਲੀ ਉਣੰਜਾ ਪੰਜਾਹ ਇਕਵੰਜਾ ਬਵੰਜਾ ਤਰਵੰਜਾ ਚਰਵੰਜਾ ਪਚਵੰਜਾ ਛਪੰਜਾ "
    "ਸਤਵੰਜਾ ਅਠਵੰਜਾ ਉਣਾਹਠ ਸੱਠ ਇਕਾਹਠ ਬਾਹਠ ਤਰੇਹਠ ਚੌਂਹਠ ਪੈਂਹਠ ਛਿਆਹਠ ਸਤਾਹਠ ਅਠਾਹਠ ਉਣੱਤਰ "
    "ਸੱਤਰ ਇਕੱਤਰ ਬਹੱਤਰ ਤਿਹੱਤਰ ਚੌਹੱਤਰ ਪਚੱਤਰ ਛਿਹੱਤਰ ਸਤੱਤਰ ਅਠੱਤਰ ਉਣਾਸੀ ਅੱਸੀ ਇਕਾਸੀ ਬਿਆਸੀ "
    "ਤਿਰਾਸੀ ਚੁਰਾਸੀ ਪਚਾਸੀ ਛਿਆਸੀ ਸਤਾਸੀ ਅਠਾਸੀ ਉਣਾਨਵੇਂ ਨੱਬੇ ਇਕਾਨਵੇਂ ਬਾਨਵੇਂ ਤਿਰਾਨਵੇਂ "
    "ਚੁਰਾਨਵੇਂ ਪਚਾਨਵੇਂ ਛਿਆਨਵੇਂ ਸਤਾਨਵੇਂ ਅਠਾਨਵੇਂ ਨੜਿੱਨਵੇਂ"
).split()
NUM_WORDS: dict[str, float] = {normalize(w): i for i, w in enumerate(_UNITS)}
# Frequent spoken/ASR spellings
NUM_WORDS.update({normalize(k): v for k, v in {
    "ਇਕ": 1, "ਨੌ": 9, "ਗਿਆਰਾ": 11, "ਬਾਰਾ": 12, "ਪੰਦਰਾ": 15, "ਪੰਝੀ": 25,
    "ਪਚਾਸ": 50, "ਪੰਜਾਹਾਂ": 50,
}.items()})
FRACTIONS = {normalize("ਡੇਢ"): 1.5, normalize("ਢਾਈ"): 2.5, normalize("ਸਵਾ"): 1.25,
             normalize("ਅੱਧਾ"): 0.5, normalize("ਪੌਣੇ"): -0.25}
SADHE = normalize("ਸਾਢੇ")          # "+0.5": ਸਾਢੇ ਤਿੰਨ = 3.5
SADHE_SET = {SADHE, normalize("साढ़े"), normalize("साढे"), "sadhe", "saade"}
MULTIPLIERS = {normalize("ਸੌ"): 100, normalize("ਹਜ਼ਾਰ"): 1000, normalize("ਲੱਖ"): 100000,
               normalize("ਕਰੋੜ"): 10_000_000}

# ---- Hindi (Prisma hi-IN, Devanagari). ITN usually gives digits; these cover the rest.
_HI = ("शून्य एक दो तीन चार पांच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
       "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस "
       "छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस "
       "अड़तालीस उनचास पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ "
       "तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर "
       "छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी "
       "नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split()
NUM_WORDS.update({normalize(w): i for i, w in enumerate(_HI)})
NUM_WORDS.update({normalize(k): v for k, v in {"पाँच": 5, "छः": 6, "छे": 6, "इक": 1}.items()})
FRACTIONS.update({normalize("डेढ़"): 1.5, normalize("ढाई"): 2.5, normalize("सवा"): 1.25,
                  normalize("आधा"): 0.5, normalize("पौने"): -0.25})
MULTIPLIERS.update({normalize("सौ"): 100, normalize("हज़ार"): 1000, normalize("हजार"): 1000,
                    normalize("लाख"): 100000, normalize("करोड़"): 10_000_000})

# ---- English (Prisma en-IN mode, or loanwords). ITN usually gives digits; these cover the rest.
_EN = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
       "sixteen seventeen eighteen nineteen").split()
EN_WORDS = {w: i for i, w in enumerate(_EN)}
EN_WORDS.update({w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())})
NUM_WORDS.update(EN_WORDS)
FRACTIONS.update({"half": 0.5})
MULTIPLIERS.update({"hundred": 100, "hundreds": 100, "thousand": 1000, "thousands": 1000, "k": 1000,
                    "lakh": 100000, "lakhs": 100000, "lac": 100000, "crore": 10_000_000})


def _is_num_token(t: str) -> bool:
    return (t.replace(".", "", 1).isdigit() or t in NUM_WORDS or t in FRACTIONS
            or t in SADHE_SET or t in MULTIPLIERS)


def parse_number_span(toks: list[str]) -> float | None:
    """Parse a contiguous run of number tokens, e.g. ['ਸਾਢੇ','ਤਿੰਨ','ਸੌ'] -> 350,
    ['2','ਹਜ਼ਾਰ','500'] -> 2500, ['ਡੇਢ','ਸੌ'] -> 150, ['fifteen','hundred'] -> 1500,
    ['one','fifty'] -> 150 (Indian English shorthand)."""
    toks = [t for t in toks if t != "and"]
    if (len(toks) == 2 and toks[0] in EN_WORDS and toks[1] in EN_WORDS
            and 1 <= EN_WORDS[toks[0]] <= 9 and EN_WORDS[toks[1]] >= 10):
        return EN_WORDS[toks[0]] * 100 + EN_WORDS[toks[1]]
    total, current, pending_half, pending_quarter = 0.0, 0.0, False, False
    seen = False
    for t in toks:
        if t.replace(".", "", 1).isdigit():
            current += float(t); seen = True
        elif t in NUM_WORDS:
            current += NUM_WORDS[t]; seen = True
        elif t in SADHE_SET:
            pending_half = True
        elif t in FRACTIONS:
            f = FRACTIONS[t]
            if f < 0:
                pending_quarter = True
            else:
                current += f
            seen = True
        elif t in MULTIPLIERS:
            m = MULTIPLIERS[t]
            base = current or 1.0
            if pending_half:
                base += 0.5; pending_half = False
            if pending_quarter:
                base -= 0.25; pending_quarter = False
            if m >= 1000:
                total += base * m; current = 0.0
            else:  # ਸੌ binds to the current group: "2 ਹਜ਼ਾਰ 5 ਸੌ"
                current = base * m
            seen = True
        else:
            return None
    if not seen:
        return None
    if pending_half:
        current += 0.5
    return total + current


UNIT_WORDS = {normalize(w) for w in
              "ਕਿੱਲੋ ਗ੍ਰਾਮ ਲੀਟਰ ਪੈਕਟ ਦਰਜਨ ਬੋਰੀ ਪੀਸ ਡੱਬਾ ਡੱਬੇ ਬੋਤਲ ਬੋਤਲਾਂ ਕੱਪ ਗੱਟਾ ਥੈਲਾ ਪੇਟੀ".split()} | set(
    "kg kgs kilo kilos kilogram kilograms gram grams g litre litres liter liters l packet packets pack packs "
    "dozen bag bags bottle bottles box boxes piece pieces pcs tin tins sack sacks cup cups".split()) | {
    normalize(w) for w in "किलो ग्राम लीटर पैकेट दर्जन बोरी पीस डिब्बा डिब्बे बोतल बोतलें थैला पेटी".split()}
ARTICLE_ONE = {normalize("ਇੱਕ"), normalize("ਇਕ"), "one", normalize("एक")}
# Hindi "दो" is both "two" and "give" ("चढ़ा दो", "जोड़ दो"): a lone दो is a verb unless a unit/rupee follows
AMBIGUOUS_TWO = {normalize("दो")}
RUPEE_WORDS = {normalize(w) for w in "ਰੁਪਏ ₹ ਰੁਪਈਆਂ ਰੁਪਈਏ ਰੁਪਿਆਂ ਰੁਪਈਆ".split()} | {
    "₹", "rs", "rupees", "rupee", "inr", "rupaye", "rupay"} | {
    normalize(w) for w in "रुपये रुपए रुपया रुपयों रूपये".split()}


def _joining_and(toks: list[str], j: int, start: int) -> bool:
    """'and' inside one number ("one hundred AND fifty"), not between two ("500 and 300")."""
    if toks[j] != "and" or j == start or j + 1 >= len(toks):
        return False
    after = toks[j + 2] if j + 2 < len(toks) else ""
    return (toks[j - 1] in MULTIPLIERS and toks[j + 1] in EN_WORDS and EN_WORDS[toks[j + 1]] < 100
            and after not in MULTIPLIERS)


def find_numbers(toks: list[str]) -> list[dict]:
    """Return every numeric span with a role guess: 'amount' or 'quantity'."""
    out, i = [], 0
    while i < len(toks):
        if _is_num_token(toks[i]):
            j = i
            while j < len(toks) and (_is_num_token(toks[j]) or _joining_and(toks, j, i)):
                # two written-out numbers in a row ("500, 300") are separate amounts,
                # unlike spoken compounds ("2 ਹਜ਼ਾਰ 500", "ਸਾਢੇ ਤਿੰਨ ਸੌ")
                if j > i and toks[j].replace(".", "", 1).isdigit() and toks[j - 1].replace(".", "", 1).isdigit():
                    break
                j += 1
            val = parse_number_span(toks[i:j])
            if val is not None:
                nxt = toks[j] if j < len(toks) else ""
                prev = toks[i - 1] if i > 0 else ""
                if nxt in UNIT_WORDS:
                    role = "quantity"
                elif nxt in RUPEE_WORDS or prev in ("₹", "rs"):   # "500 ਰੁਪਏ", "₹ 500"; not "ਰੁਪਏ 50"
                    role = "amount_explicit"
                else:
                    role = "amount"
                if role == "amount" and j - i == 1 and toks[i] in ARTICLE_ONE:
                    i = j   # "ਇੱਕ ਗਾਹਕ" = "a customer", not ₹1
                    continue
                if role == "amount" and j - i == 1 and toks[i] in AMBIGUOUS_TWO:
                    i = j   # "चढ़ा दो" = "add it", not ₹2
                    continue
                out.append({"value": val, "start": i, "end": j, "role": role,
                            "unit": nxt if role == "quantity" else None})
            i = j
        else:
            i += 1
    return out


def amount_conflict(nums: list[dict]) -> list[float]:
    """Several different plain amounts and nothing marking which one is the price -> ask."""
    if any(n["role"] == "amount_explicit" for n in nums):
        return []
    vals = sorted({n["value"] for n in nums if n["role"] == "amount"})
    return vals if len(vals) > 1 else []


def pick_amount(nums: list[dict]) -> float | None:
    explicit = [n for n in nums if n["role"] == "amount_explicit"]
    if explicit:
        return explicit[-1]["value"]
    plain = [n for n in nums if n["role"] == "amount"]
    if plain:
        return max(n["value"] for n in plain)
    return None


def pick_quantity(nums: list[dict]) -> tuple[float | None, str | None]:
    q = [n for n in nums if n["role"] == "quantity"]
    return (q[0]["value"], q[0]["unit"]) if q else (None, None)


# ------------------------------------------------------------ dates
DATE_OFFSETS = {normalize("ਅੱਜ"): 0, normalize("ਕੱਲ੍ਹ"): -1, normalize("ਪਰਸੋਂ"): -2,
                "today": 0, "yesterday": -1, "kal": -1, "parson": -2,
                normalize("आज"): 0, normalize("कल"): -1, normalize("परसों"): -2}


def date_offset(toks: list[str]) -> int:
    joined = " ".join(toks)
    if "day before yesterday" in joined:
        return -2
    for t in toks:
        if t in DATE_OFFSETS and DATE_OFFSETS[t] is not None:
            return DATE_OFFSETS[t]
    return 0


# ------------------------------------------------------------ number -> words (for UI/TTS fallbacks)
def rupees_text(amount: float) -> str:
    a = round(amount, 2)
    sign = "-" if a < 0 else ""
    a = abs(a)
    if a == int(a):
        return f"{sign}₹{int(a):,}"
    return f"{sign}₹{a:,.2f}"
