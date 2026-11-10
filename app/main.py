"""Bahi Khata — voice-first Punjabi credit ledger. FastAPI app."""
import json
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import stock, actions, audio_quality, auth, config, db, gnani
from .ml import risk
from .nlu import evon, parser
from .nlu.datagen import ITEMS
from .nlu.punjabi import find_numbers, normalize, pick_amount
from .nlu.translit import to_roman

WEB = config.ROOT / "web"
app = FastAPI(title="Bahi Khata")


@app.middleware("http")
async def _pin_lock(request, call_next):
    """With APP_PIN set, the API needs the session cookie from /api/login (see app/auth.py)."""
    if auth.needs_auth(request.url.path) and not auth.valid(request.cookies.get(auth.COOKIE)):
        return JSONResponse({"detail": "PIN required"}, status_code=401)
    return await call_next(request)


@app.get("/api/auth")
def auth_status(request: Request):
    return {"pin_required": auth.enabled(), "ok": not auth.enabled() or auth.valid(request.cookies.get(auth.COOKIE))}


@app.post("/api/login")
def login(request: Request, body: dict = Body(...)):
    cid = auth.client_id(request)
    if auth.locked_out(cid):
        raise HTTPException(429, "Too many wrong PINs. Wait 10 minutes.")
    if not auth.check_pin(cid, body.get("pin", "")):
        raise HTTPException(401, "Wrong PIN")
    resp = JSONResponse({"ok": True})
    https = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    resp.set_cookie(auth.COOKIE, auth.make_token(), max_age=auth.MAX_AGE, httponly=True, samesite="lax", secure=https)
    return resp


@app.middleware("http")
async def _no_stale_assets(request, call_next):
    """Browsers must revalidate the app's JS/CSS, so an update is never hidden behind a stale cache."""
    resp = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path == "/":
        resp.headers["Cache-Control"] = "no-cache"
    return resp
app.mount("/static", StaticFiles(directory=WEB), name="static")

KHATA_TERMS = ["ਉਧਾਰ", "ਜਮ੍ਹਾ", "ਖਾਤਾ", "ਖਾਤੇ", "ਬਕਾਇਆ", "ਹਿਸਾਬ", "ਨਕਦ", "ਖਰਚਾ", "ਵਿਕਰੀ", "ਰੁਪਏ",
               "ਗੂਗਲ ਪੇ", "ਪੇਮੈਂਟ", "ਯਾਦ ਕਰਵਾਓ", "ਭਰੋਸਾ"]
STT_TOPIC = "ਪੰਜਾਬੀ ਕਰਿਆਨਾ ਦੁਕਾਨ ਦਾ ਬਹੀ ਖਾਤਾ: ਗਾਹਕਾਂ ਦੇ ਨਾਮ, ਉਧਾਰ, ਜਮ੍ਹਾ, ਰਕਮਾਂ ਅਤੇ ਸਮਾਨ"


@app.on_event("startup")
def _startup():
    db.con()
    parser.nlu()
    risk._load()


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    # served from the root so it can control the whole app
    return FileResponse(WEB / "sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/api/health")
def health():
    return {"gnani_key": bool(config.GNANI_API_KEY), "stt_model": config.STT_MODEL, "tts_model": config.TTS_MODEL,
            "tts_voice": config.TTS_VOICE, "evon": evon.enabled(), "evon_model": config.EVON_MODEL if evon.enabled() else None}


# ------------------------------------------------------------------ voice pipeline
KHATA_TERMS_EN = ["udhaar", "khata", "credit", "payment", "balance", "dues", "cash", "Google Pay", "PhonePe",
                  "UPI", "rupees", "reminder", "atta", "dal"]
STT_TOPIC_EN = "Kirana shop credit ledger (bahi khata): customer names, credit, payments, amounts in rupees, items"


KHATA_TERMS_HI = ["उधार", "जमा", "खाता", "बकाया", "हिसाब", "नकद", "खर्चा", "बिक्री", "रुपये", "गूगल पे", "पेमेंट"]
STT_TOPIC_HI = "किराना दुकान का बही खाता: ग्राहकों के नाम, उधार, जमा, रकम और सामान"


def _gnani_http_error(e: "gnani.GnaniError") -> HTTPException:
    """Structured error the app can explain in the shopkeeper's language (see web/app.js FAIL)."""
    return HTTPException(503 if e.kind in ("down", "busy") else 502,
                         detail={"code": e.kind, "message": f"Gnani speech service: {e}"[:300]})


def _lang(x) -> str:
    x = str(x or "").lower()
    return "en" if x.startswith("en") else "hi" if x.startswith("hi") else "pa"


