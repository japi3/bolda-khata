"""On-device Punjabi NLU: a MEMM-style slot tagger + a masked-text intent classifier.

1. Slot tagger (NAME / ITEM, BIO scheme): per-token multinomial logistic
   regression over lexical + context features and the previous tag
   (a Maximum-Entropy Markov Model), decoded with Viterbi beam search.
2. Intent classifier: names, items and numbers are masked first
   ("ਰਮੇਸ਼ ਨੂੰ 500 ਉਧਾਰ" -> "xname ਨੂੰ xnum ਉਧਾਰ"), then TF-IDF over char
   n-grams + word n-grams -> logistic regression. Masking makes the classifier
   learn the *structure* of the sentence, so unseen names don't confuse it.

Runs in ~2 ms on a laptop CPU; Evon (30B) is used on top when available.
"""
import math
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .punjabi import NUM_WORDS, FRACTIONS, MULTIPLIERS, SADHE_SET, normalize, surface_tokens

POSTPOS = {normalize(w) for w in "ਨੂੰ ਨੇ ਦੇ ਦਾ ਦੀ ਤੋਂ ਵੱਲ ਲਈ ਵਾਸਤੇ ਤੇ ਵੱਲੋਂ ਦਿਆਂ".split()}
TAGS = ["O", "B-NAME", "I-NAME", "B-ITEM", "I-ITEM"]


def _is_num(w: str) -> bool:
    return (w.replace(".", "", 1).isdigit() or w in NUM_WORDS or w in FRACTIONS
            or w in MULTIPLIERS or w in SADHE_SET or w == "₹")


def token_features(toks: list[str], i: int, prev_tag: str) -> dict:
    w = toks[i]
    get = lambda k: toks[k] if 0 <= k < len(toks) else ("<s>" if k < 0 else "</s>")
    f = {
        "b": 1, "w=" + w: 1, "suf2=" + w[-2:]: 1, "suf3=" + w[-3:]: 1, "pre2=" + w[:2]: 1,
        "pre3=" + w[:3]: 1, "len=" + str(min(len(w), 8)): 1,
        "w-1=" + get(i - 1): 1, "w+1=" + get(i + 1): 1, "w-2=" + get(i - 2): 1, "w+2=" + get(i + 2): 1,
        "w-1|w=" + get(i - 1) + "|" + w: 1, "w|w+1=" + w + "|" + get(i + 1): 1,
        "pt=" + prev_tag: 1, "pt|w+1=" + prev_tag + "|" + get(i + 1): 1,
    }
    if _is_num(w):
        f["isnum"] = 1
    if w in POSTPOS:
        f["ispostpos"] = 1
    if get(i + 1) in POSTPOS:
        f["next_postpos"] = 1
    if get(i + 2) in POSTPOS:
        f["next2_postpos"] = 1
    if _is_num(get(i - 1)):
        f["prev_num"] = 1
    if i == 0:
        f["first"] = 1
    return f


class SlotTagger:
    def __init__(self):
        self.vec = DictVectorizer()
        self.clf = LogisticRegression(max_iter=300, C=3.0)

    def fit(self, samples):
        X, y = [], []
        for s in samples:
            prev = "O"
            for i, tag in enumerate(s["tags"]):
                X.append(token_features(s["tokens"], i, prev))
                y.append(tag)
                prev = tag
        self.clf.fit(self.vec.fit_transform(X), y)
        self.classes_ = list(self.clf.classes_)
        return self

    def predict(self, toks: list[str], beam: int = 4) -> tuple[list[str], float]:
        """Beam-search Viterbi decoding; returns tags and mean token confidence."""
        if not toks:
            return [], 1.0
        beams = [(0.0, ["O"], [])]  # (logprob, history incl. start, confidences)
        for i in range(len(toks)):
            cand = []
            feats = [token_features(toks, i, b[1][-1]) for b in beams]
            probs = self.clf.predict_proba(self.vec.transform(feats))
            for (lp, hist, confs), p in zip(beams, probs):
                for k in np.argsort(p)[::-1][:3]:
                    tag = self.classes_[k]
                    if tag.startswith("I-") and hist[-1][2:] != tag[2:]:
                        continue  # invalid BIO transition
                    cand.append((lp + math.log(p[k] + 1e-12), hist + [tag], confs + [p[k]]))
            beams = sorted(cand, key=lambda c: c[0], reverse=True)[:beam]
        best = beams[0]
        return best[1][1:], float(np.mean(best[2]))


