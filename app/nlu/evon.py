"""Gnani Evon (gnani-evon-v3.3, 30B MoE / ~3.5B active) as the deep-understanding layer.

Evon is open-weights on Hugging Face; serve it with vLLM/SGLang (see
deploy/evon_modal.py) and point EVON_BASE_URL at the OpenAI-compatible /v1 URL.

Two jobs:
  extract()  transcript -> strict JSON ledger command (with the shop's customer list as context)
  answer()   free-form Punjabi questions answered from a ledger summary (grounded, short)
"""
import json
import re
import time

import httpx

from .. import config

INTENTS = "CREDIT PAYMENT SALE EXPENSE BALANCE DEBTORS SUMMARY REMIND UNDO RISK OTHER".split()

SYSTEM = """You are the language engine of a voice "bahi khata" (credit ledger) app used by Punjabi
shopkeepers. You receive one speech-to-text transcript (usually Gurmukhi Punjabi, sometimes with
Hindi/English words) and return ONLY a JSON object, no prose.

Intents:
 CREDIT   shop gave goods/money on credit to a customer (ਉਧਾਰ ਦਿੱਤਾ, ਖਾਤੇ ਵਿੱਚ ਲਿਖੋ, X ਸਮਾਨ ਲੈ ਗਿਆ)
 PAYMENT  customer paid back (X ਨੇ ਪੈਸੇ ਦਿੱਤੇ, ਜਮ੍ਹਾ ਕਰਵਾਏ, ਮੋੜੇ, ਗੂਗਲ ਪੇ ਕੀਤੇ). Note "X ਨੂੰ ... ਦਿੱਤਾ" = CREDIT but "X ਨੇ ... ਦਿੱਤੇ" = PAYMENT
 SALE     cash sale, no customer account (ਨਕਦ ਵਿਕਰੀ)
 EXPENSE  shop expense (ਖਰਚਾ, ਬਿੱਲ, ਕਿਰਾਇਆ)
 BALANCE  asks how much one customer owes
 DEBTORS  asks who owes money / total dues
 SUMMARY  asks for sales/cash/expense totals for a period
 REMIND   wants a payment reminder sent to a customer (or everyone if no name)
 UNDO     cancel/delete the last entry
 RISK     asks whether a customer is trustworthy / who is risky
 OTHER    anything else

JSON schema:
{"intent": one of the intents,
 "customer": customer name in Gurmukhi exactly as it should be saved, or null. If the person matches someone in KNOWN CUSTOMERS (even with a spelling/ASR variation), return the known spelling,
 "amount": number in rupees or null (convert Punjabi number words: ਡੇਢ ਸੌ=150, ਢਾਈ ਹਜ਼ਾਰ=2500, ਸਾਢੇ ਤਿੰਨ ਸੌ=350),
 "item": goods or expense head in Gurmukhi, or null,
 "quantity": number or null, "unit": e.g. ਕਿੱਲੋ, or null,
 "day_offset": 0 today, -1 yesterday (ਕੱਲ੍ਹ), -2 (ਪਰਸੋਂ),
 "period": "today" | "week" | "month" | null (for SUMMARY),
 "settle_all": true if the customer cleared their whole balance without an amount (ਪੂਰਾ ਹਿਸਾਬ / ਸਾਰੇ ਪੈਸੇ),
 "confidence": 0..1}"""