def _voice(lang: str, reminder: bool = False) -> tuple[str | None, str | None]:
    """(voice, language code) for Timbre; None = Punjabi defaults."""
    if lang == "en":
        return (config.REMINDER_VOICE_EN if reminder else config.TTS_VOICE_EN), "en-IN"
    if lang == "hi":
        return (config.REMINDER_VOICE_HI if reminder else config.TTS_VOICE_HI), "hi-IN"
    return (config.REMINDER_VOICE if reminder else None), None


async def _speak(text: str, voice: str | None = None, lang: str = "pa") -> str | None:
    try:
        v, code = _voice(lang)
        key, _ = await gnani.synthesize(text, voice=voice or v, language=code)
        return f"/api/audio/{key}.wav"
    except gnani.GnaniError:
        return None


PAY_WORDS = {normalize(w) for w in
             "ਜਮ੍ਹਾ ਮਿਲੇ ਮਿਲ ਆਏ ਆ ਭੁਗਤਾਨ ਵਾਪਸ ਮੋੜੇ payment received paid got jama mile जमा मिले मिल आए वापस भुगतान".split()}
CREDIT_WORDS = {normalize(w) for w in "ਉਧਾਰ ਉਧਾਰੀ ਲਿਖੋ ਚੜ੍ਹਾਓ credit udhaar udhar उधार लिखो".split()}
YES_WORDS = {normalize(w) for w in
             "ਹਾਂ ਹਾਂਜੀ ਠੀਕ ਸਹੀ ਬਿਲਕੁਲ ਲਿਖ ਕਰ yes yeah yep ok okay correct right sure haan haanji theek sahi "
             "हां हाँ जी ठीक सही बिल्कुल".split()}
NO_WORDS = {normalize(w) for w in "ਨਹੀਂ ਨਹੀ ਨਾ ਗਲਤ ਰੱਦ no nope wrong cancel nahi galat नहीं ना गलत रद्द".split()}
# paid more than the bill: give the extra back, or keep it on the account
CHANGE_WORDS = {normalize(w) for w in "ਵਾਪਸ ਮੋੜ ਮੋੜੋ ਮੋੜ ਦਿਓ ਚੇਂਜ ਭਾਨ change return back vapas wapas "
                "वापस लौटा लौटाओ चेंज".split()}
ADVANCE_WORDS = {normalize(w) for w in "ਐਡਵਾਂਸ ਰੱਖ ਰੱਖੋ ਰੱਖਣੇ ਜਮ੍ਹਾ advance keep jama rakh rakho "
                 "एडवांस रख रखो रखने जमा".split()}


def _merge_pending(pending: dict, cmd: dict, transcript: str) -> dict:
    """Continue a half-finished command ("ਕਿੰਨੇ ਪੈਸੇ?" -> "ਪੰਜ ਸੌ", "ਜਮ੍ਹਾ ਕਿ ਉਧਾਰ?" -> "ਜਮ੍ਹਾ")."""
    toks = set(normalize(transcript).split())
    if pending.get("awaiting") == "direction" and not pending.get("direction_confirmed"):
        pay, cred = bool(toks & PAY_WORDS), bool(toks & CREDIT_WORDS)
        if pay != cred:   # answering the read-back also confirms what was heard
            return {**pending, "intent": "PAYMENT" if pay else "CREDIT", "direction_confirmed": True,
                    "heard_confirmed": True, "awaiting": None,
                    "transcript": pending.get("transcript", "") + " | " + transcript}
    if pending.get("awaiting") == "change":
        back, keep = bool(toks & CHANGE_WORDS), bool(toks & ADVANCE_WORDS)
        if back != keep:   # the question read back name, bill and money, so this also confirms them
            return {**pending, "extra_choice": "change" if back else "advance", "heard_confirmed": True,
                    "awaiting": None, "transcript": pending.get("transcript", "") + " | " + transcript}
    if pending.get("awaiting") == "heard" and len(toks) <= 4:
        if toks & YES_WORDS and not toks & NO_WORDS:
            return {**pending, "heard_confirmed": True, "awaiting": None,
                    "transcript": pending.get("transcript", "") + " | " + transcript}
        if toks & NO_WORDS:
            return {**cmd, "intent": "OTHER", "cancelled": True}
    if cmd["intent"] in parser.TRANSACTIONAL and cmd["amount"] and cmd["customer"]["status"] in ("match", "new"):
        return cmd  # a complete new command overrides
    merged = dict(pending)
    toks = normalize(transcript).split()
    amt = pick_amount(find_numbers(toks))
    if not merged.get("amount") and amt:
        merged["amount"] = amt
    if merged["customer"]["status"] in ("none", "ambiguous") or not merged["customer"].get("name"):
        spoken = (cmd["customer"].get("name") if cmd["customer"]["status"] != "none" else None) or transcript
        res = parser.resolve_customer(spoken.strip(" ।"), transcript, db.customers())
        if res["status"] != "none":
            merged["customer"] = res
    merged["transcript"] = (pending.get("transcript", "") + " | " + transcript).strip(" |")
    return merged


