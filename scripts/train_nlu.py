"""Train + evaluate the on-device Punjabi NLU.

Two evaluations:
  A. random split            - in-distribution sanity check
  B. held-out *templates*    - whole sentence patterns never seen in training,
                               i.e. how well it generalises to new phrasings.
Writes models/nlu.joblib and models/nlu_report.json.
"""
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.metrics import classification_report  # noqa: E402

from app import config  # noqa: E402
from app.nlu.datagen import T, generate  # noqa: E402
from app.nlu.model import KhataNLU  # noqa: E402


def spans(tags):
    out, cur = set(), None
    for i, t in enumerate(tags + ["O"]):
        if cur and not t.startswith("I-"):
            out.add((cur[0], cur[1], i)); cur = None
        if t.startswith("B-"):
            cur = (t[2:], i)
    return out


def evaluate(model, test):
    y_true, y_pred, tp, fp, fn = [], [], 0, 0, 0
    for s in test:
        r = model.analyse(" ".join(s["tokens"]))
        y_true.append(s["intent"]); y_pred.append(r["intent"])
        g, p = spans(s["tags"]), spans(r["tags"])
        tp += len(g & p); fp += len(p - g); fn += len(g - p)
    acc = sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true)
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    return {"intent_accuracy": round(acc, 4), "slot_f1": round(f1, 4), "n": len(test),
            "report": classification_report(y_true, y_pred, output_dict=True, zero_division=0)}


def main():
    t0 = time.time()
    data = generate(n_per_template=60, seed=7)
    print(f"generated {len(data)} samples across {sum(len(v) for v in T.values())} templates")

    # A. random split
    cut = int(len(data) * 0.8)
    m = KhataNLU().fit(data[:cut])
    a = evaluate(m, data[cut:])
    print(f"[A random split]      intent acc={a['intent_accuracy']:.3f}  slot F1={a['slot_f1']:.3f}")

    # B. held-out templates (~25% of each intent's patterns), different random names/amounts
    rng = random.Random(1)
    train_t, test_t = {}, {}
    for intent, temps in T.items():
        idx = list(range(len(temps))); rng.shuffle(idx)
        k = max(1, len(temps) // 4)
        test_t[intent] = [temps[i] for i in idx[:k]]
        train_t[intent] = [temps[i] for i in idx[k:]]
    mb = KhataNLU().fit(generate(60, seed=11, templates=train_t))
    b = evaluate(mb, generate(20, seed=99, templates=test_t))
    print(f"[B unseen templates]  intent acc={b['intent_accuracy']:.3f}  slot F1={b['slot_f1']:.3f}")
    for k, v in b["report"].items():
        if isinstance(v, dict) and k in T:
            print(f"   {k:8s} f1={v['f1-score']:.2f}  n={int(v['support'])}")

    final = KhataNLU().fit(data)
    final.save(config.MODEL_DIR / "nlu.joblib")
    rep = {"random_split": {k: a[k] for k in ("intent_accuracy", "slot_f1", "n")},
           "unseen_templates": {k: b[k] for k in ("intent_accuracy", "slot_f1", "n")},
           "unseen_templates_per_intent": {k: round(v["f1-score"], 3) for k, v in b["report"].items()
                                           if isinstance(v, dict) and k in T},
           "train_samples": len(data), "seconds": round(time.time() - t0, 1)}
    (config.MODEL_DIR / "nlu_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    print("saved models/nlu.joblib", rep["seconds"], "s")


if __name__ == "__main__":
    main()
