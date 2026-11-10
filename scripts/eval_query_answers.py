"""Check that smart questions get the RIGHT NUMBERS, on a throwaway ledger with known entries.

    python scripts/eval_query_answers.py

The ledger below is built so each answer can be worked out by hand (written in the comments), then every
question runs through the real app path: understand -> execute -> reply. Uses a temporary database file;
the real ledger is never touched.
"""
import asyncio
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "query_answers.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import actions, db  # noqa: E402
from app.nlu import parser  # noqa: E402

DAY = 86400
now = time.time()
start_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
TODAY, YESTERDAY = max(start_today + 1, now - 60), start_today - DAY / 2


def ago(d):
    return now - d * DAY


LEDGER = [  # (customer, kind, amount, when, item)
    ("ਬਿੱਟੂ", "credit", 3000, ago(40), None),
    ("ਬਿੱਟੂ", "credit", 2500, TODAY, "ਆਟਾ"),
    ("ਬਿੱਟੂ", "payment", 500, ago(35), None),          # Bittu owes 5000, last paid 35 days ago
    ("ਪਿੰਕੀ", "credit", 800, YESTERDAY, "ਖੰਡ"),
    ("ਪਿੰਕੀ", "payment", 300, TODAY, None),            # Pinky owes 500, new customer (since yesterday)
    ("ਜਸਵੀਰ", "credit", 7000, ago(60), None),           # Jasvir owes 7000, never paid
    ("ਕੁਲਦੀਪ", "credit", 1200, ago(20), None),
    ("ਕੁਲਦੀਪ", "payment", 1200, ago(5), None),          # Kuldeep clear
    ("ਸਿਮਰਨ", "credit", 150, ago(3), None),             # Simran owes 150, new (3 days)
    ("ਮਾਸਟਰ ਜੀ", "credit", 6000, ago(45), None),
    ("ਮਾਸਟਰ ਜੀ", "payment", 1000, ago(10), None),        # Master ji owes 5000, last paid 10 days ago
    (None, "sale", 400, TODAY, None),
    (None, "sale", 250, YESTERDAY, None),
    (None, "expense", 1000, YESTERDAY, None),
]

CASES = [  # (question, expected total, expected names in the answer list (None = don't check))
    ("ਪੰਜ ਹਜ਼ਾਰ ਤੋਂ ਵੱਧ ਕਿਸ ਕਿਸ ਵੱਲ ਬਾਕੀ ਹੈ?", 7000, ["ਜਸਵੀਰ"]),
    ("Who owes me more than 1000?", 17000, ["ਜਸਵੀਰ", "ਬਿੱਟੂ", "ਮਾਸਟਰ ਜੀ"]),
    ("200 से कम किस किस के पैसे बाकी हैं?", 150, ["ਸਿਮਰਨ"]),
    ("ਮਹੀਨੇ ਤੋਂ ਕਿਸ ਨੇ ਪੈਸੇ ਨਹੀਂ ਦਿੱਤੇ?", 12000, ["ਜਸਵੀਰ", "ਬਿੱਟੂ"]),
    ("Who hasn't paid in a week?", 17000, ["ਜਸਵੀਰ", "ਬਿੱਟੂ", "ਮਾਸਟਰ ਜੀ"]),
    ("ਕੱਲ੍ਹ ਕਿੰਨਾ ਉਧਾਰ ਗਿਆ?", 800, ["ਪਿੰਕੀ"]),
    ("ਅੱਜ ਕਿੰਨਾ ਉਧਾਰ ਦਿੱਤਾ ਗਿਆ?", 2500, ["ਬਿੱਟੂ"]),
    ("How much did we collect in the last 7 days?", 1500, ["ਕੁਲਦੀਪ", "ਪਿੰਕੀ"]),
    ("ਜਸਵੀਰ ਨੇ ਹੁਣ ਤੱਕ ਕੁੱਲ ਕਿੰਨਾ ਉਧਾਰ ਲਿਆ?", 7000, None),
    ("Bittu ne ab tak kitna saman liya?", 5500, None),
    ("ਮਾਸਟਰ ਜੀ ਨੇ ਕਿੰਨੇ ਪੈਸੇ ਦਿੱਤੇ?", 1000, None),
    ("कल कितना खर्चा हुआ?", 1000, None),
    ("ਅੱਜ ਕਿੰਨੀ ਵਿਕਰੀ ਹੋਈ?", 400, None),
    ("What did Bittu take?", 5500, None),
    ("Pinky ne pichhle 10 dino mein kitna udhaar liya?", 800, None),
    ("ਦਸ ਹਜ਼ਾਰ ਤੋਂ ਜ਼ਿਆਦਾ ਉਧਾਰ ਕਿਸ ਦਾ ਹੈ?", 0, []),
]


async def main():
    ids = {}
    for name, kind, amt, ts, item in LEDGER:
        cid = None
        if name:
            if name not in ids:
                ids[name], _ = db.get_or_create_customer(name)
            cid = ids[name]
        db.add_txn(kind, amt, customer_id=cid, item=item, ts=ts)
    ok = 0
    for text, total, names in CASES:
        cmd = await parser.understand(text)
        cmd["transcript"] = text
        r = await actions.execute(cmd)
        got_total = r.get("total", 0) or 0
        got_names = [row["name"]["pa"] for row in r.get("rows", [])]
        good = (r.get("action") == "show_list" and abs(got_total - total) < 0.01
                and (names is None or got_names == names))
        ok += good
        print(f"{'✓' if good else '✗'} {text}\n    {r.get('en')}")
        if not good:
            print(f"    want total {total} names {names} | got {r.get('action')} total {got_total} names {got_names}")
    print(f"\nright answers: {ok}/{len(CASES)}")


if __name__ == "__main__":
    asyncio.run(main())