def _recorded_at(v) -> float | None:
    """Time a queued recording was spoken (seconds or ms since epoch). Accepted only within the last 14 days
    and not in the future, so a wrong phone clock can't put entries far away."""
    try:
        t = float(v)
    except (TypeError, ValueError):
        return None
    if t > 1e12:   # milliseconds
        t /= 1000
    now = time.time()
    return t if now - 14 * 86400 <= t <= now + 60 else None


async def _handle(transcript: str, stt: dict | None, pending: dict | None, speak: bool = True,
                  audio: dict | None = None, lang: str = "pa", recorded_at: float | None = None) -> dict:
    t0 = time.perf_counter()
    # the misheard-audio detector is calibrated on Punjabi recordings only
    cmd = await parser.understand(transcript, audio if lang == "pa" else None)
    cmd["transcript"] = transcript
    if pending:
        cmd = _merge_pending(pending, cmd, transcript)
    if recorded_at:
        cmd["recorded_at"] = recorded_at
    nlu_ms = round((time.perf_counter() - t0) * 1000)
    vid = db.log_voice(transcript=transcript, detected_lang=(stt or {}).get("detected_language_code"),
                       stt_ms=(stt or {}).get("latency_ms"), nlu_engine=cmd["engine"], nlu_ms=nlu_ms,
                       parsed=json.dumps({k: v for k, v in cmd.items() if k != "local"}, ensure_ascii=False,
                                         default=str))
    reply = await actions.execute(cmd, voice_id=vid)
    t1 = time.perf_counter()
    # The UI shows the reply instantly and fetches speech via /api/tts in parallel (speak=False).
    audio = await _speak(reply[lang], lang=lang) if speak else None
    tts_ms = round((time.perf_counter() - t1) * 1000) if speak else None
    db.update_voice(vid, reply=reply["pa"])
    return {
        "transcript": transcript, "transcript_roman": to_roman(transcript),
        "command": {k: cmd[k] for k in ("intent", "confidence", "engine", "customer", "amount", "item",
                                        "quantity", "unit", "day_offset", "period", "settle_all", "local",
                                        "evon_error", "audio_check")} | {"bill": cmd.get("bill"), "query": cmd.get("query")},
        "reply": reply, "audio_url": audio,
        "timings": {"stt_ms": (stt or {}).get("latency_ms"), "nlu_ms": nlu_ms, "tts_ms": tts_ms,
                    "local_nlu_ms": cmd["local"]["ms"] if "local" in cmd else None},
    }


@app.post("/api/voice")
async def voice(audio: UploadFile = File(...), pending: str | None = Form(None), speak: bool = Form(True),
                lang: str = Form("pa"), recorded_at: str | None = Form(None)):
    data = await audio.read()
    if len(data) < 1000:
        raise HTTPException(400, "audio too short")
    lang = _lang(lang)
    names = [c["name"] for c in db.customers()]
    audio_feats = audio_quality.from_wav(data)          # measured on the original recording
    data = audio_quality.pad_wav(data)                  # leading silence so Prisma keeps the first word
    try:
        if lang == "en":   # Prisma en-IN: English + Hinglish, Latin script; names as romanised keyterms
            stt = await gnani.transcribe(data, filename=audio.filename or "speech.wav", language="en-IN",
                                         keyterms=[to_roman(n) for n in names] + KHATA_TERMS_EN, topic=STT_TOPIC_EN)
        elif lang == "hi":  # Prisma hi-IN: Devanagari; names converted to Devanagari as keyterms
            stt = await gnani.transcribe(data, filename=audio.filename or "speech.wav", language="hi-IN",
                                         keyterms=[actions.H(n) for n in names] + KHATA_TERMS_HI, topic=STT_TOPIC_HI)
        else:
            stt = await gnani.transcribe(data, filename=audio.filename or "speech.wav",
                                         keyterms=names + KHATA_TERMS + ITEMS[:40], topic=STT_TOPIC)
    except gnani.GnaniError as e:
        raise _gnani_http_error(e)
    transcript = (stt.get("transcript") or "").strip()
    if not transcript:
        msg = {"pa": "ਕੁਝ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤਾ, ਫਿਰ ਬੋਲੋ ਜੀ।", "en": "I couldn't hear anything, please try again.", "hi": "कुछ सुनाई नहीं दिया, फिर से बोलिए।",
               "action": "empty"}
        return {"transcript": "", "reply": msg, "audio_url": await _speak(msg[lang], lang=lang) if speak else None,
                "timings": {"stt_ms": stt.get("latency_ms")}}
    return await _handle(transcript, stt, json.loads(pending) if pending else None, speak=speak,
                         audio=audio_feats, lang=lang, recorded_at=_recorded_at(recorded_at))


