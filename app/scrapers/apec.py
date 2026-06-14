from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import List

import structlog
from playwright.async_api import Page

from ..models import Job
from .base import browser_page, prepare, is_job_url

log = structlog.get_logger()

URL = (
    "https://www.apec.fr/candidat/recherche-emploi.html/emploi"
    "?motsCles=d%C3%A9veloppeur%20python"
    "&anciennetePublication=101850"
    "&typesConvention=143706&typesConvention=143687&typesConvention=143686"
    "&typesConvention=143684&typesConvention=143685"
    "&lieux=711&salaireMinimum=20&salaireMaximum=200"
)


def _clean_url(href: str) -> str:
    """Strip search query params — the job ID is in the path, params are not needed."""
    p = urllib.parse.urlparse(href)
    return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


async def _extract_cards(page: Page) -> list[dict]:
    return await page.eval_on_selector_all(
        'a[href*="detail-offre"]',
        """els => els.map(a => {
            const titleEl  = a.querySelector("h2.card-title");
            const companyEl = a.querySelector(".card-offer__company");
            const details  = Array.from(
                a.querySelectorAll(".details-offer.important-list li")
            ).map(li => li.textContent.trim()).filter(Boolean);
            return {
                href:     a.href,
                title:    titleEl  ? titleEl.textContent.trim()  : "",
                company:  companyEl ? companyEl.textContent.trim() : "",
                contract: details[0] || "",
                location: details[1] || "",
                date:     details[2] || ""
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
        if not is_job_url(href, "apec"):
            continue

        clean_href = _clean_url(href)
        if clean_href in seen:
            continue
        seen.add(clean_href)

        title = item.get("title", "").strip()
        if len(title) < 6:
            continue

        company = item.get("company", "").strip() or None
        city = item.get("location", "").strip()
        contract = item.get("contract", "").strip()
        location_parts = [p for p in [city, contract] if p]

        out.append(Job(
            title=title,
            url=clean_href,  # type: ignore[arg-type]
            source="apec",
            company=company,
            location=" · ".join(location_parts) or None,
            posted_at=_parse_date(item.get("date", "")),
        ))

    log.info("apec_jobs", count=len(out))
    return out
