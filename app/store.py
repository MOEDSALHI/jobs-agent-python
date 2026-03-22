import json
import hashlib
from pathlib import Path
from typing import Iterable, List
from datetime import datetime, timezone

from .models import Job


def _h(url: str) -> str:
    return hashlib.sha1(str(url).encode()).hexdigest()


def load_jobs(state_path: str) -> list[dict]:
    path = Path(state_path)

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"jobs": []}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("jobs", [])
    except Exception:
        return []


def save_jobs(state_path: str, jobs: list[dict]) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"jobs": jobs}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_new(state_path: str, jobs: Iterable[Job]) -> list[Job]:
    existing_jobs = load_jobs(state_path)
    existing_hashes = {job["url_hash"] for job in existing_jobs}

    new: List[Job] = []

    for job in jobs:
        url_hash = _h(str(job.url))

        if url_hash in existing_hashes:
            continue

        job_dict = {
            "url_hash": url_hash,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": str(job.url),
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "source": job.source,
            "score": job.score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        existing_jobs.append(job_dict)
        existing_hashes.add(url_hash)
        new.append(job)

    save_jobs(state_path, existing_jobs)
    return new