#!/usr/bin/env python3
"""
Phase 1/2: Database Schema & Builder.

Creates SQLite database mirroring the ESORICS 2018 MariaDB schema (Fig. 2)
with extensions for malware family tracking and LLM experiment support.
"""

import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.config import DB_PATH


SCHEMA = """
-- ============================================================
-- Dataset registry: tracks which CTU scenario data came from
-- ============================================================
CREATE TABLE IF NOT EXISTS datasets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    source_url  TEXT,
    malware_family TEXT,
    malware_type   TEXT,
    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Sessions: TCP/UDP sessions (bidirectional flows)
-- Maps to ESORICS 2018 Fig. 2 "sessions" table
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id  INTEGER NOT NULL,
    src_ip      TEXT,
    dst_ip      TEXT,
    src_port    INTEGER,
    dst_port    INTEGER,
    protocol    TEXT,
    is_malicious INTEGER NOT NULL DEFAULT 0,  -- 0=normal, 1=malicious
    label       TEXT,                          -- detailed label string
    malware_family TEXT,                       -- for leave-one-family-out
    is_encrypted   INTEGER DEFAULT 0,          -- 0=no, 1=yes (TLS/SSL)
    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

-- ============================================================
-- Packets: per-packet side-channel features
-- Maps to ESORICS 2018 Fig. 2 "packets" table
-- Features from Section 4.2:
--   packet_size     = Ps
--   payload_size    = PAs  
--   payload_ratio   = Pr = PAs/Ps
--   ratio_to_prev   = Rpp = Pp/PPs (0 for 1st packet)
--   time_diff       = Td = Pt - PPt (0 for 1st packet)
-- ============================================================
CREATE TABLE IF NOT EXISTS packets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL,
    packet_idx      INTEGER NOT NULL,         -- position within session
    packet_size     INTEGER NOT NULL,         -- Ps
    payload_size    INTEGER NOT NULL,         -- PAs
    payload_ratio   REAL NOT NULL,            -- Pr
    ratio_to_prev   REAL NOT NULL DEFAULT 0,  -- Rpp
    time_diff       REAL NOT NULL DEFAULT 0,  -- Td
    timestamp       REAL,                     -- absolute packet time
    direction       TEXT,                     -- 'outgoing' or 'incoming'
    is_malicious    INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================
-- LLM experiment results: store classifications and reasoning
-- ============================================================
CREATE TABLE IF NOT EXISTS llm_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment      TEXT NOT NULL,             -- e.g., '4A_zero_shot'
    model           TEXT NOT NULL,             -- e.g., 'claude-sonnet-4-6'
    session_id      INTEGER,
    packet_ids      TEXT,                      -- JSON array of packet IDs used
    prompt_hash     TEXT,                      -- for deduplication
    prediction      INTEGER,                  -- 0=normal, 1=malicious
    confidence      REAL,                     -- LLM's stated confidence
    reasoning       TEXT,                     -- chain-of-thought text
    ground_truth    INTEGER,
    tokens_used     INTEGER,
    latency_ms      REAL,
    created         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- ============================================================
-- Indexes for query performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_packets_session ON packets(session_id);
CREATE INDEX IF NOT EXISTS idx_packets_malicious ON packets(is_malicious);
CREATE INDEX IF NOT EXISTS idx_sessions_dataset ON sessions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_sessions_malicious ON sessions(is_malicious);
CREATE INDEX IF NOT EXISTS idx_sessions_family ON sessions(malware_family);
CREATE INDEX IF NOT EXISTS idx_llm_experiment ON llm_results(experiment, model);
"""


def _configure_conn(conn: sqlite3.Connection) -> None:
    """Apply consistent settings to every connection: WAL mode, Row factory."""
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.commit()


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize database with schema. Returns connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    _configure_conn(conn)
    return conn


def get_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Get database connection. Creates DB if it doesn't exist."""
    if not db_path.exists():
        return init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    _configure_conn(conn)
    return conn


def register_dataset(conn: sqlite3.Connection, name: str,
                     family: str, mtype: str, url: str = "") -> int:
    """Register a dataset, return its ID. Idempotent."""
    cur = conn.execute("SELECT id FROM datasets WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0] if isinstance(row, tuple) else row["id"]

    cur = conn.execute(
        "INSERT INTO datasets (name, source_url, malware_family, malware_type) "
        "VALUES (?, ?, ?, ?)",
        (name, url, family, mtype)
    )
    conn.commit()
    return cur.lastrowid


def insert_session(conn: sqlite3.Connection, dataset_id: int,
                   src_ip: str, dst_ip: str, src_port: int, dst_port: int,
                   protocol: str, is_malicious: int, label: str = "",
                   malware_family: str = "", is_encrypted: int = 0) -> int:
    """Insert a session record, return its ID."""
    cur = conn.execute(
        "INSERT INTO sessions "
        "(dataset_id, src_ip, dst_ip, src_port, dst_port, protocol, "
        "is_malicious, label, malware_family, is_encrypted) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (dataset_id, src_ip, dst_ip, src_port, dst_port, protocol,
         is_malicious, label, malware_family, is_encrypted)
    )
    return cur.lastrowid


def insert_packets_batch(conn: sqlite3.Connection, packets: list[tuple]):
    """
    Bulk insert packets. Each tuple:
    (session_id, packet_idx, packet_size, payload_size, payload_ratio,
     ratio_to_prev, time_diff, timestamp, direction, is_malicious)
    """
    conn.executemany(
        "INSERT INTO packets "
        "(session_id, packet_idx, packet_size, payload_size, payload_ratio, "
        "ratio_to_prev, time_diff, timestamp, direction, is_malicious) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        packets
    )


def get_dataset_stats(conn: sqlite3.Connection) -> dict:
    """Return summary statistics of the database."""
    stats = {}
    cur = conn.execute("SELECT COUNT(*) FROM datasets")
    stats["num_datasets"] = cur.fetchone()[0]

    cur = conn.execute("SELECT COUNT(*) FROM sessions")
    stats["num_sessions"] = cur.fetchone()[0]

    cur = conn.execute("SELECT COUNT(*) FROM sessions WHERE is_malicious=1")
    stats["num_malicious_sessions"] = cur.fetchone()[0]

    cur = conn.execute("SELECT COUNT(*) FROM sessions WHERE is_malicious=0")
    stats["num_normal_sessions"] = cur.fetchone()[0]

    cur = conn.execute("SELECT COUNT(*) FROM packets")
    stats["num_packets"] = cur.fetchone()[0]

    cur = conn.execute("SELECT COUNT(*) FROM packets WHERE is_malicious=1")
    stats["num_malicious_packets"] = cur.fetchone()[0]

    cur = conn.execute("SELECT COUNT(*) FROM packets WHERE is_malicious=0")
    stats["num_normal_packets"] = cur.fetchone()[0]

    cur = conn.execute(
        "SELECT malware_family, COUNT(*) FROM sessions "
        "WHERE malware_family != '' GROUP BY malware_family"
    )
    stats["family_distribution"] = dict(cur.fetchall())

    return stats


if __name__ == "__main__":
    conn = init_db()
    print(f"Database initialized at: {DB_PATH}")
    print(f"Tables created: datasets, sessions, packets, llm_results")
    conn.close()