# Semantic cue lexicon: groups of words that signal the same meaning. Each match
# adds a shared cue token, so a synonym the classifier has never seen (e.g.
# "ਭਰੋਸੇਮੰਦ") still activates the right evidence ("cue_trust").
_CUES = {
    "trust": "ਭਰੋਸਾ ਭਰੋਸੇ ਭਰੋਸੇਮੰਦ ਯਕੀਨ ਖਤਰਾ ਖਤਰੇ ਖ਼ਤਰਾ ਰਿਸਕ ਡੁੱਬ ਡੁੱਬਣ ਸਕੋਰ ਇਤਬਾਰ ਪੱਕਾ ਕੱਚਾ ਮਾੜਾ ਚੰਗਾ trust trustworthy risky risk safe reliable score bharosa good customer भरोसा भरोसेमंद यकीन खतरा खतरे रिस्क डूब स्कोर अच्छा बुरा",
    "modal": "ਦੇਵਾਂ ਦੇਈਏ ਦੇਣਾ ਦੇਣ ਚਾਹੀਦਾ ਸਕਦੇ ਸਕਦਾ ਠੀਕ should can could will shall dena दूं दें देना चाहिए सकते सकता ठीक",
    "who": "ਕੌਣ ਕਿਸ ਕਿਹੜੇ ਕਿਹਦੇ ਕਿਨ੍ਹਾਂ ਕਿਹੜਾ ਕਿੰਨੇ who whom whose which kis kaun कौन किस किसका किसको कौनसे किन",
    "all": "ਸਾਰੇ ਸਭ ਕੁੱਲ ਸਾਰਿਆਂ ਲਿਸਟ ਸੂਚੀ ਲੋਕਾਂ ਗਾਹਕ ਗਾਹਕਾਂ all everyone everybody total list customers people sabhi sab सारे सब कुल सबको लिस्ट लोगों ग्राहक ग्राहकों",
    "due": "ਬਾਕੀ ਬਕਾਇਆ ਬਕਾਏ ਉਧਾਰ ਉਧਾਰੀ ਖੜ੍ਹੀ ਖੜ੍ਹਾ ਖੜ੍ਹੇ ਰਹਿੰਦੇ ਰਹਿੰਦਾ ਦੇਣੇ ਫਸਿਆ ਫਸੇ ਬੈਲੇਂਸ ਲੈਣੇ owe owes owed due dues pending outstanding balance baaki udhaar stuck बाकी बकाया उधार फंसा देने लेने बैलेंस",
    "ask": "ਕਿੰਨਾ ਕਿੰਨੇ ਕਿੰਨੀ ਦੱਸੋ ਦਿਖਾਓ ਖੋਲ੍ਹੋ ਕੀ ਕਿਵੇਂ ਬਾਰੇ how much what show tell open check kitna kitni batao कितना कितने कितनी बताओ दिखाओ खोलो क्या कैसे",
    "cash": "ਨਕਦ ਕੈਸ਼ ਗੱਲੇ ਗੱਲਾ ਵਿਕਰੀ ਵੇਚਿਆ ਵਿਕਿਆ ਸੇਲ ਵਿਕੇ ਵੇਚੇ cash sale sales sold sell bikri naqad counter walk नकद कैश गल्ले बिक्री बेचा बिका सेल",
    "period": "ਅੱਜ ਹਫ਼ਤੇ ਹਫਤੇ ਮਹੀਨੇ ਮਹੀਨਾ ਕੱਲ੍ਹ ਟੋਟਲ ਕਮਾਈ ਮੁਨਾਫ਼ਾ ਮੁਨਾਫਾ ਲੇਖਾ today week weekly month monthly yesterday profit earnings report business aaj आज हफ्ते महीने कल टोटल कमाई मुनाफा",
    "paid": "ਜਮ੍ਹਾ ਮੋੜ ਮੋੜਿਆ ਵਾਪਸ ਪੇਮੈਂਟ ਚੁਕਤਾ ਸਾਫ਼ ਸਾਫ ਲਾਹ ਵਸੂਲ ਗੂਗਲ ਫੋਨ ਯੂਪੀਆਈ ਭੇਜੇ ਮਿਲ ਮਿਲੇ ਆਏ ਆਇਆ paid received returned cleared settled deduct sent got mil gaye upi pay phonepe payment de diye जमा लौटाता वापस पेमेंट चुका मिल मिले आए आया भेजे गूगल फोन",
    "gave": "ਦਿੱਤਾ ਦਿੱਤੇ ਦੇ ਗਿਆ ਗਈ gave given diya दिया दिए दे गया गई",
    "credit": "ਲਿਖ ਲਿਖੋ ਲਿਖ ਲਓ ਚੜ੍ਹਾ ਚੜ੍ਹ ਪਾ ਪਾਓ ਜੋੜ ਜੋੜੋ ਐਂਟਰੀ ਲੈ ਲੈ ਗਿਆ credit add write put tab took bought likho likh note लिख लिखो चढ़ा जोड़ एंट्री ले",
    "remind": "ਯਾਦ ਰਿਮਾਈਂਡਰ ਸੁਨੇਹਾ ਮੈਸੇਜ ਤਕਾਜ਼ਾ ਤਕਾਜਾ ਵਟਸਐਪ ਵੌਇਸ ਬੋਲੋ ਫੋਨ ਕਰੋ remind reminder message whatsapp voice note yaad याद दिलाओ रिमाइंडर मैसेज व्हाट्सएप वॉइस बोलो",
    "undo": "ਕੱਟ ਮਿਟਾ ਮਿਟਾਓ ਰੱਦ ਗਲਤ ਡਿਲੀਟ ਕੈਂਸਲ ਹਟਾ ਹਟਾਓ ਅਨਡੂ ਪਿਛਲੀ ਪਿਛਲਾ ਆਖਰੀ undo delete cancel remove wrong pichli last काट मिटा रद्द गलत डिलीट कैंसल हटा पिछली पिछला आखिरी",
    "expense": "ਖਰਚਾ ਖਰਚ ਖਰਚੇ ਬਿੱਲ ਕਿਰਾਇਆ ਤਨਖਾਹ ਭਾੜਾ ਭਰੇ ਭਰਿਆ ਲੱਗ spent expense bill rent salary kharcha cost freight transport recharge repair खर्चा खर्च बिल किराया तनख्वाह भाड़ा भरा भरे लगे",
    "chat": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਧੰਨਵਾਦ ਹਾਲ ਸਲਾਹ ਮੌਸਮ ਤੁਸੀਂ ਕਰਾਂ ਮਿਲਦੇ ਹਾਂ ਜੀ ਐਪ hello hi thanks thank morning bye weather ok gst नमस्ते धन्यवाद हाल मौसम आप",
}
CUE = {}
for _c, _ws in _CUES.items():
    for _w in _ws.split():
        CUE.setdefault(normalize(_w), []).append("cue_" + _c)


