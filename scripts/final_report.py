"""Final NLU comparison on the hard test set -> models/nlu_comparison.json.
Scores MEMM, MuRIL and the shipped ensemble on text + every cached voice condition,
plus how the credit/payment confirmation rule behaves. No API calls."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.nlu.parser import DIRECTION_DOUBT  # noqa: E402
from eval.hard_test import CASES  # noqa: E402
from scripts.eval_hard import load, score  # noqa: E402
from scripts.eval_voice import CACHE, cer  # noqa: E402

KEEP = ("fully_correct", "intent_acc", "amount_acc", "customer_acc", "ms_per_utterance")


def direction_check(model, texts):
    wrong = asked = asked_right = n = 0
    for t, (_, intent, *_r) in zip(texts, CASES):
        if intent not in ("CREDIT", "PAYMENT"):
            continue
        r = model.analyse(t)
        if r["intent"] not in ("CREDIT", "PAYMENT"):
            continue
        n += 1
        other = r["proba"]["PAYMENT" if r["intent"] == "CREDIT" else "CREDIT"]
        if other > DIRECTION_DOUBT:
            asked += 1; asked_right += r["intent"] == intent
        elif r["intent"] != intent:
            wrong += 1
    return {"n": n, "wrong_direction_saved": wrong, "asked": asked, "asked_but_model_was_right": asked_right}


def main():
    cache = json.loads(CACHE.read_text())
    conds = {"text": [c[0] for c in CASES]}
    for cond in ("clean", "noisy", "loud"):
        if all(cond in cache[str(i)] for i in range(len(CASES))):
            conds[cond] = [cache[str(i)][cond] for i in range(len(CASES))]
    out = {"n": len(CASES), "conditions": {}, "prisma_cer": {}}
    for cond, texts in conds.items():
        if cond != "text":
            out["prisma_cer"][cond] = round(sum(cer(c[0], t) for c, t in zip(CASES, texts)) / len(CASES), 4)
    for name in ("memm", "muril", "ensemble"):
        m = load(name)
        for cond, texts in conds.items():
            r = score(m, [(t, *c[1:]) for t, c in zip(texts, CASES)], label=name)
            out["conditions"].setdefault(cond, {})[name] = {k: r[k] for k in KEEP}
        if name == "ensemble":
            out["direction_check"] = {cond: direction_check(m, texts) for cond, texts in conds.items()}
    (config.MODEL_DIR / "nlu_comparison.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("Prisma CER:", out["prisma_cer"])
    for cond, d in out["conditions"].items():
        print(cond.ljust(6), "  ".join(f"{k} {v['fully_correct']:.3f}" for k, v in d.items()))
    print("direction check:", out["direction_check"])


if __name__ == "__main__":
    main()
