"""Train the "please repeat" detector: should the app refuse to write an entry because
the recording was probably misheard?

Data: the 122 hard-set commands x 3 conditions (clean / 8 dB / 0 dB shop noise). For each:
  audio features  - blind SNR estimate etc. (app/audio_quality.py), from a fresh mix at
                    the same SNR as the cached Prisma transcript
  language model  - ensemble confidence, margin, tagger confidence, transcript speed
  label           - 1 if the command would be written WRONG (intent, amount or customer)
Only commands the app would write (credit/payment/sale/expense) are used.

Evaluation: 5-fold cross-validation grouped by sentence, so the same command never appears in
train and test. Inside each fold the ask-threshold is chosen on the TRAINING folds to minimise
COST_RATIO x (wrong writes saved) + (correct commands asked to repeat). Compared against
single-signal baselines and other cost ratios. (A first version capped false asks at 5%; at
that cap audio features added nothing, because in loud noise even correct-looking commands
are unreliable, so the cap was replaced by this cost rule.)
Saves models/repeat_detector.joblib + models/repeat_report.json.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app import audio_quality as aq, config, gnani  # noqa: E402
from eval.hard_test import CASES, CUSTOMERS  # noqa: E402
from scripts.eval_hard import TRANSACTIONAL, command, load  # noqa: E402
from app.nlu.parser import DIRECTION_DOUBT  # noqa: E402
from app.nlu.punjabi import amount_conflict, find_numbers  # noqa: E402
from scripts.eval_voice import CACHE, SNR_DB, SNR_LOUD_DB, VOICES, mix, shop_noise  # noqa: E402

WRITES = TRANSACTIONAL
FEATURES = ["snr_db", "dynamic_db", "speech_frac", "conf", "margin", "tag_conf", "chars_per_s"]
COST_RATIO = 3.0   # a wrong ledger entry is as bad as 3 unnecessary "is that right?" taps. (Was 5; after retraining the NLU, 3 was at least as good in every condition, so switched — chosen after seeing CV results.)


def lm_features(analysis: dict, transcript: str, duration: float) -> dict:
    p = sorted(analysis["proba"].values(), reverse=True)
    return {"conf": p[0], "margin": p[0] - p[1], "tag_conf": analysis.get("tag_confidence", 1.0),
            "chars_per_s": len(transcript.replace(" ", "")) / max(duration, 0.5)}


def correct(c: dict, intent, amount, cust) -> bool:
    if c["intent"] != intent:
        return False
    if intent in TRANSACTIONAL:
        ok_a = (c["amount"] == amount) if amount is not None else (c["amount"] is None and c["settle"])
        if not ok_a:
            return False
    if cust is not None:
        got = c["customer"].get("name") if c["customer"]["status"] in ("match", "new") else None
        return got == cust
    return True


async def build():
    cache = json.loads(CACHE.read_text())
    clips = [aq.read_wav((await gnani.synthesize(t, voice=VOICES[i % 2]))[1]) for i, (t, *_r) in enumerate(CASES)]
    model = load("ensemble")
    customers = [{"id": i + 1, "name": n} for i, n in enumerate(CUSTOMERS)]
    rng = np.random.default_rng(7)
    rows = []
    for i, ((x, sr), (text, intent, amount, cust)) in enumerate(zip(clips, CASES)):
        others = [c[0] for j, c in enumerate(clips) if j != i]
        noise = shop_noise(len(x), others, rng)
        for cond, audio in (("clean", x), ("noisy", mix(x, noise, SNR_DB)), ("loud", mix(x, noise, SNR_LOUD_DB))):
            tr = cache[str(i)][cond]
            c = command(model, tr, customers)
            if c["intent"] not in WRITES:
                continue   # the detector only guards ledger writes
            af = aq.features(audio, sr)
            f = {**{k: af[k] for k in ("snr_db", "dynamic_db", "speech_frac")},
                 **lm_features(c["raw"], tr, af["duration_s"])}
            pr = c["raw"]["proba"]
            other = {"CREDIT": "PAYMENT", "PAYMENT": "CREDIT"}.get(c["intent"])
            rule_ask = bool((other and pr.get(other, 0) > DIRECTION_DOUBT)
                            or amount_conflict(find_numbers(c["raw"]["tokens"])))
            rows.append({"case": i, "cond": cond, "wrong": int(not correct(c, intent, amount, cust)),
                         "rule_ask": rule_ask, **f})
    return rows


def threshold_for(scores: np.ndarray, y: np.ndarray, ratio: float) -> float:
    best, best_cost = 1.0, float("inf")
    for th in np.unique(np.concatenate([scores, [1.0]])):
        ask = scores > th
        cost = ratio * np.sum((y == 1) & ~ask) + np.sum((y == 0) & ask)
        if cost < best_cost:
            best, best_cost = float(th), cost
    return best


def cv(rows, feats, ratio=COST_RATIO):
    X = np.array([[r[f] for f in feats] for r in rows]); y = np.array([r["wrong"] for r in rows])
    g = np.array([r["case"] for r in rows])
    ask = np.zeros(len(y), bool)
    for tr, te in GroupKFold(5).split(X, y, g):
        m = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)).fit(X[tr], y[tr])
        th = threshold_for(m.predict_proba(X[tr])[:, 1], y[tr], ratio)
        ask[te] = m.predict_proba(X[te])[:, 1] > th
    return ask, y


def summarise(rows, ask, y):
    out = {}
    for cond in ("clean", "noisy", "loud", "all"):
        m = np.array([cond == "all" or r["cond"] == cond for r in rows])
        w, a = y[m] == 1, ask[m]
        out[cond] = {"writes": int(m.sum()), "wrong_writes_without_detector": int(w.sum()),
                     "wrong_writes_caught": int((w & a).sum()), "wrong_writes_saved": int((w & ~a).sum()),
                     "correct_but_asked_to_repeat": int((~w & a).sum()),
                     "ask_rate": round(float(a.mean()), 3)}
    return out


def main():
    rows = asyncio.run(build())
    print(f"{len(rows)} write commands, {sum(r['wrong'] for r in rows)} would be written wrong")
    report = {}
    runs = [("snr_only", ["snr_db"], COST_RATIO), ("language_model_only", ["conf", "margin", "tag_conf"], COST_RATIO),
            ("combined", FEATURES, COST_RATIO), ("combined_ratio3", FEATURES, 3.0), ("combined_ratio10", FEATURES, 10.0)]
    for name, feats, ratio in runs:
        ask, y = cv(rows, feats, ratio)
        report[name] = summarise(rows, ask, y)
        a = report[name]["all"]
        print(f"{name:20s} caught {a['wrong_writes_caught']}/{a['wrong_writes_without_detector']} wrong writes, "
              f"asked {a['correct_but_asked_to_repeat']} correct ones to repeat  |  " +
              "  ".join(f"{c}: {report[name][c]['wrong_writes_caught']}/{report[name][c]['wrong_writes_without_detector']}"
                        f" (+{report[name][c]['correct_but_asked_to_repeat']} false)" for c in ("clean", "noisy", "loud")))
    # all safeguards together: direction rule + "which amount?" + detector
    ask, y = cv(rows, FEATURES)
    rules = np.array([r["rule_ask"] for r in rows])
    report["rules_only"] = summarise(rows, rules, y)
    report["all_safeguards"] = summarise(rows, ask | rules, y)
    # shipped: the detector only acts when the recording is loud (blind SNR below the existing
    # "hold the phone closer" cut-off), so normal and busy-shop commands are not interrupted
    from app.repeat_detector import LOUD_SNR_DB
    loud = np.array([r["snr_db"] < LOUD_SNR_DB for r in rows])
    report["all_safeguards_loud_only"] = summarise(rows, (ask & loud) | rules, y)
    for name in ("rules_only", "all_safeguards", "all_safeguards_loud_only"):
        print(f"{name:20s} " + "  ".join(
            f"{c}: {report[name][c]['wrong_writes_saved']} wrong saved silently / {report[name][c]['wrong_writes_without_detector']}"
            f" ({report[name][c]['correct_but_asked_to_repeat']} correct ones questioned)" for c in ("clean", "noisy", "loud")))
    # final model on everything, same threshold rule
    X = np.array([[r[f] for f in FEATURES] for r in rows]); y = np.array([r["wrong"] for r in rows])
    m = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000)).fit(X, y)
    th = threshold_for(m.predict_proba(X)[:, 1], y, COST_RATIO)
    coefs = dict(zip(FEATURES, np.round(m[-1].coef_[0], 3).tolist()))
    joblib.dump({"model": m, "features": FEATURES, "threshold": th}, config.MODEL_DIR / "repeat_detector.joblib")
    report["final"] = {"threshold": round(th, 4), "cost_ratio": COST_RATIO, "coefficients_standardised": coefs, "n": len(rows)}
    (config.MODEL_DIR / "repeat_report.json").write_text(json.dumps(report, indent=1))
    print("coefficients:", coefs, "threshold", round(th, 3))


if __name__ == "__main__":
    main()
