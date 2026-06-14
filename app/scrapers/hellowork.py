from __future__ import annotations

from typing import List

import structlog
from playwright.async_api import Page

from ..models import Job
from .base import browser_page, prepare, is_job_url

log = structlog.get_logger()

# d=3j = last 3 days; store deduplication prevents re-sending already-seen jobs
URL = ("https://www.hellowork.com/fr-fr/emploi/recherche.html"
       "?k=D%C3%A9veloppeur+Python&l=%C3%8Ele-de-France&d=3j&c=CDI&c=Independant&p=1")


async def _extract_cards(page: Page) -> list[dict]:
    return await page.eval_on_selector_all(
        'a[data-cy="offerTitle"]',
        """els => els.map(a => {
            const li        = a.closest('li');
            const titleEl   = a.querySelector('h3 p:first-child');
            const companyEl = a.querySelector('h3 p.typo-s');
            const location  = li?.querySelector('[data-cy="localisationCard"]')
                                ?.textContent?.trim() || '';
            const contract  = li?.querySelector('[data-cy="contractCard"]')
                                ?.textContent?.trim() || '';
            const remote    = li?.querySelector('[data-cy="contractTag"]')
                                ?.textContent?.trim() || '';
            return {
                href:    a.href,
                title:   titleEl?.textContent?.trim()   || '',
                company: companyEl?.textContent?.trim() || '',
                location: location,
                contract: contract,
                remote:   remote,
            };
        })"""
    )


async def scrape() -> List[Job]:
    async with browser_page() as page:
        await prepare(URL, page)
        raw = await _extract_cards(page)

    out: List[Job] = []
    seen: set[str] = set()

    for item in raw:
        href = item.get("href", "")
        if not is_job_url(href, "hellowork"):
            continue
        if href in seen:
            continue
        seen.add(href)

        title = item.get("title", "").strip()
        if len(title) < 6:
            continue

        loc_parts = [
            p for p in [
                item.get("location", "").strip(),
                item.get("contract", "").strip(),
                item.get("remote", "").strip(),
            ] if p
        ]
        out.append(Job(
            title=title,
            url=href,  # type: ignore[arg-type]
            source="hellowork",
            company=item.get("company", "").strip() or None,
            location=" · ".join(loc_parts) or None,
        ))

    log.info("hellowork_jobs", count=len(out))
    return out
