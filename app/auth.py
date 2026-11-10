"""PIN lock for when the app is reachable from the internet (phone link).

If APP_PIN is set in .env, every /api/ call needs a session cookie, which you get by entering the
PIN. The cookie is HMAC-signed with SESSION_SECRET and lasts 30 days. Wrong PINs are rate-limited per
client (5 tries per 10 minutes), so a 6-digit PIN can't be brute-forced through a public link.
"""
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque

from . import config

COOKIE = "bk_session"
MAX_AGE = 30 * 86400
MAX_FAILS, WINDOW = 5, 600
OPEN_PATHS = {"/api/login", "/api/auth"}

_fails: dict[str, deque] = defaultdict(deque)


def _env_value(key: str) -> str:
    return (os.getenv(key) or "").strip()


def pin() -> str:
    return _env_value("APP_PIN")


def enabled() -> bool:
    return bool(pin())


def _secret() -> bytes:
    s = _env_value("SESSION_SECRET")
    if not s:   # create once and keep it in .env so sessions survive restarts
        s = secrets.token_urlsafe(32)
        with (config.ROOT / ".env").open("a") as f:
            f.write(f"SESSION_SECRET={s}\n")
        os.environ["SESSION_SECRET"] = s
    return s.encode()


def make_token() -> str:
    exp = str(int(time.time()) + MAX_AGE)
    sig = hmac.new(_secret(), exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.split(".", 1)
    good = hmac.new(_secret(), exp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good) and exp.isdigit() and int(exp) > time.time()


def client_id(request) -> str:
    # behind the Cloudflare tunnel every request comes from localhost; the real client is in this header
    return (request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0]
            or (request.client.host if request.client else "?")).strip()


def locked_out(cid: str) -> bool:
    q = _fails[cid]
    while q and q[0] < time.time() - WINDOW:
        q.popleft()
    return len(q) >= MAX_FAILS


def check_pin(cid: str, attempt: str) -> bool:
    if locked_out(cid):
        return False
    ok = hmac.compare_digest(str(attempt or "").strip(), pin())
    if not ok:
        _fails[cid].append(time.time())
    return ok


def needs_auth(path: str) -> bool:
    return enabled() and path.startswith("/api/") and path not in OPEN_PATHS
