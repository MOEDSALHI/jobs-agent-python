from __future__ import annotations

import asyncio
import structlog

from .models import Job
from .scoring import score
from .store import save_new
from .notify_email import send_email
from .notify_telegram import send_tg
from .config import S
from .scrapers import apec, wttj, hellowork

log = structlog.get_logger()


def match_keywords(job: Job) -> bool:
    title = (job.title or "").lower()
    if any(k in title for k in S.keywords):
        return True

    from app.scrapers.base import slug_to_title
    slug_t = slug_to_title(str(job.url)).lower()
    return any(k in slug_t for k in S.keywords)


async def run_once() -> list[Job]:
    log.info("run_start")

    batches = await asyncio.gather(
        apec.scrape(),
        wttj.scrape(),
        hellowork.scrape(),
        return_exceptions=True,
    )

    jobs: list[Job] = []
    for batch in batches:
        if isinstance(batch, Exception):
            log.warning("scrape_err", err=str(batch))
            continue
        jobs.extend(batch)

    filtered: list[Job] = []
    seen = set()

    for job in jobs:
        if not match_keywords(job):
            continue

        job.score = score(job, S.keywords)

        if str(job.url) in seen:
            continue
        seen.add(str(job.url))
        filtered.append(job)

    log.info("filter_stats", raw=len(jobs), kept=len(filtered))

    # conn = connect(S.DB_PATH)
    # new = save_new(conn, filtered)

    new = save_new(S.STATE_PATH, filtered)

    if new:
        ranked = sorted(new, key=lambda x: -x.score)
        await send_email(ranked[:40])
        await send_tg(ranked[:20])

    log.info("run_end", new=len(new), total=len(filtered))
    return new