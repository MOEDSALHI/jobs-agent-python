from typing import List
from .base import browser_page, prepare, get_links, is_job_url, slug_to_title
from ..models import Job
import structlog, urllib.parse
log = structlog.get_logger()

URL = ("https://www.apec.fr/candidat/recherche-emploi.html/emploi"
       "?motsCles=d%C3%A9veloppeur%20python"
       "&anciennetePublication=101850"
       "&typesConvention=143706&typesConvention=143687&typesConvention=143686"
       "&typesConvention=143684&typesConvention=143685"
       "&lieux=711&salaireMinimum=20&salaireMaximum=200")

def _same_domain(href: str) -> bool:
    try:
        return urllib.parse.urlparse(href).netloc.endswith("apec.fr")
    except Exception:
        return False

async def scrape() -> List[Job]:
    async with browser_page() as page:
        await prepare(URL, page)
        raw = await get_links(page)

    out: List[Job] = []
    seen = set()
    for it in raw:
        href = (it.get("href") or "")
        if not _same_domain(href):
            continue
        if not is_job_url(href, "apec"):
            # tolérance: certaines offres sont /candidat/xxxxx/offre-xxxxx.html avec params
            if "offre-" not in href and "/emploi/" not in href:
                continue
        if href in seen:
            continue
        seen.add(href)
        txt = (it.get("text") or "").strip()
        title = txt if len(txt) > 8 else slug_to_title(href)
        if len(title) < 6:
            continue
        out.append(Job(title=title, url=href, source="apec"))
    log.info("apec_jobs", count=len(out))
    return out