def mask(toks: list[str], tags: list[str]) -> str:
    out = []
    for w, t in zip(toks, tags):
        if t.startswith("B-"):
            out.append("x" + t[2:].lower())
        elif t.startswith("I-"):
            continue
        elif _is_num(w):
            if not out or out[-1] != "xnum":
                out.append("xnum")
        else:
            out.append(w)
    # cues fire on everything except names: an expense head like "ਬਿਜਲੀ ਦਾ ਬਿੱਲ" is tagged
    # ITEM (and masked), but its words are still strong evidence for EXPENSE.
    cues = sorted({c for w, t in zip(toks, tags) if not t.endswith("NAME") for c in CUE.get(w, [])})
    return " ".join(out + cues)


def make_intent_clf() -> Pipeline:
    feats = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                 token_pattern=r"\S+")),
    ])
    return Pipeline([("f", feats), ("lr", LogisticRegression(max_iter=2000, C=8.0))])


class KhataNLU:
    def __init__(self):
        self.tagger = SlotTagger()
        self.intent = make_intent_clf()

    def fit(self, samples):
        self.tagger.fit(samples)
        self.intent.fit([mask(s["tokens"], s["tags"]) for s in samples], [s["intent"] for s in samples])
        return self

    def analyse(self, text: str) -> dict:
        toks = normalize(text).split()
        surf = surface_tokens(text)
        if len(surf) != len(toks):
            surf = toks
        tags, tag_conf = self.tagger.predict(toks)
        masked = mask(toks, tags)
        proba = self.intent.predict_proba([masked])[0]
        classes = list(self.intent.classes_)
        order = np.argsort(proba)[::-1]
        spans = {"NAME": [], "ITEM": []}
        cur = None
        for w, t in zip(surf, tags):
            if t.startswith("B-"):
                cur = [w]; spans[t[2:]].append(cur)
            elif t.startswith("I-") and cur is not None:
                cur.append(w)
            else:
                cur = None
        return {
            "tokens": toks, "tags": tags, "masked": masked,
            "intent": classes[order[0]], "confidence": float(proba[order[0]]),
            "alternatives": [(classes[k], round(float(proba[k]), 3)) for k in order[1:3]],
            "proba": {str(classes[k]): float(proba[k]) for k in range(len(classes))},
            "names": [" ".join(s) for s in spans["NAME"]],
            "items": [" ".join(s) for s in spans["ITEM"]],
            "tag_confidence": tag_conf,
        }

    def save(self, path: Path):
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path) -> "KhataNLU":
        return joblib.load(path)
