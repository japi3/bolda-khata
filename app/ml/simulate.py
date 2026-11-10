"""Behavioural simulator of kirana-store credit customers.

Real per-customer khata histories are not publicly available, so we simulate
them from interpretable latent traits, then train on observable features only:

  reliability   r  ~ mixture of Betas (good / average / slow / chronic defaulter)
  visit rate    λ  credit purchases per week
  ticket size      log-normal
  pay cycle        settles roughly every P days, P shrinking with r
  pay fraction     how much of the balance is cleared at each settlement
  shocks           any customer may hit financial distress (job loss, illness,
                   harvest failure) and stop paying while still borrowing for a while

Label (from a cutoff day): did the customer fail to repay at least half of what
they owed at the cutoff within the next 45 days?
"""
import numpy as np

HORIZON = 45


def simulate_customer(rng: np.random.Generator, days: int = 240):
    kind = rng.choice(["good", "average", "slow", "defaulter"], p=[0.38, 0.32, 0.20, 0.10])
    r = {"good": rng.beta(18, 2), "average": rng.beta(7, 3), "slow": rng.beta(4, 5),
         "defaulter": rng.beta(1.5, 8)}[kind]
    lam = rng.uniform(0.3, 4.0) / 7                       # credits per day
    ticket = rng.lognormal(np.log(rng.uniform(80, 1200)), 0.5)
    cycle = max(3.0, rng.normal(40 - 32 * r, 4))          # days between settlements
    pay_frac = np.clip(rng.normal(0.35 + 0.65 * r, 0.12), 0.05, 1.0)
    start = rng.integers(0, 60)
    shock_day = rng.integers(start + 20, days) if rng.random() < 0.18 else None
    shock_len = rng.integers(25, 120)
    recover = rng.random() < 0.35

    events, bal = [], 0.0
    next_settle = start + rng.exponential(cycle)
    for d in range(start, days):
        in_shock = shock_day is not None and shock_day <= d < shock_day + shock_len
        stops_buying = in_shock and d > shock_day + 20
        if not stops_buying and rng.random() < lam * (1.3 if in_shock else 1.0):
            amt = round(float(ticket * rng.lognormal(0, 0.35)) / 10) * 10 or 10
            events.append((d + rng.random() * 0.5, "credit", amt)); bal += amt
        if shock_day is not None and d >= shock_day + shock_len and not recover:
            continue  # never pays again
        if d >= next_settle and bal > 0:
            if in_shock:
                p_pay, frac = 0.04, 0.15
            else:
                p_pay, frac = 0.45 + 0.55 * r, pay_frac
            if rng.random() < p_pay:
                amt = round(bal * min(1.0, frac * rng.uniform(0.7, 1.3)) / 10) * 10
                if amt > 0:
                    amt = min(amt, bal)
                    events.append((d + 0.6, "payment", amt)); bal -= amt
            next_settle = d + max(2.0, rng.exponential(cycle))
    events.sort()
    return events, {"type": kind, "reliability": r}


def label(events, cutoff: float) -> int | None:
    owed = sum(a if k == "credit" else -a for t, k, a in events if t <= cutoff)
    if owed <= 50:
        return 0
    repaid = sum(a for t, k, a in events if k == "payment" and cutoff < t <= cutoff + HORIZON)
    return int(repaid < 0.5 * owed)