@app.post("/api/text")
async def text(body: dict = Body(...)):
    t = (body.get("text") or "").strip()
    if not t:
        raise HTTPException(400, "empty text")
    return await _handle(t, None, body.get("pending"), speak=body.get("speak", True), lang=_lang(body.get("lang")),
                         recorded_at=_recorded_at(body.get("recorded_at")))


@app.post("/api/resolve")
async def resolve(body: dict = Body(...)):
    """UI picked a customer for an ambiguous/missing name."""
    cmd = body["pending"]
    if body.get("customer_id"):
        c = db.customer(int(body["customer_id"]))
        cmd["customer"] = {"status": "match", "id": c["id"], "name": c["name"], "candidates": []}
    elif body.get("new_name"):
        cmd["customer"] = {"status": "new", "id": None, "name": body["new_name"].strip(), "candidates": []}
    if body.get("intent") in ("CREDIT", "PAYMENT"):
        cmd["intent"], cmd["direction_confirmed"], cmd["heard_confirmed"] = body["intent"], True, True
    if body.get("confirm"):
        cmd["heard_confirmed"] = True
    if body.get("amount"):
        cmd["amount"], cmd["amount_options"], cmd["heard_confirmed"] = float(body["amount"]), [], True
    if body.get("extra") in ("change", "advance"):
        cmd["extra_choice"], cmd["heard_confirmed"] = body["extra"], True
    reply = await actions.execute(cmd)
    lang = _lang(body.get("lang"))
    return {"reply": reply, "audio_url": await _speak(reply[lang], lang=lang) if body.get("speak", True) else None}


# ------------------------------------------------------------------ state & ledger
def _cust_view(c: dict, with_score=True) -> dict:
    out = {**c, "name_roman": to_roman(c["name"]), "name_hi": actions.H(c["name"])}
    if with_score:
        s = risk.score_customer(c["id"])
        out["score"] = {k: s.get(k) for k in ("trust", "band", "low_data", "risk")}
    return out


@app.get("/api/state")
def state():
    s, e = db.period_bounds("today")
    custs = db.customers()
    owed = [c for c in custs if c["balance"] > 0]
    recent = db.txns(limit=12)
    for t in recent:
        t["customer_roman"] = to_roman(t["customer"]) if t["customer"] else None
        t["item_roman"] = to_roman(t["item"]) if t["item"] else None
        t["customer_hi"] = actions.H(t["customer"]) if t["customer"] else None
        t["item_hi"] = actions.H(t["item"]) if t["item"] else None
    return {"settings": db.get_settings(), "today": db.summary(s, e),
            "total_outstanding": round(sum(c["balance"] for c in owed), 2), "n_owing": len(owed),
            "recent": recent, "customers": [_cust_view(c) for c in custs], "health": health()}


@app.get("/api/customers/{cid}")
def customer_detail(cid: int):
    c = db.customer(cid)
    if not c:
        raise HTTPException(404)
    ts = db.txns(cid, limit=500)
    running, out = c["balance"], []
    for t in ts:  # newest first -> running balance after each txn
        out.append({**t, "balance_after": round(running, 2), "item_roman": to_roman(t["item"]) if t["item"] else None,
                    "item_hi": actions.H(t["item"]) if t["item"] else None})
        running -= t["amount"] if t["kind"] == "credit" else -t["amount"] if t["kind"] == "payment" else 0
    return {"customer": _cust_view(c, with_score=False), "txns": out, "score": risk.score_customer(cid)}


@app.patch("/api/customers/{cid}")
def patch_customer(cid: int, body: dict = Body(...)):
    db.update_customer(cid, body.get("name"), body.get("phone"))
    return customer_detail(cid)


@app.post("/api/txns")
def add_txn(body: dict = Body(...)):
    kind = body["kind"]
    cid = body.get("customer_id")
    if kind in ("credit", "payment") and not cid:
        if not body.get("customer_name"):
            raise HTTPException(400, "customer required")
        cid, _ = db.get_or_create_customer(body["customer_name"])
    tid = db.add_txn(kind, float(body["amount"]), customer_id=cid, item=body.get("item"),
                     note=body.get("note"), source="manual")
    return db.txn(tid)


