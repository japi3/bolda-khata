"""Customer credit-behaviour features, computed identically for simulated
training data and for the live ledger.

Events are (t_days, kind, amount) with kind in {'credit','payment'}.
Payments are matched to credits first-in-first-out, which gives us the age of
every unpaid rupee and how long each repaid credit took to clear.
"""
from collections import deque

import numpy as np

FEATURES = [
    "log_outstanding",        # how much is owed now
    "oldest_unpaid_days",     # age of the oldest unpaid credit
    "wavg_unpaid_age",        # amount-weighted age of what is owed
    "avg_days_to_repay",      # historical speed of clearing credit (NaN if never)
    "on_time_rate",           # share of matured credits cleared within 30 days (NaN if none)
    "days_since_payment",     # recency of last payment (NaN if never paid)
    "days_since_credit",
    "pay_credit_ratio_60d",   # payments / credits over the last 60 days
    "n_credits_60d",
    "log_avg_credit",
    "outstanding_months",     # outstanding / avg monthly payments (capped)
    "tenure_days",
    "credit_trend",           # last-30d credit vs previous-60d monthly average
]

# Human-readable reasons, used by the explainer. (direction "+" = higher value raises risk)
REASONS = {
    "log_outstanding": ("+", "ਬਕਾਇਆ ਰਕਮ ਵੱਡੀ ਹੈ", "large amount outstanding",
                        "ਬਕਾਇਆ ਥੋੜ੍ਹਾ ਹੈ", "small outstanding amount"),
    "oldest_unpaid_days": ("+", "ਪੁਰਾਣਾ ਉਧਾਰ ਹਾਲੇ ਨਹੀਂ ਮੁੜਿਆ", "old credit still unpaid",
                           "ਕੋਈ ਪੁਰਾਣਾ ਉਧਾਰ ਨਹੀਂ ਖੜ੍ਹਾ", "no old dues"),
    "wavg_unpaid_age": ("+", "ਜ਼ਿਆਦਾਤਰ ਬਕਾਇਆ ਪੁਰਾਣਾ ਹੈ", "most dues are old",
                        "ਬਕਾਇਆ ਨਵਾਂ ਹੈ", "dues are recent"),
    "avg_days_to_repay": ("+", "ਪੈਸੇ ਮੋੜਨ ਵਿੱਚ ਦੇਰ ਕਰਦਾ ਹੈ", "slow to repay historically",
                          "ਜਲਦੀ ਪੈਸੇ ਮੋੜਦਾ ਹੈ", "repays quickly"),
    "on_time_rate": ("-", "ਵੇਲੇ ਸਿਰ ਘੱਟ ਮੋੜਦਾ ਹੈ", "rarely pays on time",
                     "ਵੇਲੇ ਸਿਰ ਪੈਸੇ ਮੋੜਦਾ ਹੈ", "usually pays on time"),
    "days_since_payment": ("+", "ਕਾਫ਼ੀ ਦਿਨਾਂ ਤੋਂ ਕੋਈ ਪੈਸਾ ਨਹੀਂ ਆਇਆ", "no payment in a long time",
                           "ਹਾਲ ਹੀ ਵਿੱਚ ਪੈਸੇ ਦਿੱਤੇ", "paid recently"),
    "days_since_credit": ("-", "ਹਾਲ ਹੀ ਵਿੱਚ ਉਧਾਰ ਲਿਆ", "took credit recently",
                          "ਨਵਾਂ ਉਧਾਰ ਨਹੀਂ ਲੈ ਰਿਹਾ", "not taking new credit"),
    "pay_credit_ratio_60d": ("-", "ਉਧਾਰ ਵੱਧ ਲੈਂਦਾ, ਮੋੜਦਾ ਘੱਟ", "borrows more than repays",
                             "ਜਿੰਨਾ ਲੈਂਦਾ ਉਨਾ ਮੋੜਦਾ ਹੈ", "repays what it borrows"),
    "n_credits_60d": ("+", "ਬਹੁਤ ਵਾਰ ਉਧਾਰ ਲੈਂਦਾ ਹੈ", "borrows very often",
                      "ਕਦੇ ਕਦੇ ਉਧਾਰ ਲੈਂਦਾ ਹੈ", "borrows occasionally"),
    "log_avg_credit": ("+", "ਹਰ ਵਾਰ ਵੱਡਾ ਉਧਾਰ", "large credit per visit",
                       "ਛੋਟੇ ਛੋਟੇ ਉਧਾਰ", "small credit per visit"),
    "outstanding_months": ("+", "ਬਕਾਇਆ ਉਸਦੀ ਮੋੜਨ ਦੀ ਸਮਰੱਥਾ ਤੋਂ ਵੱਧ", "dues exceed usual repayment capacity",
                           "ਬਕਾਇਆ ਸਮਰੱਥਾ ਅੰਦਰ ਹੈ", "dues within repayment capacity"),
    "tenure_days": ("-", "ਨਵਾਂ ਗਾਹਕ ਹੈ", "new customer",
                    "ਪੁਰਾਣਾ ਗਾਹਕ ਹੈ", "long-standing customer"),
    "credit_trend": ("+", "ਉਧਾਰ ਤੇਜ਼ੀ ਨਾਲ ਵਧ ਰਿਹਾ ਹੈ", "credit growing fast",
                     "ਉਧਾਰ ਸਥਿਰ ਹੈ", "credit is stable"),
}


