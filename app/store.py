import sqlite3, hashlib
from typing import Iterable, List
from .models import Job

DDL = """
CREATE TABLE IF NOT EXISTS jobs(
  url_hash TEXT PRIMARY KEY,
  title TEXT, company TEXT, location TEXT, url TEXT,
  posted_at TEXT, source TEXT, score REAL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.execute(DDL)
    return c

def _h(url: str) -> str:
    import hashlib
    return hashlib.sha1(str(url).encode()).hexdigest()  # <- cast str

def save_new(conn: sqlite3.Connection, jobs: Iterable[Job]) -> list[Job]:
    new: List[Job] = []
    for j in jobs:
        try:
            conn.execute(
                "INSERT INTO jobs(url_hash,title,company,location,url,posted_at,source,score)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (_h(str(j.url)), j.title, j.company, j.location, str(j.url),  # <- cast str
                 j.posted_at.isoformat() if j.posted_at else None,
                 j.source, j.score),
            )
            new.append(j)
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return new
