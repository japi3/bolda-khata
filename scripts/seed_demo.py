"""Seed a realistic 90-day demo shop: customers with distinct repayment personalities,
daily cash sales and expenses. Usage:  python scripts/seed_demo.py [--reset]"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db  # noqa: E402

DAY = 86400
ITEMS = ["ਆਟਾ", "ਦਾਲ", "ਖੰਡ", "ਚਾਹ ਪੱਤੀ", "ਸਰ੍ਹੋਂ ਦਾ ਤੇਲ", "ਦੁੱਧ", "ਚੌਲ", "ਸਾਬਣ", "ਘਿਓ", "ਬਿਸਕੁਟ", None, None]

# name, phone, personality: (visits/week, avg ticket, settle every N days, fraction paid, stops paying at day-ago or None)
CUSTOMERS = [
    ("ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ", "9876501234", (3.0, 260, 7, 1.0, None)),       # weekly settler, very reliable
    ("ਹਰਪ੍ਰੀਤ ਕੌਰ", "9814022345", (2.0, 420, 15, 0.95, None)),       # fortnightly, reliable
    ("ਰਮੇਸ਼ ਕੁਮਾਰ", "9779033456", (2.5, 350, 30, 0.85, None)),       # monthly payer
    ("ਬਿੱਟੂ", "9888044567", (3.5, 300, 20, 0.45, 38)),               # shock: stopped paying ~38 days ago
    ("ਸੁਖਵਿੰਦਰ", "9915055678", (1.2, 900, 40, 0.5, None)),           # big tickets, slow and partial
    ("ਮਾਸਟਰ ਜੀ", "9463066789", (1.0, 500, 10, 1.0, None)),            # reliable
    ("ਪਿੰਕੀ", None, (2.0, 180, 25, 0.6, None)),                       # small, slowish
    ("ਕੁਲਦੀਪ", "9501077890", (1.5, 650, 60, 0.3, None)),             # chronic late payer
    ("ਸਿਮਰਨ", None, (0.8, 220, 12, 1.0, None)),
    ("ਜਸਵੀਰ", "9872088901", (2.2, 380, 18, 0.8, None)),
]


def main():
    if "--reset" in sys.argv and config.DB_PATH.exists():
        db._con = None
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(config.DB_PATH) + suffix)
            if p.exists():
                p.unlink()
    rng = random.Random(2026)
    now = time.time()
    start = now - 90 * DAY
    db.set_settings({"shop_name": "ਸ਼ਰਮਾ ਕਰਿਆਨਾ ਸਟੋਰ", "shop_name_en": "Sharma Kirana Store",
                     "shop_name_hi": "शर्मा किराना स्टोर", "owner_name": "ਰਾਜੇਸ਼ ਸ਼ਰਮਾ"})
    n = 0
    for name, phone, (visits, ticket, cycle, frac, stop_ago) in CUSTOMERS:
        cid, _ = db.get_or_create_customer(name)
        if phone:
            db.update_customer(cid, phone=phone)
        bal, next_settle = 0.0, start + rng.uniform(0, cycle) * DAY
        t = start + rng.uniform(0, 5) * DAY
        while t < now - 0.3 * DAY:
            stopped = stop_ago is not None and t > now - stop_ago * DAY
            if rng.random() < visits / 7:
                amt = max(20, round(rng.lognormvariate(0, 0.4) * ticket / 10) * 10)
                db.add_txn("credit", amt, customer_id=cid, item=rng.choice(ITEMS), source="seed",
                           ts=t + rng.uniform(8, 20) * 3600)
                bal += amt; n += 1
            if t >= next_settle and bal > 0 and not stopped:
                pay = round(bal * min(1.0, frac * rng.uniform(0.8, 1.15)) / 10) * 10
                if pay > 0:
                    db.add_txn("payment", min(pay, bal), customer_id=cid, source="seed", ts=t + 19 * 3600)
                    bal -= min(pay, bal); n += 1
                next_settle = t + max(3, rng.gauss(cycle, cycle * 0.25)) * DAY
            t += DAY
    # cash sales + expenses
    d = start
    while d < now - DAY * 0.5:
        for _ in range(rng.randint(2, 5)):
            db.add_txn("sale", round(rng.lognormvariate(5.6, 0.6) / 10) * 10 or 50, item=rng.choice(ITEMS),
                       source="seed", ts=d + rng.uniform(8, 21) * 3600); n += 1
        if rng.random() < 0.15:
            head, amt = rng.choice([("ਚਾਹ ਪਾਣੀ", 60), ("ਭਾੜਾ", 400), ("ਮਾਲ ਦੀ ਖਰੀਦ", 3500), ("ਸਫ਼ਾਈ", 150)])
            db.add_txn("expense", amt, item=head, source="seed", ts=d + 12 * 3600); n += 1
        if abs((d - start) / DAY - 30) < 0.5 or abs((d - start) / DAY - 60) < 0.5:
            db.add_txn("expense", 2400, item="ਬਿਜਲੀ ਦਾ ਬਿੱਲ", source="seed", ts=d + 11 * 3600)
            db.add_txn("expense", 8000, item="ਦੁਕਾਨ ਦਾ ਕਿਰਾਇਆ", source="seed", ts=d + 11 * 3600); n += 2
        d += DAY
    print(f"seeded {n} entries for {len(CUSTOMERS)} customers into {config.DB_PATH}")
    from app.ml.risk import score_customer
    for c in db.customers():
        s = score_customer(c["id"])
        print(f"  {c['name']:16s} bal ₹{c['balance']:>8,.0f}  trust {s['trust']:>3}  {s['band']['en']:8s} "
              f"{', '.join(r['en'] for r in s['reasons'][:2])}")


if __name__ == "__main__":
    main()
