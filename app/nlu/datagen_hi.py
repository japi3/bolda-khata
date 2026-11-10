"""Hindi (Devanagari) command templates, marked with a "HI:" prefix, for the trilingual NLU.

Prisma hi-IN returns Devanagari with digits (ITN). Names come from a Hindi name list plus
the Punjabi name generator converted to Devanagari, so the tagger learns context
("X को ... उधार दिया") rather than a fixed list.
"""
import random

from .punjabi import normalize
from .translit import guru_to_deva

T_HI = {
"CREDIT": [
    "{N} को {A} का {I} उधार दिया", "{N} के खाते में {A} लिख दो", "{N} {Q} {I} ले गया {A} का",
    "{N} ने {A} का सामान उधार लिया", "{D} {N} को {A} उधार", "{N} के नाम {A} चढ़ा दो",
    "{N} के खाते में {A} और जोड़ दो", "{N} को {A} का सामान दिया पैसे बाद में देगा", "{N} का {A} उधार लिखो",
    "उधार {N} {A}", "{N} के खाते में {A} की एंट्री करो", "{N} {I} ले गई {A} का बाद में देगी",
    "{N} के लिए {Q} {I} {A} उधार", "{N} आया था {Q} {I} ले गया {A} उधार", "{N} के नाम पर {A} लिखो",
],
"PAYMENT": [
    "{N} ने {A} दे दिए", "{N} ने {A} जमा करवाए", "{N} से {A} मिल गए", "{N} ने {A} वापस किए",
    "{N} ने {A} गूगल पे किए", "{N} का {A} का पेमेंट आ गया", "{N} ने पूरा हिसाब चुका दिया",
    "{D} {N} {A} दे गया", "{N} के खाते से {A} काट दो", "{N} ने सारे पैसे दे दिए", "{N} ने {A} फोन पे से भेजे",
    "{N} से {A} नकद लिए", "जमा {N} {A}", "{N} आया था {A} दे गया", "{N} की तरफ से {A} आए",
],
"SALE": [
    "{A} की नकद बिक्री", "{Q} {I} {A} का नकद बेचा", "कैश में {A} का {I} बिका", "{A} का सामान नकद बेचा",
    "नकद {A}", "एक ग्राहक {A} का {I} ले गया पैसे देकर", "{D} {A} की बिक्री हुई", "गल्ले में {A} आए बिक्री के",
    "{A} की सेल लिखो", "{I} बेचा {A} नकद",
],
"EXPENSE": [
    "{A} का खर्चा {E}", "{E} के {A} दिए", "{E} में {A} खर्च हुए", "खर्चा {A} {E}", "{E} के लिए {A} भरे",
    "{D} {E} का {A} खर्च हुआ", "{E} भरा {A}", "दुकान का खर्चा {A} {E}", "{E} पर {A} लगे",
],
"BALANCE": [
    "{N} के कितने पैसे बाकी हैं", "{N} का हिसाब बताओ", "{N} का खाता दिखाओ", "{N} पर कितना बकाया है",
    "{N} का बैलेंस कितना है", "{N} ने कितने देने हैं", "{N} का कितना उधार है", "{N} का खाता खोलो",
    "{N} से कितने लेने हैं",
],
"DEBTORS": [
    "किस किस के पैसे बाकी हैं", "कौन कौन उधार लेकर बैठा है", "सारे बकाया बताओ", "सबसे ज़्यादा उधार किसका है",
    "उधार वालों की लिस्ट दिखाओ", "बाज़ार में कितना पैसा फंसा है", "कुल कितना उधार बाकी है",
    "कितने लोगों का उधार बाकी है",
],
"SUMMARY": [
    "आज की बिक्री कितनी हुई", "आज का हिसाब बताओ", "आज कितने पैसे आए", "इस हफ्ते की कमाई कितनी है",
    "कल कितना खर्चा हुआ", "इस महीने कितनी बिक्री हुई", "आज का टोटल बताओ", "महीने का मुनाफा कितना है",
],
"REMIND": [
    "{N} को याद दिलाओ", "{N} को पैसों का रिमाइंडर भेजो", "{N} को मैसेज करो कि पैसे दे जाए", "सबको रिमाइंडर भेजो",
    "{N} को व्हाट्सएप पर याद दिलाओ", "{N} को बोलो हिसाब कर जाए", "{N} के लिए वॉइस मैसेज बनाओ",
],
"UNDO": [
    "पिछली एंट्री काट दो", "गलत हो गया वापस करो", "आखिरी एंट्री मिटा दो", "उसे रद्द कर दो", "पिछला डिलीट करो",
    "नहीं नहीं वो गलत था हटा दो", "अभी वाली एंट्री कैंसल करो",
],
"RISK": [
    "क्या {N} को उधार देना ठीक है", "{N} पर भरोसा कर सकते हैं", "{N} पैसे लौटाता है या नहीं", "{N} को और उधार दूं",
    "{N} का भरोसा स्कोर बताओ", "किसको उधार नहीं देना चाहिए", "कौन से ग्राहक खतरे वाले हैं", "{N} कितना भरोसेमंद है",
],
"OTHER": [
    "नमस्ते", "आप कौन हो", "मौसम कैसा है", "दुकान की बिक्री कैसे बढ़ाएं", "धन्यवाद", "क्या हाल है", "ठीक है",
    "जीएसटी के बारे में बताओ",
],
}
T_HI = {k: ["HI:" + t for t in v] for k, v in T_HI.items()}

