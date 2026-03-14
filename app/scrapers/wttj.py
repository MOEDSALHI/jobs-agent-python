from typing import List
from .base import browser_page, prepare, get_links, is_job_url, slug_to_title
from ..models import Job
import structlog
log = structlog.get_logger()

URL = ("https://www.welcometothejungle.com/fr/jobs"
       "?refinementList%5Boffices.country_code%5D%5B%5D=FR"
       "&refinementList%5Boffices.state%5D%5B%5D=%C3%8Ele-de-France"
       "&refinementList%5Bcontract_type%5D%5B%5D=FULL_TIME"
       "&refinementList%5Bcontract_type%5D%5B%5D=FREELANCE"
       "&query=d%C3%A9veloppeur%20python&page=1"
       "&aroundQuery=%C3%8Ele-de-France%2C%20France&sortBy=mostRecent")

async def scrape() -> List[Job]:
    async with browser_page() as page:
        await prepare(URL, page)
        raw = await get_links(page)

    out: List[Job] = []
    seen = set()
    for it in raw:
        href = (it.get("href") or "")
        if not is_job_url(href, "wttj"): 
            continue
        if href in seen: 
            continue
        seen.add(href)
        txt = (it.get("text") or "").strip()
        title = txt if len(txt) > 8 else slug_to_title(href)
        if len(title) < 6:
            continue
        out.append(Job(title=title, url=href, source="wttj"))
    log.info("wttj_jobs", count=len(out))
    return out
