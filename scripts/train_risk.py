"""Train the customer credit-risk model on simulated khata histories.

Compares a gradient-boosted model against two baselines a shopkeeper might use:
  - "oldest dues" rule of thumb (risk = age of oldest unpaid credit)
  - logistic regression on the same features
Splits by customer, calibrates probabilities on a validation set (isotonic),
and saves models/risk.joblib + models/risk_report.json.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.frozen import FrozenEstimator  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app import config  # noqa: E402
from app.ml.features import FEATURES, compute, vector  # noqa: E402
from app.ml.simulate import label, simulate_customer  # noqa: E402


def build(n_customers: int, seed: int):
    rng = np.random.default_rng(seed)
    X, y, g, meta = [], [], [], []
    for cid in range(n_customers):
        events, m = simulate_customer(rng)
        for cutoff in rng.uniform(90, 190, size=2):
            past = [e for e in events if e[0] <= cutoff]
            if len(past) < 2:
                continue
            f = compute(events, cutoff)
            X.append(vector(f)); y.append(label(events, cutoff)); g.append(cid); meta.append(m["type"])
    return np.array(X, float), np.array(y), np.array(g), np.array(meta)


def top_precision(y, p, frac=0.2):
    k = max(1, int(len(p) * frac))
    idx = np.argsort(p)[::-1][:k]
    return float(y[idx].mean())


def main():
    t0 = time.time()
    X, y, g, meta = build(9000, seed=42)
    print(f"{len(y)} samples from {len(set(g))} simulated customers, risky rate={y.mean():.3f}")
    rng = np.random.default_rng(0)
    custs = np.unique(g); rng.shuffle(custs)
    n = len(custs)
    tr, va = set(custs[: int(.6 * n)]), set(custs[int(.6 * n): int(.8 * n)])
    mtr = np.array([c in tr for c in g]); mva = np.array([c in va for c in g]); mte = ~(mtr | mva)

    gbm = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=24,
                                         l2_regularization=1.0, early_stopping=True, random_state=0)
    gbm.fit(X[mtr], y[mtr])
    cal = CalibratedClassifierCV(FrozenEstimator(gbm), method="isotonic").fit(X[mva], y[mva])

    lr = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                       LogisticRegression(max_iter=2000)).fit(X[mtr], y[mtr])

    yt = y[mte]
    p_gbm = cal.predict_proba(X[mte])[:, 1]
    p_lr = lr.predict_proba(X[mte])[:, 1]
    p_rule = X[mte][:, FEATURES.index("oldest_unpaid_days")]
    res = {}
    for name, p in [("rule_oldest_dues", p_rule), ("logistic_regression", p_lr), ("gradient_boosting", p_gbm)]:
        res[name] = {"auc": round(roc_auc_score(yt, p), 4),
                     "precision_top20pct": round(top_precision(yt, p), 4)}
        if name != "rule_oldest_dues":
            res[name]["brier"] = round(brier_score_loss(yt, p), 4)
        print(f"  {name:22s} AUC={res[name]['auc']:.3f}  precision@top20%={res[name]['precision_top20pct']:.3f}"
              + (f"  Brier={res[name]['brier']:.3f}" if 'brier' in res[name] else ""))

    # permutation importance (AUC drop) for the report
    imp = {}
    base = roc_auc_score(yt, p_gbm)
    for j, fname in enumerate(FEATURES):
        Xp = X[mte].copy(); Xp[:, j] = rng.permutation(Xp[:, j])
        imp[fname] = round(base - roc_auc_score(yt, cal.predict_proba(Xp)[:, 1]), 4)
    imp = dict(sorted(imp.items(), key=lambda kv: -kv[1]))
    print("  top features:", list(imp.items())[:5])

    # reference profile = median of customers who were NOT risky (used by the explainer)
    ref = np.nanmedian(X[mtr][y[mtr] == 0], axis=0)
    joblib.dump({"model": cal, "features": FEATURES, "reference": ref, "base_rate": float(y.mean())},
                config.MODEL_DIR / "risk.joblib")
    report = {"samples": int(len(y)), "customers": int(len(set(g))), "risky_rate": round(float(y.mean()), 4),
              "test": res, "permutation_importance_auc_drop": imp, "seconds": round(time.time() - t0, 1)}
    (config.MODEL_DIR / "risk_report.json").write_text(json.dumps(report, indent=2))
    print("saved models/risk.joblib in", report["seconds"], "s")


if __name__ == "__main__":
    main()
