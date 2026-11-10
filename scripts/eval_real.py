"""Report on real-voice recordings (Settings → Voice testing, or imported ones).

Re-scores every recording with the CURRENT app (same understanding + the same "ask before acting"
questions), using the stored Prisma transcripts, so no API calls. Each recording ends up as:
  correct       the app acted right without asking
  asked         the app asked back first (safe; split into "needed" and "unneeded")
  wrong_silent  the app would have acted wrongly without asking: the dangerous case

    python scripts/eval_real.py            # summary
    python scripts/eval_real.py --errors   # every recording that wasn't handled perfectly
Writes models/real_report.json (shown on the Insights screen).
"""
import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import collect, config  # noqa: E402


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    a = ap.parse_args()
    rows = collect.rows()
    if not rows:
        print("No recordings yet. Open the app → Settings → Voice testing.")
        return
    groups = defaultdict(lambda: defaultdict(int))
    details = []
    for r in rows:
        e = r["expected"]
        if r["transcript"]:
            res = await collect.score(r["transcript"], e["intent"], e["amount"], e["customer"], r["lang"], r.get("audio"))
        else:
            res = {"outcome": "asked", "correct": False, "asked": "empty"}
        kind = res["outcome"]
        if kind == "asked":
            kind = "asked_needed" if not res["correct"] else "asked_unneeded"
        for key in ("all", f"lang={r['lang']}", f"env={r['env']}", f"mode={r['mode']}", f"speaker={r['speaker'] or '-'}"):
            groups[key]["n"] += 1
            groups[key][kind] += 1
            groups[key]["understood"] += bool(res["correct"])
        if kind != "correct":
            details.append((kind, r, res))
    print(f"{len(rows)} real recordings")
    print(f"  {'group':22s} {'understood':>10s} {'acted right':>12s} {'asked back':>11s} {'WRONG, silent':>14s}")
    for k in sorted(groups, key=lambda k: (k != "all", k)):
        g = groups[k]
        n = g["n"]
        asked = g["asked_needed"] + g["asked_unneeded"]
        print(f"  {k:22s} {g['understood']:>4d}/{n:<5d} {g['correct']:>6d}/{n:<5d} {asked:>5d}/{n:<5d} {g['wrong_silent']:>8d}/{n:<5d}")
    if a.errors:
        for kind in ("wrong_silent", "asked_needed", "asked_unneeded"):
            items = [d for d in details if d[0] == kind]
            if not items:
                continue
            title = {"wrong_silent": "WRONG and acted on without asking",
                     "asked_needed": "Misheard, but the app asked back (safe)",
                     "asked_unneeded": "Understood, but asked anyway (extra tap)"}[kind]
            print(f"\n{title}:")
            for _, r, res in items:
                e = r["expected"]
                print(f"  [{r['lang']}/{r['env']}] heard: {r['transcript']}\n"
                      f"      want {e['intent']} {e['amount']} {e['customer']} | got {res.get('intent')} "
                      f"{res.get('amount')} {res.get('customer')}{'  → asks: ' + str(res.get('asked')) if res.get('asked') else ''}")
    report = {"n": len(rows), "groups": {k: dict(v) for k, v in groups.items()}}
    # keep the shape the Insights screen expects
    report["groups"]["all"]["correct_understood"] = groups["all"]["understood"]
    (config.MODEL_DIR / "real_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
