import sqlite3
import json
import os

DB_PATH = os.environ.get("DB_PATH", "landgold.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                email       TEXT NOT NULL,
                phone       TEXT,
                language    TEXT DEFAULT 'en',
                budget_usd  REAL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS land_data (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id              INTEGER REFERENCES leads(id) ON DELETE CASCADE,
                land_type            TEXT NOT NULL,
                area_m2              REAL NOT NULL,
                location             TEXT,
                road_type            TEXT DEFAULT 'provincial_road',
                highway_proximity_m  REAL DEFAULT 100,
                title_constraints    TEXT DEFAULT '[]',
                gov_signal           TEXT DEFAULT 'none',
                created_at           TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS gov_signals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_type     TEXT NOT NULL,
                region          TEXT,
                description     TEXT,
                confidence_pct  INTEGER DEFAULT 50,
                active          INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id     INTEGER REFERENCES leads(id) ON DELETE CASCADE,
                agent       TEXT NOT NULL,
                lang        TEXT NOT NULL,
                message     TEXT NOT NULL,
                status      TEXT DEFAULT 'PENDING_APPROVAL',
                approved_at TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)


def insert_lead(name: str, email: str, phone: str, language: str, budget_usd: float) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO leads (name, email, phone, language, budget_usd) VALUES (?,?,?,?,?)",
            (name, email, phone, language, budget_usd),
        )
        return cur.lastrowid


def insert_land_data(lead_id: int, land_type: str, area_m2: float, location: str,
                     road_type: str, highway_proximity_m: float,
                     title_constraints: list, gov_signal: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO land_data
               (lead_id, land_type, area_m2, location, road_type,
                highway_proximity_m, title_constraints, gov_signal)
               VALUES (?,?,?,?,?,?,?,?)""",
            (lead_id, land_type, area_m2, location, road_type,
             highway_proximity_m, json.dumps(title_constraints), gov_signal),
        )
        return cur.lastrowid


def save_message(lead_id: int, agent: str, lang: str,
                 message: str, status: str = "PENDING_APPROVAL") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (lead_id, agent, lang, message, status) VALUES (?,?,?,?,?)",
            (lead_id, agent, lang, message, status),
        )
        return cur.lastrowid


def approve_message(message_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE messages SET status='APPROVED', approved_at=datetime('now') WHERE id=?",
            (message_id,),
        )


def get_leads() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM leads ORDER BY created_at DESC"
        )]


def get_messages(lead_id: int) -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM messages WHERE lead_id=? ORDER BY created_at DESC", (lead_id,)
        )]


def get_active_signals() -> list:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM gov_signals WHERE active=1 ORDER BY confidence_pct DESC"
        )]
