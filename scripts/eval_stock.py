"""Score stock understanding (eval/stock_test.py PARSE) and run the stock SCENARIO end to end.

    python scripts/eval_stock.py [--errors]

The scenario runs on a temporary database: entries are said one after another through the real app path
(understand -> execute), then the resulting stock is compared with what it must be.
"""
import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "stock_eval.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import actions, db, stock  # noqa: E402
from app.nlu import parser  # noqa: E402
from eval import stock_test  # noqa: E402
from eval.hard_test import CUSTOMERS  # noqa: E402


def _match(got, exp):
    if exp is None:
        return got is None
    if got is None or got.get("type") != exp["type"]:
        return False
    if "item" in exp and got.get("item") != exp["item"]:
        return False
    if "items" in exp:
        g = sorted((k, round(q, 3), u) for k, q, u in got.get("items", []))
        e = sorted((k, round(q, 3), u) for k, q, u in exp["items"])
        return g == e
    return True


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--blind2", action="store_true", help="second blind set and scenario")
    a = ap.parse_args()
    for n in CUSTOMERS:
        db.get_or_create_customer(n)
    ok_s = n_s = ok_n = n_n = 0
    errors = []
    parse = stock_test.PARSE_BLIND2 if a.blind2 else stock_test.PARSE
    scenario = stock_test.SCENARIO2 if a.blind2 else stock_test.SCENARIO
    want = stock_test.SCENARIO2_STOCK if a.blind2 else stock_test.SCENARIO_STOCK
    for text, lang, exp in parse:
        cmd = await parser.understand(text)
        got = cmd.get("stock")
        good = _match(got, exp)
        if exp is None:
            ok_n, n_n = ok_n + good, n_n + 1
        else:
            ok_s, n_s = ok_s + good, n_s + 1
        if not good:
            errors.append((text, exp, got, cmd["intent"]))
    print(f"stock commands/questions understood: {ok_s}/{n_s}")
    print(f"other commands left alone:           {ok_n}/{n_n}")

    # leak check: ledger commands from the hard sets must never become stock commands
    from eval.hard_test import CASES as PA
    from eval.hard_test_en import CASES as EN
    from eval.hard_test_hi import CASES as HI
    leaked = []
    for case in PA + EN + HI:
        cmd = await parser.understand(case[0])
        if cmd.get("stock"):
            leaked.append((case[0], cmd["stock"]))
    print(f"hard-set sentences (all 206) turned into stock commands by mistake: {len(leaked)}")

    # scenario on a fresh ledger
    for t in db.txns(limit=1000):
        db.set_deleted(t["id"], True)
    db.con().execute("UPDATE stock_moves SET deleted=1")
    db.con().commit()
    log = []
    for text in scenario:
        cmd = await parser.understand(text)
        cmd["transcript"] = text
        r = await actions.execute(cmd)
        log.append((text, cmd["intent"], r.get("en")))
    got = {}
    for lv in stock.levels():
        got.setdefault(lv["key"], {})[lv["unit"]] = lv["qty"]
    low = sorted(lv["key"] for lv in stock.levels() if lv["low"])
    ok_low = (not a.blind2) or low == stock_test.SCENARIO2_LOW
    print(f"scenario stock: {'RIGHT' if got == want else 'WRONG'}" + ("" if not a.blind2 else
          f"; running low: {'RIGHT' if ok_low else 'WRONG'} {low}"))
    if a.errors or got != want or not ok_low:
        print(f"   want {want}\n   got  {got}")
        for text, intent, en in log:
            print(f"   - {text}  [{intent}]  -> {en}")
    if a.errors:
        for text, exp, got_, intent in errors:
            print(f"  ✗ {text}\n      want {exp}\n      got  {got_} (intent {intent})")
        for text, q in leaked:
            print(f"  ✗ leaked: {text} -> {q}")


if __name__ == "__main__":
    asyncio.run(main())
