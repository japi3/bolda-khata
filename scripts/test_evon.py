"""Smoke-test Evon: raw chat call, then JSON extraction + grounded answer on Punjabi commands."""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.nlu import evon  # noqa: E402

CASES = [
    "ਰਮੇਸ਼ ਨੂੰ 500 ਰੁਪਏ ਦਾ ਆਟਾ ਉਧਾਰ ਦਿੱਤਾ।",
    "ਗੁਰਪ੍ਰੀਤ ਨੇ ਡੇਢ ਸੌ ਜਮ੍ਹਾ ਕਰਵਾਏ",
    "ਦੁਕਾਨ ਦਾ ਕਿਰਾਇਆ 8000 ਦੇ ਦਿੱਤਾ।",
    "ਬਿੱਟੂ ਤੇ ਭਰੋਸਾ ਕਰਾਂ?",
    "ਕੱਲ੍ਹ ਕਿੰਨਾ ਖਰਚਾ ਹੋਇਆ ਸੀ?",
]


async def main():
    if not evon.enabled():
        sys.exit("EVON_BASE_URL not set")
    print("endpoint:", config.EVON_BASE_URL)
    t = time.perf_counter()
    print("raw:", (await evon._chat([{"role": "user", "content": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਇੱਕ ਵਾਕ ਵਿੱਚ ਜਵਾਬ ਦਿਓ।"}],
                                     max_tokens=60))[:200], f"({time.perf_counter() - t:.1f}s)")
    known = ["ਰਮੇਸ਼ ਕੁਮਾਰ", "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ", "ਬਿੱਟੂ", "ਹਰਪ੍ਰੀਤ ਕੌਰ"]
    for c in CASES:
        r = await evon.extract(c, known)
        print(f"{r['_ms']:>5} ms  {c}  ->  {r.get('intent')} cust={r.get('customer')} amt={r.get('amount')} "
              f"item={r.get('item')} day={r.get('day_offset')}")
    print("answer:", await evon.answer("ਸਭ ਤੋਂ ਵੱਧ ਉਧਾਰ ਕਿਸ ਦਾ ਹੈ?",
                                       "ਕੁੱਲ ਬਕਾਇਆ ₹45,910\n- ਕੁਲਦੀਪ: ਬਕਾਇਆ ₹17,510\n- ਬਿੱਟੂ: ਬਕਾਇਆ ₹14,360",
                                       "ਸ਼ਰਮਾ ਕਰਿਆਨਾ ਸਟੋਰ"))


if __name__ == "__main__":
    asyncio.run(main())
