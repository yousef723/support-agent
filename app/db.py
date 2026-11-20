"""Storage for businesses, tickets, and every step the agent takes.

Uses PostgreSQL when DATABASE_URL is set (Docker Compose, CI, production).
Falls back to a local SQLite file when it is not, so quick local runs need no database server.
"""
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

TICKET_FIELDS = {
    "status", "subject", "priority", "summary", "handoff_reason",
    "final_reply", "steps_used", "cost_usd", "duration_ms",
}


def using_postgres():
    return bool(os.getenv("DATABASE_URL"))


def _schema():
    """CREATE TABLE statements. Only the id and float column types differ between the two databases."""
    pk = "SERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    real = "DOUBLE PRECISION" if using_postgres() else "REAL"
    return [
        f"""CREATE TABLE IF NOT EXISTS businesses (
            id {pk},
            name TEXT NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )""",
        f"""CREATE TABLE IF NOT EXISTS tickets (
            id {pk},
            business_id INTEGER NOT NULL REFERENCES businesses(id),
            customer_message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            subject TEXT,
            priority TEXT,
            summary TEXT,
            handoff_reason TEXT,
            final_reply TEXT,
            steps_used INTEGER NOT NULL DEFAULT 0,
            cost_usd {real} NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )""",
        f"""CREATE TABLE IF NOT EXISTS steps (
            id {pk},
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            seq INTEGER NOT NULL,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            input TEXT,
            output TEXT,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            cost_usd {real} NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_tickets_business ON tickets (business_id, id)",
        "CREATE INDEX IF NOT EXISTS idx_steps_ticket ON steps (ticket_id, seq)",
    ]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_conn():
    if using_postgres():
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
    else:
        conn = sqlite3.connect(os.getenv("DB_PATH", "support.db"))
        conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _run(conn, sql, params=()):
    """Run one query. SQL is written with ? placeholders; PostgreSQL wants %s."""
    if using_postgres():
        sql = sql.replace("?", "%s")
    return conn.execute(sql, params)


def init_db():
    with get_conn() as conn:
        for statement in _schema():
            _run(conn, statement)


def create_business(name, api_key=None):
    api_key = api_key or "sk_" + secrets.token_urlsafe(24)
    with get_conn() as conn:
        _run(conn, "INSERT INTO businesses (name, api_key, created_at) VALUES (?, ?, ?)",
             (name, api_key, _now()))
    return api_key


def ensure_business(name, api_key):
    """Create the business only if this key does not exist yet."""
    if not get_business_by_key(api_key):
        create_business(name, api_key)


def get_business_by_key(api_key):
    with get_conn() as conn:
        row = _run(conn, "SELECT * FROM businesses WHERE api_key = ?", (api_key,)).fetchone()
    return dict(row) if row else None


def create_ticket_row(business_id, message):
    with get_conn() as conn:
        row = _run(
            conn,
            "INSERT INTO tickets (business_id, customer_message, created_at) VALUES (?, ?, ?) RETURNING id",
            (business_id, message, _now()),
        ).fetchone()
    return row["id"]


def update_ticket(ticket_id, **fields):
    bad = set(fields) - TICKET_FIELDS
    if bad:
        raise ValueError(f"Unknown ticket fields: {bad}")
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        _run(conn, f"UPDATE tickets SET {sets} WHERE id = ?", [*fields.values(), ticket_id])


def get_ticket(ticket_id, business_id=None):
    """If business_id is given, a business can only see its own tickets."""
    sql, params = "SELECT * FROM tickets WHERE id = ?", [ticket_id]
    if business_id is not None:
        sql += " AND business_id = ?"
        params.append(business_id)
    with get_conn() as conn:
        row = _run(conn, sql, params).fetchone()
    return dict(row) if row else None


def list_tickets(business_id, limit=100):
    with get_conn() as conn:
        rows = _run(
            conn,
            "SELECT * FROM tickets WHERE business_id = ? ORDER BY id DESC LIMIT ?",
            (business_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def add_step(ticket_id, seq, kind, name, input_text, output_text, duration_ms, cost_usd=0.0):
    with get_conn() as conn:
        _run(
            conn,
            "INSERT INTO steps (ticket_id, seq, kind, name, input, output, duration_ms, cost_usd, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, seq, kind, name, input_text, output_text, duration_ms, cost_usd, _now()),
        )


def get_steps(ticket_id):
    with get_conn() as conn:
        rows = _run(conn, "SELECT * FROM steps WHERE ticket_id = ? ORDER BY seq", (ticket_id,)).fetchall()
    return [dict(r) for r in rows]
