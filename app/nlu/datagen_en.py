"""English + Hinglish command templates (marked with an "EN:" prefix) for the bilingual NLU.

Prisma's en-IN mode returns Latin script and accepts English-Hindi mixed speech, so
shopkeepers who prefer English (or Hinglish: "Bittu ko 500 udhaar diya") get the same
features. Names are drawn from the same Punjabi name generator, romanised, plus
common Latin spellings, so the tagger learns e.g. "gave X 500" / "X paid".
"""
import random

from .punjabi import normalize
from .translit import to_roman

T_EN = {
"CREDIT": [
    "gave {N} {A} on credit", "{N} took {Q} {I} on credit for {A}", "add {A} to {N}'s account",
    "write {A} in {N}'s khata", "{N} bought {I} worth {A} on udhaar", "put {A} on {N}'s tab",
    "{D} {N} took goods worth {A} will pay later", "credit {A} to {N}", "{N} owes {A} more for {I}",
    "give {N} {A} udhaar", "{N} took {I} for {A} not paid yet", "add {A} udhaar for {N}",
    "{N} ko {A} udhaar diya", "{N} ke khate mein {A} likh do", "{N} {Q} {I} le gaya {A} ka",
    "{N} took {A} of groceries on credit", "note {A} credit for {N}", "{N} ka {A} udhaar likho",
],
"PAYMENT": [
    "{N} paid {A}", "received {A} from {N}", "{N} gave back {A}", "{N} cleared {A}",
    "{N} paid {A} by google pay", "got {A} from {N} via upi", "{N} settled the full account",
    "{N} paid everything", "{D} {N} returned {A}", "deduct {A} from {N}'s account",
    "{N} sent {A} on phonepe", "payment of {A} from {N}", "{N} ne {A} de diye",
    "{N} se {A} mil gaye", "{N} ka payment aa gaya {A}", "{N} paid {A} cash",
    "{N} cleared all his dues", "{N} ne pura hisaab kar diya",
],
"SALE": [
    "cash sale of {A}", "sold {Q} {I} for {A} cash", "{A} cash sale", "sold {I} worth {A} in cash",
    "a customer bought {I} for {A} and paid cash", "{D} cash sales {A}", "counter sale {A}",
    "{A} naqad bikri", "{A} ka maal becha cash mein", "walk in customer paid {A}",
    "sold goods for {A} cash", "{Q} {I} sold for {A}",
],
"EXPENSE": [
    "paid {E} {A}", "{E} {A}", "spent {A} on {E}", "expense of {A} for {E}", "{A} went on {E}",
    "paid {A} for {E}", "{D} paid the {E} {A}", "{E} ka {A} kharcha", "kharcha {A} {E}",
    "{E} cost {A}", "bought {E} for the shop {A}",
],
"BALANCE": [
    "how much does {N} owe", "what is {N}'s balance", "show {N}'s account", "how much is pending from {N}",
    "{N}'s dues", "open {N}'s khata", "tell me {N}'s balance", "how much udhaar does {N} have",
    "{N} ka kitna baaki hai", "{N} ka hisaab batao", "what does {N} owe me", "check {N}'s account",
],
"DEBTORS": [
    "who owes me money", "show all dues", "total outstanding", "list of people with pending payments",
    "who has the biggest udhaar", "how much money is stuck in the market", "how many customers owe money",
    "kis kis ka paisa baaki hai", "show all pending accounts", "total udhaar kitna hai",
    "who all have to pay me",
],
"SUMMARY": [
    "today's sales", "how much did i sell today", "summary for today", "this week's earnings",
    "how much was spent this month", "yesterday's total", "monthly profit", "how much cash came in today",
    "aaj ki bikri kitni hui", "give me the weekly report", "how was business today",
],
"REMIND": [
    "remind {N} to pay", "send {N} a reminder", "send a payment reminder to {N}", "whatsapp {N} about the dues",
    "send reminders to everyone who owes", "ask {N} to clear the dues", "make a voice note for {N}",
    "{N} ko yaad dilao", "message {N} about the payment",
],
"UNDO": [
    "undo", "delete the last entry", "cancel that", "that was wrong remove it", "undo the last one",
    "remove what you just wrote", "no no delete it", "pichli entry cancel karo", "wrong entry delete it",
],
"RISK": [
    "can i trust {N}", "should i give {N} more credit", "is {N} risky", "{N}'s trust score",
    "does {N} pay on time", "who should i stop giving credit to", "which customers are risky",
    "is it safe to give {N} udhaar", "will {N} pay back", "{N} pe bharosa kar sakte hain",
    "is {N} a good customer",
],
"OTHER": [
    "hello", "good morning", "thank you", "what can you do", "how is the weather",
    "how do i grow my business", "ok", "who are you", "tell me about gst", "bye", "thanks a lot",
],
}
T_EN = {k: ["EN:" + t for t in v] for k, v in T_EN.items()}

LATIN_NAMES = """Ramesh Suresh Raju Sonu Pinky Bittu Rahul Amit Neha Priya Gurpreet Harpreet Manpreet
Kuldeep Simran Jasvir Sukhwinder Baljeet Raman Aman Sandeep Rajinder Deepak Vicky Goldy Happy Bobby
Anita Pooja Sunita Mohan Iqbal Salim Lovely Navjot Gagan Harman Pardeep Satnam Lakhvir Mandeep""".split()
LATIN_SURNAMES = "Singh Kaur Sharma Verma Gupta Arora Gill Sandhu Dhillon Brar Bajwa Mann Sidhu".split()
LATIN_TITLES = ["Master ji", "Doctor sahib", "Sarpanch ji", "Pandit ji", "Sharma ji", "Uncle ji", "Aunty ji",
                "Gupta ji", "Bhabhi ji", "Baba ji"]