def compute(events: list[tuple[float, str, float]], now: float) -> dict:
    """events: (t_days, kind, amount) sorted by time; only events with t <= now are used."""
    ev = [e for e in events if e[0] <= now]
    queue: deque = deque()             # [t_credit, remaining]
    repay_days, matured, on_time = [], 0, 0
    first_t = ev[0][0] if ev else now
    last_pay = last_credit = None
    for t, kind, amt in ev:
        if kind == "credit":
            queue.append([t, amt]); last_credit = t
        else:
            last_pay = t
            rem = amt
            while rem > 1e-9 and queue:
                head = queue[0]
                take = min(rem, head[1])
                head[1] -= take; rem -= take
                if head[1] <= 1e-9:
                    d = t - head[0]
                    repay_days.append(d)
                    queue.popleft()
    # matured credits: credits older than 30 days (repaid or not)
    for d in repay_days:
        matured += 1; on_time += d <= 30
    for tc, rem in queue:
        if now - tc > 30:
            matured += 1
    outstanding = sum(r for _, r in queue)
    ages = [(now - tc, r) for tc, r in queue if r > 0]
    credits60 = [a for t, k, a in ev if k == "credit" and t > now - 60]
    pays60 = [a for t, k, a in ev if k == "payment" and t > now - 60]
    credits30 = sum(a for t, k, a in ev if k == "credit" and t > now - 30)
    credits_prev = sum(a for t, k, a in ev if k == "credit" and now - 90 < t <= now - 30) / 2
    all_credits = [a for _, k, a in ev if k == "credit"]
    pays90 = sum(a for t, k, a in ev if k == "payment" and t > now - 90)
    monthly_pay = pays90 / 3
    return {
        "log_outstanding": float(np.log1p(max(outstanding, 0))),
        "oldest_unpaid_days": max((a for a, _ in ages), default=0.0),
        "wavg_unpaid_age": (sum(a * r for a, r in ages) / outstanding) if outstanding > 0 else 0.0,
        "avg_days_to_repay": float(np.mean(repay_days)) if repay_days else np.nan,
        "on_time_rate": (on_time / matured) if matured else np.nan,
        "days_since_payment": (now - last_pay) if last_pay is not None else np.nan,
        "days_since_credit": (now - last_credit) if last_credit is not None else np.nan,
        "pay_credit_ratio_60d": min(sum(pays60) / sum(credits60), 3.0) if credits60 else
                                (1.5 if pays60 else np.nan),
        "n_credits_60d": float(len(credits60)),
        "log_avg_credit": float(np.log1p(np.mean(all_credits))) if all_credits else 0.0,
        "outstanding_months": min(outstanding / monthly_pay, 24.0) if monthly_pay > 0 else
                              (24.0 if outstanding > 0 else 0.0),
        "tenure_days": now - first_t,
        "credit_trend": min(credits30 / credits_prev, 5.0) if credits_prev > 0 else
                        (2.0 if credits30 > 0 else 1.0),
        "_outstanding": outstanding,
        "_monthly_pay": monthly_pay,
        "_n_events": len(ev),
        "_repay_days": repay_days,
    }


def vector(f: dict) -> list[float]:
    return [f[k] for k in FEATURES]


# Hindi versions: (risk reason, strength)
REASONS_HI = {'log_outstanding': ('बकाया रकम बड़ी है', 'बकाया थोड़ा है'), 'oldest_unpaid_days': ('पुराना उधार अभी तक नहीं लौटा', 'कोई पुराना उधार बाकी नहीं'), 'wavg_unpaid_age': ('ज़्यादातर बकाया पुराना है', 'बकाया नया है'), 'avg_days_to_repay': ('पैसे लौटाने में देर करता है', 'जल्दी पैसे लौटाता है'), 'on_time_rate': ('समय पर कम लौटाता है', 'समय पर पैसे लौटाता है'), 'days_since_payment': ('काफ़ी दिनों से कोई पैसा नहीं आया', 'हाल ही में पैसे दिए'), 'days_since_credit': ('हाल ही में उधार लिया', 'नया उधार नहीं ले रहा'), 'pay_credit_ratio_60d': ('उधार ज़्यादा लेता है, लौटाता कम', 'जितना लेता है उतना लौटाता है'), 'n_credits_60d': ('बहुत बार उधार लेता है', 'कभी-कभी उधार लेता है'), 'log_avg_credit': ('हर बार बड़ा उधार', 'छोटे-छोटे उधार'), 'outstanding_months': ('बकाया उसकी लौटाने की क्षमता से ज़्यादा', 'बकाया क्षमता के अंदर है'), 'tenure_days': ('नया ग्राहक है', 'पुराना ग्राहक है'), 'credit_trend': ('उधार तेज़ी से बढ़ रहा है', 'उधार स्थिर है')}
