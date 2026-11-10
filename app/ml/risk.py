"""Score live customers with the trained risk model and explain each score.

Explanation method: for every feature, swap the customer's value for that of a
typical reliable customer and measure how much the predicted risk changes. The
features whose swap lowers the risk the most are the reasons for the risk
(a simple, model-agnostic counterfactual attribution).
"""
import time

import joblib
import numpy as np

from .. import config, db
from .features import FEATURES, REASONS, REASONS_HI, compute, vector

_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(config.MODEL_DIR / "risk.joblib")
    return _bundle


def band(trust: int) -> dict:
    # trust = 100 * (1 - calibrated P(fails to repay half the dues within 45 days)).
    # Base rate in training is ~25%, so risk >= 40% (1.6x base) is flagged red,
    # risk 20-40% amber, below 20% green.
    if trust >= 80:
        return {"key": "good", "pa": "ਭਰੋਸੇਮੰਦ", "en": "Reliable", "hi": "भरोसेमंद"}
    if trust >= 60:
        return {"key": "watch", "pa": "ਧਿਆਨ ਰੱਖੋ", "en": "Watch", "hi": "ध्यान रखें"}
    return {"key": "risky", "pa": "ਖਤਰਾ", "en": "Risky", "hi": "ख़तरा"}


def _days(events):
    return [(ts / 86400.0, k, a) for ts, k, a in events]


def score_customer(cid: int, now: float | None = None) -> dict:
    b = _load()
    model, ref = b["model"], b["reference"]
    now_d = (now or time.time()) / 86400.0
    events = _days(db.customer_events(cid))
    if not events:
        return {"trust": None, "band": {"key": "new", "pa": "ਨਵਾਂ", "en": "New", "hi": "नया"}, "risk": None,
                "reasons": [], "strengths": [], "low_data": True, "suggested_limit": None}
    f = compute(events, now_d)
    x = np.array([vector(f)], float)
    p = float(model.predict_proba(x)[0, 1])

    # counterfactual attribution
    deltas = []
    X = np.repeat(x, len(FEATURES), axis=0)
    for j in range(len(FEATURES)):
        X[j, j] = ref[j]
    pj = model.predict_proba(X)[:, 1]
    for j, name in enumerate(FEATURES):
        if np.isnan(x[0, j]):
            continue
        deltas.append((p - pj[j], name))
    deltas.sort(reverse=True)
    reasons = [{"feature": n, "pa": REASONS[n][1], "en": REASONS[n][2], "hi": REASONS_HI[n][0], "impact": round(d, 3)}
               for d, n in deltas if d > 0.02][:3]
    strengths = [{"feature": n, "pa": REASONS[n][3], "en": REASONS[n][4], "hi": REASONS_HI[n][1], "impact": round(d, 3)}
                 for d, n in sorted(deltas) if d < -0.02][:2]

    trust = int(round(100 * (1 - p)))
    low_data = f["_n_events"] < 4 or f["tenure_days"] < 14
    # Suggested further credit: what they usually repay in a month, scaled by trust,
    # minus what is already outstanding.
    monthly = f["_monthly_pay"]
    limit = max(0.0, monthly * 1.5 * (1 - p) - 0.5 * f["_outstanding"]) if monthly > 0 else 0.0
    limit = int(round(limit / 50.0) * 50)
    rd = f["_repay_days"]
    return {
        "trust": trust, "risk": round(p, 3), "band": band(trust), "reasons": reasons, "strengths": strengths,
        "low_data": low_data, "suggested_limit": limit,
        "typical_repay_days": round(float(np.median(rd)), 1) if rd else None,
        "oldest_unpaid_days": round(f["oldest_unpaid_days"], 1),
        "features": {k: (None if (isinstance(v, float) and np.isnan(v)) else round(float(v), 3))
                     for k, v in f.items() if not k.startswith("_")},
    }


def portfolio() -> dict:
    """Shop-wide risk picture + expected collections this week."""
    rows = []
    for c in db.customers():
        if c["n_txns"] == 0:
            continue
        s = score_customer(c["id"])
        rows.append({**c, "score": s})
    owed = [r for r in rows if r["balance"] > 0]
    at_risk = sum(r["balance"] for r in owed if r["score"]["band"]["key"] == "risky")
    total = sum(r["balance"] for r in owed)
    # Expected collections in 7 days: P(pay soon) ~ (1-risk) adjusted by typical repay speed
    exp7 = 0.0
    for r in owed:
        s = r["score"]
        speed = s.get("typical_repay_days") or 30.0
        p7 = (1 - (s["risk"] or 0.3)) * min(1.0, 7.0 / max(speed, 1.0))
        exp7 += r["balance"] * 0.6 * p7   # partial settlements are the norm
    return {
        "total_outstanding": round(total, 2), "at_risk": round(at_risk, 2),
        "at_risk_share": round(at_risk / total, 3) if total else 0.0,
        "expected_collections_7d": round(exp7 / 10) * 10,
        "customers": sorted(rows, key=lambda r: (r["score"]["trust"] is None, r["score"]["trust"] or 0)),
    }
