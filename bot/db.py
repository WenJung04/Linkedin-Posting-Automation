"""SQLite storage for events, captures, answers and drafts. Single user, so plain sqlite3."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from bot.prompt import Draft
from bot.session import ACTIVE_STATUSES, Session

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    question_index INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    kind TEXT NOT NULL,          -- 'note' or 'photo'
    text TEXT NOT NULL DEFAULT '',  -- note text or photo caption
    photo_path TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS answers (
    event_id INTEGER NOT NULL REFERENCES events(id),
    question_key TEXT NOT NULL,
    answer TEXT,                 -- NULL means skipped
    PRIMARY KEY (event_id, question_key)
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    body_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def _session(self, row: sqlite3.Row | None) -> Session | None:
        if row is None:
            return None
        return Session(row["id"], row["name"], row["status"], row["question_index"])

    def create_event(self, name: str) -> Session:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO events (name, status, started_at) VALUES (?, 'capturing', ?)",
                (name, _now()),
            )
        return Session(cur.lastrowid, name)

    def active_session(self) -> Session | None:
        placeholders = ",".join("?" * len(ACTIVE_STATUSES))
        row = self.conn.execute(
            f"SELECT * FROM events WHERE status IN ({placeholders}) ORDER BY id DESC LIMIT 1",
            ACTIVE_STATUSES,
        ).fetchone()
        return self._session(row)

    def latest_session(self) -> Session | None:
        row = self.conn.execute(
            "SELECT * FROM events WHERE status != 'cancelled' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return self._session(row)

    def save_session(self, session: Session) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE events SET status = ?, question_index = ? WHERE id = ?",
                (session.status, session.question_index, session.event_id),
            )

    def add_note(self, event_id: int, text: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO captures (event_id, kind, text, created_at) VALUES (?, 'note', ?, ?)",
                (event_id, text, _now()),
            )

    def add_photo(self, event_id: int, caption: str, photo_path: Path) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO captures (event_id, kind, text, photo_path, created_at) "
                "VALUES (?, 'photo', ?, ?, ?)",
                (event_id, caption, str(photo_path), _now()),
            )

    def notes(self, event_id: int) -> list[str]:
        rows = self.conn.execute(
            "SELECT text FROM captures WHERE event_id = ? AND kind = 'note' ORDER BY id",
            (event_id,),
        )
        return [row["text"] for row in rows]

    def photos(self, event_id: int) -> list[tuple[Path, str]]:
        rows = self.conn.execute(
            "SELECT photo_path, text FROM captures WHERE event_id = ? AND kind = 'photo' ORDER BY id",
            (event_id,),
        )
        return [(Path(row["photo_path"]), row["text"]) for row in rows]

    def capture_counts(self, event_id: int) -> tuple[int, int]:
        row = self.conn.execute(
            "SELECT SUM(kind = 'note') AS notes, SUM(kind = 'photo') AS photos "
            "FROM captures WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        return row["notes"] or 0, row["photos"] or 0

    def save_answer(self, event_id: int, key: str, answer: str | None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO answers (event_id, question_key, answer) VALUES (?, ?, ?)",
                (event_id, key, answer),
            )

    def answers(self, event_id: int) -> dict[str, str | None]:
        rows = self.conn.execute(
            "SELECT question_key, answer FROM answers WHERE event_id = ?", (event_id,)
        )
        return {row["question_key"]: row["answer"] for row in rows}

    def save_draft(self, event_id: int, draft: Draft) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO drafts (event_id, body_json, created_at) VALUES (?, ?, ?)",
                (event_id, json.dumps(draft.__dict__), _now()),
            )
