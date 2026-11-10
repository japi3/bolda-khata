"""Thin async client for Gnani Prisma (STT) and Timbre (TTS).

Docs: https://docs.gnani.ai/api/introduction/introduction
"""
import asyncio
import hashlib
import json
import time

import httpx

from . import config


class GnaniError(RuntimeError):
    pass


# Some accounts allow only one active request at a time (429 RATE_LIMITED),
# so every call goes through one lock and retries with backoff.
_lock: asyncio.Lock | None = None
_client: httpx.AsyncClient | None = None
_loop = None


def _http() -> httpx.AsyncClient:
    """One client + lock per event loop (scripts may call asyncio.run several times)."""
    global _client, _lock, _loop
    loop = asyncio.get_running_loop()
    if _client is None or _loop is not loop:
        _loop, _lock = loop, asyncio.Lock()
        _client = httpx.AsyncClient(
            base_url=config.GNANI_BASE,
            headers={"X-API-Key-ID": config.GNANI_API_KEY},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
    return _client


async def _post(path: str, retries: int = 3, **kw) -> httpx.Response:
    delay = 0.6
    last = None
    for attempt in range(retries + 1):
        client = _http()
        async with _lock:
            try:
                r = await client.post(path, **kw)
            except httpx.HTTPError as e:  # network hiccup
                last = GnaniError(f"network error: {e}")
                r = None
        if r is not None:
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                last = GnaniError(f"{r.status_code}: {r.text[:200]}")
            elif r.status_code >= 400:
                raise GnaniError(f"{r.status_code}: {r.text[:300]}")
            else:
                return r
        await asyncio.sleep(delay)
        delay *= 2
    raise last or GnaniError("request failed")


async def transcribe(
    audio: bytes,
    filename: str = "speech.wav",
    language: str | None = None,
    keyterms: list[str] | None = None,
    topic: str | None = None,
) -> dict:
    """Prisma v3.0 REST transcription (clips up to 30 s).

    `format=transcribe` turns spoken numbers into digits (ITN), which makes
    amount extraction far more reliable. `keyterms` biases recognition toward
    the shop's own customer names and items.
    """
    data = {
        "model": config.STT_MODEL,
        "language_code": language or config.LANG,
        "format": "transcribe",
    }
    if keyterms:
        uniq = list(dict.fromkeys(k for k in keyterms if k and "<|" not in k))[:200]
        data["keyterms"] = json.dumps(uniq, ensure_ascii=False)
    if topic:
        data["topic"] = topic[:1600]
    t0 = time.perf_counter()
    r = await _post("/stt/v3", files={"audio_file": (filename, audio)}, data=data)
    body = r.json()
    if not body.get("success", False):
        raise GnaniError(json.dumps(body.get("error", body), ensure_ascii=False))
    body["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    return body


async def synthesize(text: str, voice: str | None = None, model: str | None = None,
                     language: str | None = None, speed: float = 1.0) -> tuple[str, bytes]:
    """Timbre TTS -> WAV bytes. Results are cached on disk by content hash
    (saves programme credits and makes repeat phrases instant)."""
    voice = voice or config.TTS_VOICE
    model = model or config.TTS_MODEL
    language = language or config.LANG
    key = hashlib.sha1(f"{model}|{voice}|{language}|{speed}|{text}".encode()).hexdigest()[:20]
    path = config.AUDIO_CACHE / f"{key}.wav"
    if path.exists():
        return key, path.read_bytes()
    payload = {
        "text": text,
        "voice": voice,
        "model": model,
        "language": language,
        "speed": speed,
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    r = await _post("/api/v1/tts/inference", json=payload)
    path.write_bytes(r.content)
    return key, r.content