HI_NAMES = """रमेश सुरेश राजू सोनू पिंकी बिट्टू राहुल अमित नेहा प्रिया गुरप्रीत हरप्रीत मनप्रीत कुलदीप सिमरन जसवीर
सुखविंदर बलजीत रमन अमन संदीप राजिंदर दीपक विक्की गोल्डी अनीता पूजा सुनीता मोहन इकबाल सलीम नवजोत गगन
लखवीर मनदीप सतनाम मुकेश दिनेश राकेश सीमा रेखा""".split()
HI_SURNAMES = "सिंह कौर शर्मा वर्मा गुप्ता अरोड़ा गिल संधू यादव".split()
HI_TITLES = ["मास्टर जी", "डॉक्टर साहब", "सरपंच जी", "पंडित जी", "शर्मा जी", "चाचा जी", "भाभी जी", "बाबा जी"]
ITEMS_HI = """आटा चावल दाल चीनी चायपत्ती तेल घी साबुन दूध नमक मिर्च हल्दी बिस्कुट मैदा बेसन पनीर दही अंडे
सब्ज़ी गुड़ मसाला नमकीन मैगी प्याज़ आलू टमाटर चने राजमा मूंगफली बादाम कॉपी पेन माचिस""".split()
MULTI_ITEMS_HI = ["सरसों का तेल", "चाय पत्ती", "गैस सिलेंडर", "कोल्ड ड्रिंक", "रिफाइंड तेल", "देसी घी", "ब्रेड का पैकेट"]
EXPENSES_HI = ["बिजली का बिल", "दुकान का किराया", "किराया", "चाय पानी", "माल की खरीद", "लड़के की तनख्वाह",
               "भाड़ा", "रिपेयर", "पेट्रोल", "सफाई", "पानी का बिल"]
DAYS_HI = ["आज", "कल", "परसों", "अभी", "सुबह", "शाम को"]
UNITS_HI = ["किलो", "लीटर", "पैकेट", "दर्जन", "बोरी", "डिब्बे", "बोतल"]
AMOUNT_WORDS_HI = ["पांच सौ", "डेढ़ सौ", "ढाई सौ", "दो हज़ार", "साढ़े तीन सौ", "एक हज़ार दो सौ", "सौ", "तीन सौ",
                   "पचास", "बीस", "सात सौ", "बारह सौ", "ढाई हज़ार", "चार सौ पचास"]
FILLERS_HI_PRE = ["हां जी", "अरे भाई", "सुनो", "अच्छा", "चलो", "ज़रा", "लिखो", "हां", "देखो जी"]
FILLERS_HI_POST = ["जी", "है जी", "ठीक है", "बस"]


def synth_name_hi(rng: random.Random) -> list[str]:
    from .datagen import synth_name
    r = rng.random()
    if r < 0.45:
        base = [rng.choice(HI_NAMES)]
    elif r < 0.8:
        base = guru_to_deva(" ".join(synth_name(rng))).split()
    else:
        return rng.choice(HI_TITLES).split()
    if rng.random() < 0.25:
        base.append(rng.choice(HI_SURNAMES))
    if rng.random() < 0.12:
        base.append("जी")
    return base


def synth_amount_hi(rng: random.Random) -> list[str]:
    if rng.random() < 0.75:
        n = rng.choice([rng.randint(1, 50) * 10, rng.randint(1, 40) * 50, rng.randint(1, 20) * 500,
                        rng.randint(10, 9999)])
        form = rng.random()
        if form < 0.45:
            return [str(n), "रुपये"]
        if form < 0.55:
            return ["₹", str(n)]
        return [str(n)]
    return rng.choice(AMOUNT_WORDS_HI).split() + (["रुपये"] if rng.random() < 0.5 else [])


def synth_qty_hi(rng: random.Random) -> list[str]:
    n = str(rng.randint(1, 10)) if rng.random() < 0.6 else rng.choice(["एक", "दो", "तीन", "चार", "पांच", "दस", "आधा", "डेढ़"])
    return [n, rng.choice(UNITS_HI)]


def synth_item_hi(rng: random.Random) -> list[str]:
    return (rng.choice(MULTI_ITEMS_HI) if rng.random() < 0.25 else rng.choice(ITEMS_HI)).split()


def expand_hi(template: str, rng: random.Random) -> tuple[list[str], list[str]]:
    toks, tags, name = [], [], None
    for part in template[3:].split():
        if part == "{N}":
            name = name or synth_name_hi(rng)
            seg, lab = name, "NAME"
        elif part == "{I}":
            seg, lab = synth_item_hi(rng), "ITEM"
        elif part == "{E}":
            seg, lab = rng.choice(EXPENSES_HI).split(), "ITEM"
        elif part == "{A}":
            seg, lab = synth_amount_hi(rng), None
        elif part == "{Q}":
            seg, lab = synth_qty_hi(rng), None
        elif part == "{D}":
            seg, lab = ([rng.choice(DAYS_HI)] if rng.random() < 0.7 else []), None
        else:
            seg, lab = [part], None
        k = 0
        for w in seg:
            for sub in normalize(w).split():
                toks.append(sub)
                tags.append("O" if lab is None else ("B-" if k == 0 else "I-") + lab)
                k += 1
    return toks, tags


def augment_hi(toks, tags, rng: random.Random):
    toks, tags = list(toks), list(tags)
    if rng.random() < 0.25:
        f = normalize(rng.choice(FILLERS_HI_PRE)).split()
        toks, tags = f + toks, ["O"] * len(f) + tags
    if rng.random() < 0.1:
        f = normalize(rng.choice(FILLERS_HI_POST)).split()
        toks, tags = toks + f, tags + ["O"] * len(f)
    return toks, tags
