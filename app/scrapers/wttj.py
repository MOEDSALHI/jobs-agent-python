from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import List

import httpx
import structlog
from playwright.async_api import async_playwright, TimeoutError as PwTimeout

from ..config import S
from ..models import Job

log = structlog.get_logger()

WTTJ_BASE = "https://www.welcometothejungle.com"
WTTJ_API_BASE = "https://api.welcometothejungle.com"
WTTJ_LOGIN_URL = f"{WTTJ_BASE}/fr/authenticate/signin"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CONTRACT_LABELS: dict[str, str] = {
    "full_time": "CDI",
    "part_time": "Temps partiel",
    "internship": "Stage",
    "apprenticeship": "Alternance",
    "freelance": "Freelance",
    "temporary": "CDD",
    "vie": "VIE",
}

REMOTE_LABELS: dict[str, str] = {
    "no": "",
    "partial": " · Remote partiel",
    "full": " · Full remote",
}


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html or "")
    return s.get_text()


async def _get_session_cookies(email: str, password: str) -> dict[str, str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=UA,
            locale="fr-FR",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        log.info("wttj_login_start")
        await page.goto(WTTJ_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        try:
            await page.fill('[data-testid="sign-in-form-email-input"]', email)
            await page.fill('[data-testid="sign-in-form-password-input"]', password)
            await page.click('[data-testid="sign-in-form-submit-button"]')
            # Wait for a post-login DOM element — more reliable than wait_for_url on SPAs
            await page.wait_for_selector(
                '[data-testid="nav-logout-button"], [data-testid="nav-my-space-button"]',
                timeout=20000,
            )
            log.info("wttj_login_ok")
        except PwTimeout:
            log.warning("wttj_login_failed")
            await browser.close()
            return {}

        cookies = {
            c["name"]: c["value"]
            for c in await context.cookies()
            if "welcometothejungle" in c.get("domain", "")
        }
        await browser.close()
        return cookies


async def _fetch_all_pages(
    client: httpx.AsyncClient, published_since: str = "last_3d"
) -> list[dict]:
    # Warm up the semantic search engine before querying jobs
    await client.get(
        f"{WTTJ_API_BASE}/api/v3/search/embedding_generation", timeout=10
    )

    url = f"{WTTJ_API_BASE}/api/v3/search/jobs"
    all_jobs: list[dict] = []
    page = 1

    while True:
        resp = await client.get(
            url,
            params={"page": page, "published_since": published_since, "version": "v1"},
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning("wttj_api_error", page=page, status=resp.status_code)
            break

        data = resp.json()
        all_jobs.extend(data.get("data", []))

        meta = data.get("metadata", {})
        if page >= meta.get("page_count", 1):
            break
        page += 1

    log.info("wttj_raw_jobs", count=len(all_jobs))
    return all_jobs


async def _fetch_job_content(
    client: httpx.AsyncClient, wk_reference: str
) -> str:
    """Fetches full job text via two API calls: resolve wk_reference → then fetch detail."""
    try:
        r1 = await client.get(
            f"{WTTJ_API_BASE}/api/v1/jobs/{wk_reference}", timeout=10
        )
        if r1.status_code != 200:
            return ""
        redirect = r1.json()
        org_slug = redirect["website_organization_slug"]
        job_slug = redirect["job_slug"]

        r2 = await client.get(
            f"{WTTJ_API_BASE}/api/v1/organizations/{org_slug}/jobs/{job_slug}",
            timeout=10,
        )
        if r2.status_code != 200:
            return ""
        detail = r2.json().get("job", {})

        parts: list[str] = []
        for field in ("description", "profile", "recruitment_process", "company_description"):
            val = detail.get(field)
            if isinstance(val, str):
                parts.append(_strip_html(val))
        for field in ("skills", "tools"):
            for item in detail.get(field) or []:
                if isinstance(item, dict) and item.get("name"):
                    parts.append(item["name"])

        return " ".join(parts)
    except Exception:
        return ""


def _build_job(raw: dict) -> Job | None:
    org = raw.get("organization") or {}
    website_org = org.get("website_organization") or {}
    # website_organization.slug is required for the public URL (≠ organization.slug)
    org_slug = website_org.get("slug") or org.get("slug", "")
    job_slug = raw.get("slug", "")

    if not org_slug or not job_slug:
        return None

    title = (raw.get("name") or "").strip()
    if len(title) < 3:
        return None

    office = raw.get("office") or {}
    city = office.get("city", "")
    contract = CONTRACT_LABELS.get(raw.get("contract_type", ""), raw.get("contract_type", ""))
    remote = REMOTE_LABELS.get(raw.get("remote", "no"), "")
    location_parts = [p for p in [city, contract + remote] if p]

    posted_at: datetime | None = None
    if raw.get("published_at"):
        try:
            posted_at = datetime.fromisoformat(
                raw["published_at"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except (ValueError, AttributeError):
            pass

    return Job(
        title=title,
        url=f"{WTTJ_BASE}/fr/companies/{org_slug}/jobs/{job_slug}",  # type: ignore[arg-type]
        source="wttj",
        company=org.get("name") or None,
        location=" · ".join(location_parts) or None,
        posted_at=posted_at,
    )


async def scrape() -> List[Job]:
    email = S.WTTJ_EMAIL or ""
    password = S.WTTJ_PASSWORD or ""

    if not email or not password:
        log.warning("wttj_no_credentials", msg="Set WTTJ_EMAIL and WTTJ_PASSWORD in .env")
        return []

    cookies = await _get_session_cookies(email, password)
    if not cookies:
        return []

    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Origin": WTTJ_BASE,
        "Referer": f"{WTTJ_BASE}/",
    }

    keywords = S.keywords
    results: list[Job] = []
    seen_ids: set[str] = set()
    content_checked = 0

    async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
        raw_jobs = await _fetch_all_pages(client)

        for raw in raw_jobs:
            job_id = raw.get("reference") or raw.get("slug", "")
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            job = _build_job(raw)
            if job is None:
                continue

            # Layer 1: title match (fast, no extra API calls)
            if any(k in job.title.lower() for k in keywords):
                results.append(job)
                continue

            # Layer 2: content match (2 API calls — only for jobs that missed title filter)
            wk_ref = raw.get("wk_reference", "")
            if not wk_ref:
                continue
            content = await _fetch_job_content(client, wk_ref)
            content_checked += 1
            if content and any(k in content.lower() for k in keywords):
                job.content = content
                results.append(job)

    log.info("wttj_jobs", count=len(results), content_checked=content_checked)
    return results
