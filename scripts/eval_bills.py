"""Score the multi-part bill parser on the held-out set (eval/bill_test.py).

    python scripts/eval_bills.py [--errors]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.nlu.bill import parse_bill  # noqa: E402
from app.nlu.parser import nlu  # noqa: E402
from app.nlu.punjabi import surface_tokens  # noqa: E402
from eval.bill_test import CASES, CASES_BLIND2  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--blind2", action="store_true", help="score the second blind set instead")
    a = ap.parse_args()
    cases = CASES_BLIND2 if a.blind2 else CASES
    m = nlu()
    ok_detect = ok_total = ok_paid = n_bills = 0
    errors = []
    for text, lang, total, paid, cust in cases:
        r = m.analyse(text)
        b = parse_bill(r["tokens"], r["tags"], surface_tokens(text))
        detected = b is not None
        should = total is not None
        good_detect = detected == should
        ok_detect += good_detect
        if should:
            n_bills += 1
            gt = bool(b) and abs(b["total"] - total) < 0.01
            gp = bool(b) and (b["paid"] == paid)
            ok_total += gt
            ok_paid += gp
            if not (gt and gp):
                errors.append((text, total, paid, b))
        elif not good_detect:
            errors.append((text, None, None, b))
    n = len(cases)
    print(f"bill detected correctly (bill vs not a bill): {ok_detect}/{n}")
    print(f"bill total right:  {ok_total}/{n_bills}")
    print(f"paid-now right:    {ok_paid}/{n_bills}")
    if a.errors:
        for text, total, paid, b in errors:
            got = f"total {b['total']} paid {b['paid']} lines {[(l['item'], l['amount']) for l in b['lines']]}" if b else "not a bill"
            print(f"  ✗ {text}\n      want {'total ' + str(total) + ' paid ' + str(paid) if total else 'not a bill'} | got {got}")


if __name__ == "__main__":
    main()