ITEMS_EN = """flour atta rice dal lentils sugar tea oil ghee soap milk salt chilli turmeric biscuits
maida besan paneer curd eggs vegetables bread jaggery spices detergent namkeen maggi onions potatoes
tomatoes chickpeas rajma peanuts almonds notebook pen batteries matches candles shampoo toothpaste""".split()
MULTI_ITEMS_EN = ["mustard oil", "tea leaves", "gas cylinder", "cold drink", "refined oil", "basmati rice",
                  "desi ghee", "washing powder"]
EXPENSES_EN = ["electricity bill", "shop rent", "rent", "tea and snacks", "stock purchase", "helper's salary",
               "salary", "transport", "freight", "repair", "petrol", "cleaning", "water bill", "mobile recharge"]
DAYS_EN = ["today", "yesterday", "this morning", "in the evening", "just now", "day before yesterday"]
UNITS_EN = ["kg", "kilo", "kilos", "litre", "litres", "packet", "packets", "dozen", "bag", "bottles", "boxes"]
AMOUNT_WORDS_EN = ["five hundred", "one hundred fifty", "two hundred fifty", "two thousand", "three hundred fifty",
                   "one thousand two hundred", "hundred", "three hundred", "fifty", "twenty", "seven hundred",
                   "fifteen hundred", "two thousand five hundred", "four hundred fifty", "one lakh"]
FILLERS_EN_PRE = ["ok", "listen", "yes", "please", "ji", "acha", "haan", "so"]
FILLERS_EN_POST = ["please", "ji", "ok", "thanks"]


def synth_name_en(rng: random.Random) -> list[str]:
    from .datagen import synth_name
    r = rng.random()
    if r < 0.45:
        base = [rng.choice(LATIN_NAMES)]
    elif r < 0.8:
        base = to_roman(" ".join(synth_name(rng))).split()
        base = [w for w in base if w.lower() != "jee"] or base
    else:
        return rng.choice(LATIN_TITLES).split()
    if rng.random() < 0.25:
        base.append(rng.choice(LATIN_SURNAMES))
    if rng.random() < 0.1:
        base.append("ji")
    return base


def synth_amount_en(rng: random.Random) -> list[str]:
    if rng.random() < 0.8:
        n = rng.choice([rng.randint(1, 50) * 10, rng.randint(1, 40) * 50, rng.randint(1, 20) * 500,
                        rng.randint(10, 9999)])
        form = rng.random()
        if form < 0.35:
            return [str(n), "rupees"]
        if form < 0.5:
            return ["rs", str(n)]
        if form < 0.55:
            return ["₹", str(n)]
        return [str(n)]
    return rng.choice(AMOUNT_WORDS_EN).split() + (["rupees"] if rng.random() < 0.4 else [])


def synth_qty_en(rng: random.Random) -> list[str]:
    if rng.random() < 0.15:
        return ["a", "dozen"]
    n = str(rng.randint(1, 10)) if rng.random() < 0.7 else rng.choice(["one", "two", "three", "five", "ten"])
    return [n, rng.choice(UNITS_EN)]


def synth_item_en(rng: random.Random) -> list[str]:
    return (rng.choice(MULTI_ITEMS_EN) if rng.random() < 0.25 else rng.choice(ITEMS_EN)).split()


def expand_en(template: str, rng: random.Random) -> tuple[list[str], list[str]]:
    toks, tags, name = [], [], None
    for part in template[3:].split():
        suffix = ""
        if part.endswith("'s") and part.startswith("{"):
            part, suffix = part[:-2], "'s"
        if part == "{N}":
            name = name or synth_name_en(rng)
            seg, lab = list(name), "NAME"
            if suffix:   # "Ramesh's" -> name token "ramesh" + "'s"
                seg[-1] = seg[-1] + "'s"
        elif part == "{I}":
            seg, lab = synth_item_en(rng), "ITEM"
        elif part == "{E}":
            seg, lab = rng.choice(EXPENSES_EN).split(), "ITEM"
        elif part == "{A}":
            seg, lab = synth_amount_en(rng), None
        elif part == "{Q}":
            seg, lab = synth_qty_en(rng), None
        elif part == "{D}":
            seg, lab = (rng.choice(DAYS_EN).split() if rng.random() < 0.7 else []), None
        else:
            seg, lab = [part], None
        k = 0
        for w in seg:
            for sub in normalize(w).split():
                toks.append(sub)
                tags.append("O" if lab is None else ("B-" if k == 0 else "I-") + lab)
                k += 1
    return toks, tags


def augment_en(toks, tags, rng: random.Random):
    toks, tags = list(toks), list(tags)
    if rng.random() < 0.2:
        f = rng.choice(FILLERS_EN_PRE).split()
        toks, tags = f + toks, ["O"] * len(f) + tags
    if rng.random() < 0.1:
        f = rng.choice(FILLERS_EN_POST).split()
        toks, tags = toks + f, tags + ["O"] * len(f)
    return toks, tags