EXAMPLES = [
    ("ਰਮੇਸ਼ ਨੂੰ 500 ਰੁਪਏ ਦਾ ਆਟਾ ਉਧਾਰ ਦਿੱਤਾ।",
     {"intent": "CREDIT", "customer": "ਰਮੇਸ਼", "amount": 500, "item": "ਆਟਾ", "quantity": None, "unit": None,
      "day_offset": 0, "period": None, "settle_all": False, "confidence": 0.97}),
    ("ਕੱਲ੍ਹ ਗੁਰਪ੍ਰੀਤ ਨੇ ਡੇਢ ਸੌ ਜਮ੍ਹਾ ਕਰਵਾਏ",
     {"intent": "PAYMENT", "customer": "ਗੁਰਪ੍ਰੀਤ", "amount": 150, "item": None, "quantity": None, "unit": None,
      "day_offset": -1, "period": None, "settle_all": False, "confidence": 0.95}),
    ("ਇਸ ਹਫ਼ਤੇ ਕਿੰਨੀ ਵਿਕਰੀ ਹੋਈ",
     {"intent": "SUMMARY", "customer": None, "amount": None, "item": None, "quantity": None, "unit": None,
      "day_offset": 0, "period": "week", "settle_all": False, "confidence": 0.93}),
]

_client: httpx.AsyncClient | None = None


def enabled() -> bool:
    return bool(config.EVON_BASE_URL)


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=config.EVON_BASE_URL.rstrip("/"),
                                    headers={"Authorization": f"Bearer {config.EVON_API_KEY}"},
                                    timeout=config.EVON_TIMEOUT)
    return _client


async def _chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.0) -> str:
    body = {"model": config.EVON_MODEL, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature,
            # Evon's chat template reasons by default; off for low-latency extraction.
            "chat_template_kwargs": {"enable_thinking": False}}
    r = await _http().post("/chat/completions", json=body)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"] or ""


def _parse_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError(f"no JSON in Evon output: {text[:200]}")
    return json.loads(m.group(0))


async def extract(transcript: str, known_customers: list[str]) -> dict:
    msgs = [{"role": "system", "content": SYSTEM}]
    for t, j in EXAMPLES:
        msgs.append({"role": "user", "content": f"KNOWN CUSTOMERS: ਰਮੇਸ਼, ਗੁਰਪ੍ਰੀਤ\nTRANSCRIPT: {t}"})
        msgs.append({"role": "assistant", "content": json.dumps(j, ensure_ascii=False)})
    names = ", ".join(known_customers[:150]) or "(none yet)"
    msgs.append({"role": "user", "content": f"KNOWN CUSTOMERS: {names}\nTRANSCRIPT: {transcript}"})
    t0 = time.perf_counter()
    out = _parse_json(await _chat(msgs))
    out["_ms"] = round((time.perf_counter() - t0) * 1000)
    if out.get("intent") not in INTENTS:
        out["intent"] = "OTHER"
    return out


async def answer(question: str, context: str, shop: str) -> str:
    msgs = [
        {"role": "system", "content":
            f"ਤੁਸੀਂ '{shop}' ਦੁਕਾਨ ਦੇ ਬਹੀ ਖਾਤਾ ਸਹਾਇਕ ਹੋ। ਹਮੇਸ਼ਾ ਸਿਰਫ਼ ਪੰਜਾਬੀ (ਗੁਰਮੁਖੀ) ਵਿੱਚ, ਵੱਧ ਤੋਂ ਵੱਧ ਦੋ ਛੋਟੇ "
            "ਵਾਕਾਂ ਵਿੱਚ ਜਵਾਬ ਦਿਓ, ਕਿਉਂਕਿ ਜਵਾਬ ਬੋਲ ਕੇ ਸੁਣਾਇਆ ਜਾਵੇਗਾ। ਹਿਸਾਬ ਬਾਰੇ ਸਿਰਫ਼ ਹੇਠਾਂ ਦਿੱਤੇ ਅੰਕੜੇ ਵਰਤੋ; "
            "ਕੋਈ ਅੰਕੜਾ ਆਪਣੇ ਕੋਲੋਂ ਨਾ ਘੜੋ। ਰਕਮਾਂ ₹ ਨਾਲ ਲਿਖੋ।\n\nਦੁਕਾਨ ਦਾ ਹਿਸਾਬ:\n" + context},
        {"role": "user", "content": question},
    ]
    text = await _chat(msgs, max_tokens=160, temperature=0.3)
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
