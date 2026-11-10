"""SQLite ledger. Amounts are stored in paise (integers) to avoid float errors.

Sign convention for a customer's balance ("ਬਕਾਇਆ", money they owe the shop):
    credit  (ਉਧਾਰ ਦਿੱਤਾ)   -> +amount
    payment (ਪੈਸੇ ਮਿਲੇ)    -> -amount
Shop-level entries (sale, expense) have no customer.
"""
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    created_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_customer_name ON customers(name);
CREATE TABLE IF NOT EXISTS txns (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    kind TEXT NOT NULL CHECK (kind IN ('credit','payment','sale','expense')),
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    item TEXT,
    quantity REAL,
    unit TEXT,
    note TEXT,
    ts REAL NOT NULL,            -- when it happened (can be back-dated: "ਕੱਲ੍ਹ")
    created_at REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'voice',
    voice_id INTEGER,
    deleted INTEGER NOT NULL DEFAULT 0,
    group_id TEXT                -- entries written together (a bill's credit + payment) share this
);
CREATE INDEX IF NOT EXISTS ix_txn_customer ON txns(customer_id, ts);
CREATE TABLE IF NOT EXISTS voice_log (
    id INTEGER PRIMARY KEY,
    transcript TEXT,
    detected_lang TEXT,
    stt_ms INTEGER,
    nlu_engine TEXT,
    nlu_ms INTEGER,
    parsed TEXT,
    reply TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
-- stock moves: +qty in (restocking), -qty out (sold / taken on credit), or a counted stock (kind 'set', stored
-- as the difference). A move tied to a ledger entry disappears with that entry's undo.
CREATE TABLE IF NOT EXISTS stock_moves (
    id INTEGER PRIMARY KEY,
    item_key TEXT NOT NULL,
    unit TEXT NOT NULL,
    qty REAL NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('in','out','set')),
    txn_id INTEGER REFERENCES txns(id),
    created_at REAL NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_stock_item ON stock_moves(item_key, unit);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    return con


_con: sqlite3.Connection | None = None


def con() -> sqlite3.Connection:
    global _con
    if _con is None:
        _con = connect()
        _con.executescript(SCHEMA)
        cols = {r["name"] for r in _con.execute("PRAGMA table_info(txns)")}
        if "group_id" not in cols:   # databases created before bills existed
            _con.execute("ALTER TABLE txns ADD COLUMN group_id TEXT")
            _con.commit()
    return _con


@contextmanager
def tx():
    c = con()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise


# ------------------------------------------------------------------ settings
DEFAULT_SETTINGS = {"shop_name": "ਸ਼ਰਮਾ ਕਰਿਆਨਾ ਸਟੋਰ", "shop_name_en": "", "shop_name_hi": "", "owner_name": "",
                    "shop_phone": ""}


def get_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    for r in con().execute("SELECT key, value FROM settings"):
        s[r["key"]] = r["value"]
    return s


def set_settings(values: dict):
    with tx() as c:
        for k, v in values.items():
            if k in DEFAULT_SETTINGS:
                c.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                          "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))


# ------------------------------------------------------------------ customers
def customers() -> list[dict]:
    rows = con().execute("""
        SELECT c.id, c.name, c.phone, c.created_at,
          COALESCE(SUM(CASE WHEN t.kind='credit' THEN t.amount_paise
                            WHEN t.kind='payment' THEN -t.amount_paise END),0) AS bal,
          MAX(t.ts) AS last_ts, COUNT(t.id) AS n
        FROM customers c LEFT JOIN txns t ON t.customer_id=c.id AND t.deleted=0
        GROUP BY c.id ORDER BY bal DESC, c.name""").fetchall()
    return [{"id": r["id"], "name": r["name"], "phone": r["phone"], "balance": r["bal"] / 100,
             "last_ts": r["last_ts"], "n_txns": r["n"], "created_at": r["created_at"]} for r in rows]


def customer(cid: int) -> dict | None:
    for c in customers():
        if c["id"] == cid:
            return c
    return None


def get_or_create_customer(name: str) -> tuple[int, bool]:
    name = name.strip()
    r = con().execute("SELECT id FROM customers WHERE name=?", (name,)).fetchone()
    if r:
        return r["id"], False
    with tx() as c:
        cur = c.execute("INSERT INTO customers(name, created_at) VALUES(?,?)", (name, time.time()))
        return cur.lastrowid, True


def update_customer(cid: int, name: str | None = None, phone: str | None = None):
    with tx() as c:
        if name:
            c.execute("UPDATE customers SET name=? WHERE id=?", (name.strip(), cid))
        if phone is not None:
            c.execute("UPDATE customers SET phone=? WHERE id=?", (phone.strip() or None, cid))


def balance(cid: int) -> float:
    r = con().execute("""SELECT COALESCE(SUM(CASE WHEN kind='credit' THEN amount_paise
                          WHEN kind='payment' THEN -amount_paise END),0) b
                          FROM txns WHERE customer_id=? AND deleted=0""", (cid,)).fetchone()
    return r["b"] / 100


# ------------------------------------------------------------------ transactions
def add_txn(kind: str, amount: float, customer_id: int | None = None, item: str | None = None,
            quantity: float | None = None, unit: str | None = None, note: str | None = None,
            day_offset: int = 0, source: str = "voice", voice_id: int | None = None,
            ts: float | None = None, group_id: str | None = None) -> int:
    now = time.time()
    if ts is None:
        ts = now + day_offset * 86400
    with tx() as c:
        cur = c.execute(
            "INSERT INTO txns(customer_id,kind,amount_paise,item,quantity,unit,note,ts,created_at,source,voice_id,group_id)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (customer_id, kind, int(round(amount * 100)), item, quantity, unit, note, ts, now, source, voice_id,
             group_id))
        return cur.lastrowid


def _txn_row(r) -> dict:
    return {"id": r["id"], "customer_id": r["customer_id"], "customer": r["cname"], "kind": r["kind"],
            "amount": r["amount_paise"] / 100, "item": r["item"], "quantity": r["quantity"],
            "unit": r["unit"], "note": r["note"], "ts": r["ts"], "source": r["source"],
            "deleted": bool(r["deleted"]), "group_id": r["group_id"], "created_at": r["created_at"]}


def txns(customer_id: int | None = None, limit: int = 50, include_deleted=False) -> list[dict]:
    q = ("SELECT t.*, c.name cname FROM txns t LEFT JOIN customers c ON c.id=t.customer_id WHERE 1=1")
    args: list = []
    if customer_id is not None:
        q += " AND t.customer_id=?"; args.append(customer_id)
    if not include_deleted:
        q += " AND t.deleted=0"
    q += " ORDER BY t.ts DESC, t.id DESC LIMIT ?"; args.append(limit)
    return [_txn_row(r) for r in con().execute(q, args)]


def txn(tid: int) -> dict | None:
    r = con().execute("SELECT t.*, c.name cname FROM txns t LEFT JOIN customers c ON c.id=t.customer_id "
                      "WHERE t.id=?", (tid,)).fetchone()
    return _txn_row(r) if r else None


def last_txn() -> dict | None:
    r = con().execute("SELECT t.*, c.name cname FROM txns t LEFT JOIN customers c ON c.id=t.customer_id "
                      "WHERE t.deleted=0 ORDER BY t.created_at DESC, t.id DESC LIMIT 1").fetchone()
    return _txn_row(r) if r else None


def set_deleted(tid: int, deleted: bool = True):
    """Deleting (or restoring) one entry of a bill affects the whole bill (its credit + payment)."""
    with tx() as c:
        r = c.execute("SELECT group_id FROM txns WHERE id=?", (tid,)).fetchone()
        if r and r["group_id"]:
            c.execute("UPDATE txns SET deleted=? WHERE group_id=?", (1 if deleted else 0, r["group_id"]))
        else:
            c.execute("UPDATE txns SET deleted=? WHERE id=?", (1 if deleted else 0, tid))


def group_txns(group_id: str) -> list[dict]:
    return [_txn_row(r) for r in con().execute(
        "SELECT t.*, c.name cname FROM txns t LEFT JOIN customers c ON c.id=t.customer_id WHERE t.group_id=? "
        "ORDER BY t.id", (group_id,))]


def customer_events(cid: int) -> list[tuple[float, str, float]]:
    """(ts, kind, amount) oldest first — input to the risk features."""
    return [(r["ts"], r["kind"], r["amount_paise"] / 100) for r in con().execute(
        "SELECT ts, kind, amount_paise FROM txns WHERE customer_id=? AND deleted=0 "
        "AND kind IN ('credit','payment') ORDER BY ts, id", (cid,))]


def period_bounds(period: str, day_offset: int = 0) -> tuple[float, float]:
    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = start_today - timedelta(days=start_today.weekday())
        return start.timestamp(), now.timestamp() + 1
    if period == "month":
        start = start_today.replace(day=1)
        return start.timestamp(), now.timestamp() + 1
    day = start_today + timedelta(days=day_offset)
    return day.timestamp(), (day + timedelta(days=1)).timestamp()


def window_bounds(window: str, n: int | None = None) -> tuple[float, float]:
    """Time range for a smart question: today / yesterday / day_before / this_week / last_week /
    this_month / last_month / days (last n days, today included) / all."""
    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if window in ("today", "yesterday", "day_before"):
        return period_bounds("today", {"today": 0, "yesterday": -1, "day_before": -2}[window])
    if window == "this_week":
        return period_bounds("week")
    if window == "this_month":
        return period_bounds("month")
    if window == "last_week":
        this_week = start_today - timedelta(days=start_today.weekday())
        return (this_week - timedelta(days=7)).timestamp(), this_week.timestamp()
    if window == "last_month":
        this_month = start_today.replace(day=1)
        prev = (this_month - timedelta(days=1)).replace(day=1)
        return prev.timestamp(), this_month.timestamp()
    if window == "days":
        return (start_today - timedelta(days=max(1, n or 1) - 1)).timestamp(), now.timestamp() + 1
    return 0.0, now.timestamp() + 1


def txns_between(start: float, end: float, kind: str | None = None, customer_id: int | None = None) -> list[dict]:
    q = ("SELECT t.*, c.name cname FROM txns t LEFT JOIN customers c ON c.id=t.customer_id "
         "WHERE t.deleted=0 AND t.ts>=? AND t.ts<?")
    args: list = [start, end]
    if kind:
        q += " AND t.kind=?"
        args.append(kind)
    if customer_id:
        q += " AND t.customer_id=?"
        args.append(customer_id)
    return [_txn_row(r) for r in con().execute(q + " ORDER BY t.ts DESC, t.id DESC", args)]


def customer_activity() -> dict[int, dict]:
    """customer_id -> {first_ts, last_payment_ts} (for "who hasn't paid in a month?")."""
    out = {}
    for r in con().execute("SELECT customer_id, MIN(ts) first_ts, MAX(CASE WHEN kind='payment' THEN ts END) last_pay "
                           "FROM txns WHERE deleted=0 AND customer_id IS NOT NULL GROUP BY customer_id"):
        out[r["customer_id"]] = {"first_ts": r["first_ts"], "last_payment_ts": r["last_pay"]}
    return out


def summary(start: float, end: float) -> dict:
    out = {"credit": 0.0, "payment": 0.0, "sale": 0.0, "expense": 0.0}
    for r in con().execute("SELECT kind, SUM(amount_paise) s, COUNT(*) n FROM txns WHERE deleted=0 "
                           "AND ts>=? AND ts<? GROUP BY kind", (start, end)):
        out[r["kind"]] = r["s"] / 100
    out["cash_in"] = out["sale"] + out["payment"]
    out["net_cash"] = out["cash_in"] - out["expense"]
    return out


def daily_series(days: int = 30) -> list[dict]:
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for d in range(days - 1, -1, -1):
        day = now - timedelta(days=d)
        s = summary(day.timestamp(), (day + timedelta(days=1)).timestamp())
        s["date"] = day.strftime("%Y-%m-%d")
        out.append(s)
    return out


def log_voice(**kw) -> int:
    with tx() as c:
        cur = c.execute("INSERT INTO voice_log(transcript,detected_lang,stt_ms,nlu_engine,nlu_ms,parsed,reply,created_at)"
                        " VALUES(?,?,?,?,?,?,?,?)",
                        (kw.get("transcript"), kw.get("detected_lang"), kw.get("stt_ms"), kw.get("nlu_engine"),
                         kw.get("nlu_ms"), kw.get("parsed"), kw.get("reply"), time.time()))
        return cur.lastrowid


def update_voice(vid: int, **kw):
    sets = ", ".join(f"{k}=?" for k in kw)
    with tx() as c:
        c.execute(f"UPDATE voice_log SET {sets} WHERE id=?", (*kw.values(), vid))
