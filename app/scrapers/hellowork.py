from typing import List
from .base import browser_page, prepare, get_links, is_job_url, slug_to_title
from ..models import Job
import structlog, urllib.parse
log = structlog.get_logger()

URL = ("https://www.hellowork.com/fr-fr/emploi/recherche.html"
       "?k=D%C3%A9veloppeur+Python&l=%C3%8Ele-de-France&d=h&c=CDI&c=Independant&p=1")

def _is_index(href: str) -> bool:
    p = urllib.parse.urlparse(href)
    return any(x in p.path for x in ("/index-", "/recherche.html")) or "#main-content" in href

async def scrape() -> List[Job]:
    async with browser_page() as page:
        await prepare(URL, page)
        raw = await get_links(page)

    out: List[Job] = []
    seen = set()
    for it in raw:
        href = (it.get("href") or "")
        if _is_index(href):
            continue
        if not is_job_url(href, "hellowork"):
            continue
        if href in seen:
            continue
        seen.add(href)
        txt = (it.get("text") or "").strip()
        title = txt if len(txt) > 8 else slug_to_title(href)
        if len(title) < 6:
            continue
        out.append(Job(title=title, url=href, source="hellowork"))
    log.info("hellowork_jobs", count=len(out))
    return out
