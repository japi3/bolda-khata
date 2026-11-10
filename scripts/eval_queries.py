"""Score smart-question understanding on the held-out set (eval/query_test.py).

    python scripts/eval_queries.py [--errors] [--set blind2]

A case is right when every expected key matches the query spec the app builds (and a non-question gets no
query at all, so ordinary commands behave exactly as before). Also checks that none of the hard-set
ledger commands (pa/en/hi) picks up a query by mistake.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.nlu import parser  # noqa: E402
from eval import query_test  # noqa: E402
from eval.hard_test import CUSTOMERS  # noqa: E402

CUSTS = [{"id": i + 1, "name": n} for i, n in enumerate(CUSTOMERS)]


async def spec(text):
    cmd = await parser.understand(text, None, CUSTS)
    q = cmd.get("query")
    if q and q.get("customer_id"):
        q = {**q, "customer": next(c["name"] for c in CUSTS if c["id"] == q["customer_id"])}
    return cmd, q


def matches(q, exp):
    if exp is None:
        return q is None
    if q is None:
        return False
    return all(q.get(k) == v for k, v in exp.items())


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--set", default="CASES")
    a = ap.parse_args()
    cases = getattr(query_test, a.set)
    by_lang, errors = {}, []
    ok_q = n_q = ok_n = n_n = 0
    for text, lang, exp in cases:
        _, q = await spec(text)
        good = matches(q, exp)
        t = by_lang.setdefault(lang, [0, 0])
        t[0] += good
        t[1] += 1
        if exp is None:
            ok_n += good
            n_n += 1
        else:
            ok_q += good
            n_q += 1
        if not good:
            errors.append((text, exp, q))
    print(f"smart questions understood exactly: {ok_q}/{n_q}")
    print(f"ordinary commands left alone:       {ok_n}/{n_n}")
    print("by language: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in by_lang.items()))

    # no ledger command from the hard sets may turn into a question
    from eval.hard_test import CASES as PA
    from eval.hard_test_en import CASES as EN
    from eval.hard_test_hi import CASES as HI
    leaked = []
    for case in PA + EN + HI:
        text, intent = case[0], case[1]
        if intent in parser.TRANSACTIONAL:
            _, q = await spec(text)
            if q:
                leaked.append((text, q))
    print(f"hard-set ledger commands turned into questions by mistake: {len(leaked)}")
    if a.errors:
        for text, exp, q in errors:
            print(f"  ✗ {text}\n      want {exp}\n      got  {q}")
        for text, q in leaked:
            print(f"  ✗ leaked: {text} -> {q}")


if __name__ == "__main__":
    asyncio.run(main())
