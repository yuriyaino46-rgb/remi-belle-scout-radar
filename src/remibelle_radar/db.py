import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .models import ClassifiedCandidate, RadarResult

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY,
  display_name TEXT NOT NULL,
  priority TEXT NOT NULL,
  score INTEGER NOT NULL,
  reason TEXT NOT NULL,
  radar TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_text TEXT NOT NULL DEFAULT '',
  source_is_self_post INTEGER,
  x_url TEXT, instagram_url TEXT, instagram_status TEXT,
  tiktok_url TEXT, showroom_url TEXT, other_profile_url TEXT,
  age_text TEXT, affiliation_text TEXT,
  evidence_json TEXT NOT NULL DEFAULT '[]',
  discovered_at TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  excluded_reason TEXT,
  review_priority TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidates_x ON candidates(x_url) WHERE x_url IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidates_instagram ON candidates(instagram_url) WHERE instagram_url IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidates_tiktok ON candidates(tiktok_url) WHERE tiktok_url IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidates_showroom ON candidates(showroom_url) WHERE showroom_url IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidates_other ON candidates(other_profile_url) WHERE other_profile_url IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidates_source ON candidates(source_url);
CREATE TABLE IF NOT EXISTS sightings (
  id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL REFERENCES candidates(id),
  radar TEXT NOT NULL, source_url TEXT NOT NULL, seen_at TEXT NOT NULL,
  UNIQUE(candidate_id, source_url)
);
CREATE TABLE IF NOT EXISTS execution_logs (
  id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, executed_at TEXT NOT NULL,
  radar TEXT NOT NULL, searched INTEGER NOT NULL, added INTEGER NOT NULL,
  duplicates INTEGER NOT NULL, excluded INTEGER NOT NULL, failures INTEGER NOT NULL,
  s_count INTEGER NOT NULL, errors_json TEXT NOT NULL, unpersisted_json TEXT NOT NULL,
  sheet_synced INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert(self, item: ClassifiedCandidate) -> tuple[int, bool]:
        c = item.candidate
        with self.connect() as conn:
            existing = self._find_duplicate(conn, c)
            if existing:
                conn.execute(
                    "INSERT OR IGNORE INTO sightings(candidate_id,radar,source_url,seen_at) VALUES(?,?,?,?)",
                    (existing["id"], c.radar.value, c.source_url, c.discovered_at.isoformat()),
                )
                return int(existing["id"]), False
            values = (
                c.display_name, item.priority.value, item.score, item.reason, c.radar.value,
                c.source_url, c.source_text, c.source_is_self_post, c.x_url, c.instagram_url,
                c.instagram_status, c.tiktok_url, c.showroom_url, c.other_profile_url,
                c.age_text, c.affiliation_text, json.dumps(c.evidence, ensure_ascii=False),
                c.discovered_at.isoformat(), item.excluded_reason, item.review_priority,
            )
            cur = conn.execute(
                """INSERT INTO candidates(display_name,priority,score,reason,radar,source_url,
                source_text,source_is_self_post,x_url,instagram_url,instagram_status,tiktok_url,
                showroom_url,other_profile_url,age_text,affiliation_text,evidence_json,discovered_at,
                excluded_reason,review_priority) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )
            candidate_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO sightings(candidate_id,radar,source_url,seen_at) VALUES(?,?,?,?)",
                (candidate_id, c.radar.value, c.source_url, c.discovered_at.isoformat()),
            )
            return candidate_id, True

    @staticmethod
    def _find_duplicate(conn: sqlite3.Connection, c) -> sqlite3.Row | None:
        # Names are deliberately absent. A shared public profile URL is required.
        for column, value in (
            ("x_url", c.x_url), ("instagram_url", c.instagram_url),
            ("tiktok_url", c.tiktok_url), ("showroom_url", c.showroom_url),
            ("other_profile_url", c.other_profile_url), ("source_url", c.source_url),
        ):
            if value:
                row = conn.execute(f"SELECT id FROM candidates WHERE {column}=?", (value,)).fetchone()
                if row:
                    return row
        return None

    def save_log(self, run_id: str, executed_at: str, result: RadarResult) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO execution_logs(run_id,executed_at,radar,searched,added,duplicates,
                excluded,failures,s_count,errors_json,unpersisted_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, executed_at, result.radar.value, result.searched, result.added,
                 result.duplicates, result.excluded, result.failures, result.s_count,
                 json.dumps(result.errors, ensure_ascii=False),
                 json.dumps(result.unpersisted, ensure_ascii=False)),
            )

    def update_log(self, run_id: str, result: RadarResult, sheet_synced: bool = False) -> None:
        with self.connect() as conn:
            conn.execute(
                """UPDATE execution_logs SET failures=?, errors_json=?, unpersisted_json=?,
                sheet_synced=? WHERE run_id=? AND radar=?""",
                (result.failures, json.dumps(result.errors, ensure_ascii=False),
                 json.dumps(result.unpersisted, ensure_ascii=False), int(sheet_synced),
                 run_id, result.radar.value),
            )

    def rows(self, query: str, args: tuple = ()) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(query, args).fetchall()]
