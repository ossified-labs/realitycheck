"""SQLite storage (stdlib only). Swap for PostgreSQL later by reimplementing this module."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    claim TEXT NOT NULL,
    status TEXT NOT NULL,              -- queued | researching | analyzing | completed | partial | failed
    error TEXT,
    verdict TEXT,                      -- overall verdict label
    report_json TEXT,                  -- structured report (see services/report.py)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subclaims (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    claim_type TEXT,                   -- causal | correlational | descriptive | quantitative | other
    qualifiers_json TEXT,              -- population, timeframe, etc.
    queries_json TEXT,
    verdict TEXT,
    verdict_reason TEXT
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT,
    domain TEXT,
    published_date TEXT,
    content TEXT,                      -- text we retrieved (truncated)
    duplicate_of TEXT,                 -- source id this near-duplicates, if any
    injection_flag INTEGER NOT NULL DEFAULT 0,
    snippet_only INTEGER NOT NULL DEFAULT 0,  -- 1 if we only had the search snippet, not the page
    retrieved_at TEXT NOT NULL,
    UNIQUE (investigation_id, canonical_url)
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    subclaim_id TEXT NOT NULL REFERENCES subclaims(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    label TEXT NOT NULL,               -- supports | contradicts | mixed | insufficient
    passage TEXT NOT NULL,             -- the passage shown to the model
    quote TEXT,                        -- verbatim quote the model relied on (validated)
    quote_verified INTEGER NOT NULL DEFAULT 0,
    explanation TEXT,
    evidence_type TEXT,                -- rct | meta_analysis | observational | ... | unknown
    shows_causation INTEGER,
    relevance REAL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Database:
    """Thin thread-safe wrapper. One connection guarded by a lock is plenty for an MVP."""

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.lock = threading.Lock()
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    # -- generic helpers -------------------------------------------------
    def _exec(self, sql: str, params: tuple = ()) -> None:
        with self.lock:
            self.conn.execute(sql, params)
            self.conn.commit()

    def _all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    # -- investigations --------------------------------------------------
    def create_investigation(self, claim: str) -> str:
        inv_id = new_id()
        now = _now()
        self._exec(
            "INSERT INTO investigations (id, claim, status, created_at, updated_at) VALUES (?,?,?,?,?)",
            (inv_id, claim, "queued", now, now),
        )
        return inv_id

    def set_status(self, inv_id: str, status: str, error: str | None = None) -> None:
        self._exec(
            "UPDATE investigations SET status=?, error=?, updated_at=? WHERE id=?",
            (status, error, _now(), inv_id),
        )

    def save_report(self, inv_id: str, verdict: str, report: dict) -> None:
        self._exec(
            "UPDATE investigations SET verdict=?, report_json=?, updated_at=? WHERE id=?",
            (verdict, json.dumps(report), _now(), inv_id),
        )

    def get_investigation(self, inv_id: str) -> dict | None:
        row = self._one("SELECT * FROM investigations WHERE id=?", (inv_id,))
        if row:
            row["report"] = json.loads(row.pop("report_json") or "null")
        return row

    def list_investigations(self, limit: int = 50) -> list[dict]:
        return self._all(
            "SELECT id, claim, status, verdict, created_at FROM investigations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )

    def count_recent(self, since_iso: str) -> int:
        row = self._one("SELECT COUNT(*) AS n FROM investigations WHERE created_at >= ?", (since_iso,))
        return int(row["n"]) if row else 0

    # -- subclaims -------------------------------------------------------
    def add_subclaim(self, inv_id: str, position: int, text: str, claim_type: str,
                     qualifiers: dict, queries: list[str]) -> str:
        sc_id = new_id()
        self._exec(
            "INSERT INTO subclaims (id, investigation_id, position, text, claim_type, qualifiers_json, queries_json)"
            " VALUES (?,?,?,?,?,?,?)",
            (sc_id, inv_id, position, text, claim_type, json.dumps(qualifiers), json.dumps(queries)),
        )
        return sc_id

    def set_subclaim_verdict(self, sc_id: str, verdict: str, reason: str) -> None:
        self._exec("UPDATE subclaims SET verdict=?, verdict_reason=? WHERE id=?", (verdict, reason, sc_id))

    def get_subclaims(self, inv_id: str) -> list[dict]:
        rows = self._all("SELECT * FROM subclaims WHERE investigation_id=? ORDER BY position", (inv_id,))
        for r in rows:
            r["qualifiers"] = json.loads(r.pop("qualifiers_json") or "{}")
            r["queries"] = json.loads(r.pop("queries_json") or "[]")
        return rows

    # -- sources ---------------------------------------------------------
    def add_source(self, inv_id: str, *, url: str, canonical_url: str, title: str, domain: str,
                   published_date: str | None, content: str, duplicate_of: str | None,
                   injection_flag: bool, snippet_only: bool) -> str:
        existing = self._one(
            "SELECT id FROM sources WHERE investigation_id=? AND canonical_url=?", (inv_id, canonical_url)
        )
        if existing:
            return existing["id"]
        src_id = new_id()
        self._exec(
            "INSERT INTO sources (id, investigation_id, url, canonical_url, title, domain, published_date,"
            " content, duplicate_of, injection_flag, snippet_only, retrieved_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (src_id, inv_id, url, canonical_url, title, domain, published_date, content,
             duplicate_of, int(injection_flag), int(snippet_only), _now()),
        )
        return src_id

    def get_sources(self, inv_id: str) -> list[dict]:
        return self._all(
            "SELECT id, url, title, domain, published_date, duplicate_of, injection_flag, snippet_only,"
            " retrieved_at"
            " FROM sources WHERE investigation_id=? ORDER BY retrieved_at",
            (inv_id,),
        )

    # -- evidence --------------------------------------------------------
    def add_evidence(self, inv_id: str, sc_id: str, src_id: str, *, label: str, passage: str,
                     quote: str | None, quote_verified: bool, explanation: str,
                     evidence_type: str, shows_causation: bool | None, relevance: float) -> str:
        ev_id = new_id()
        self._exec(
            "INSERT INTO evidence (id, investigation_id, subclaim_id, source_id, label, passage, quote,"
            " quote_verified, explanation, evidence_type, shows_causation, relevance)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (ev_id, inv_id, sc_id, src_id, label, passage, quote, int(quote_verified), explanation,
             evidence_type, None if shows_causation is None else int(shows_causation), relevance),
        )
        return ev_id

    def get_evidence(self, inv_id: str) -> list[dict]:
        return self._all(
            "SELECT e.*, s.url, s.title, s.domain, s.published_date, s.duplicate_of, s.injection_flag,"
            " s.snippet_only"
            " FROM evidence e JOIN sources s ON s.id = e.source_id"
            " WHERE e.investigation_id=? ORDER BY e.relevance DESC",
            (inv_id,),
        )