@app.delete("/api/txns/{tid}")
def delete_txn(tid: int):
    db.set_deleted(tid, True)
    return {"ok": True}


@app.post("/api/txns/{tid}/restore")
def restore_txn(tid: int):
    db.set_deleted(tid, False)
    return {"ok": True}


@app.get("/api/stock")
def stock_levels():
    """Every tracked item with its quantity now, in pa / en / hi, low items first."""
    from .ledger_queries import _stock_row
    return {"items": [_stock_row(lv) for lv in stock.levels()]}


@app.post("/api/stock/undo/{move_id}")
def stock_undo(move_id: int, body: dict = Body(default={})):
    stock.undo_set(move_id, not body.get("restore"))
    return {"ok": True}


@app.get("/api/insights")
def insights():
    p = risk.portfolio()
    p["customers"] = [{**{k: r[k] for k in ("id", "name", "balance", "phone")}, "name_roman": to_roman(r["name"]), "name_hi": actions.H(r["name"]),
                       "score": {k: r["score"].get(k) for k in ("trust", "band", "reasons", "strengths",
                                                                 "low_data", "suggested_limit",
                                                                 "oldest_unpaid_days")}}
                      for r in p["customers"]]
    reports = {}
    for name in ("risk_report", "nlu_report", "e2e_report", "nlu_comparison", "repeat_report", "real_report"):
        f = config.MODEL_DIR / f"{name}.json"
        if f.exists():
            reports[name] = json.loads(f.read_text())
    return {**p, "daily": db.daily_series(30), "models": reports}


@app.post("/api/reminders/{cid}")
async def reminder(cid: int, lang: str = "pa"):
    lang = _lang(lang)
    rem = actions.build_reminder(cid)
    if not rem:
        raise HTTPException(400, "nothing due")
    rem["audio_url"] = await _speak(rem[lang], lang=lang, voice=_voice(lang, reminder=True)[0])
    phone = "".join(ch for ch in (rem.get("phone") or "") if ch.isdigit())
    if len(phone) == 10:
        phone = "91" + phone
    rem["whatsapp_url"] = f"https://wa.me/{phone}?text={quote(rem[lang])}" if phone else \
        f"https://wa.me/?text={quote(rem[lang])}"
    return rem


@app.post("/api/tts")
async def tts(body: dict = Body(...)):
    lang = _lang(body.get("lang"))
    v, code = _voice(lang)
    try:   # called directly (not via _speak) so the app learns *why* a spoken reply failed
        key, _ = await gnani.synthesize(body["text"], voice=body.get("voice") or v, language=code)
    except gnani.GnaniError as e:
        raise _gnani_http_error(e)
    return {"audio_url": f"/api/audio/{key}.wav"}


@app.get("/api/audio/{key}.wav")
def audio(key: str):
    if not key.isalnum():
        raise HTTPException(400)
    f = config.AUDIO_CACHE / f"{key}.wav"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="audio/wav")


# ------------------------------------------------------------------ real-voice testing
@app.get("/api/collect/prompts")
def collect_prompts(lang: str = "pa"):
    from . import collect
    return {"lang": _lang(lang), "prompts": collect.prompts(_lang(lang)), "stats": collect.stats()}


@app.post("/api/collect")
async def collect_record(audio: UploadFile = File(...), lang: str = Form("pa"), case: int = Form(...),
                         mode: str = Form("free"), env: str = Form("quiet"), speaker: str = Form("")):
    from . import collect
    data = await audio.read()
    if len(data) < 1000:
        raise HTTPException(400, "audio too short")
    lang = _lang(lang)
    if not 0 <= case < len(collect.prompts(lang)):
        raise HTTPException(400, "bad case")
    try:
        row = await collect.record(data, lang, case, mode if mode in ("read", "free") else "free",
                                   env if env in ("quiet", "busy", "loud") else "quiet", speaker.strip())
    except gnani.GnaniError as e:
        raise _gnani_http_error(e)
    return {**row, "stats": collect.stats()}


@app.delete("/api/collect/{rid}")
def collect_delete(rid: str):
    from . import collect
    if not rid.isalnum() or not collect.delete(rid):
        raise HTTPException(404)
    return {"ok": True, "stats": collect.stats()}


@app.get("/api/settings")
def get_settings():
    return db.get_settings()


@app.put("/api/settings")
def put_settings(body: dict = Body(...)):
    db.set_settings(body)
    return db.get_settings()
