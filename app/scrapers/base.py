from playwright.async_api import async_playwright, Page, TimeoutError as PwTimeout
from contextlib import asynccontextmanager
import asyncio
import structlog
import re, urllib.parse

log = structlog.get_logger()

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

@asynccontextmanager
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            extra_http_headers={"User-Agent": UA},
            viewport={"width": 1366, "height": 900},
        )
        page = await ctx.new_page()
        try:
            yield page
        finally:
            await ctx.close(); await browser.close()

async def _try_click(page: Page, selector: str) -> bool:
    try:
        await page.click(selector, timeout=2000)
        return True
    except Exception:
        return False

async def accept_cookies(page: Page) -> None:
    # Essais multi-sélecteurs (FR/EN)
    selectors = [
        'button:has-text("Tout accepter")',
        'button:has-text("Accepter")',
        'button:has-text("J\'accepte")',
        'button:has-text("Accept all")',
        '[aria-label*="accept"]',
        '[data-testid*="consent"] button',
    ]
    for s in selectors:
        if await _try_click(page, s):
            log.info("cookies_clicked", selector=s)
            await asyncio.sleep(0.5)
            return

async def auto_scroll(page: Page, max_steps: int = 20) -> None:
    last_height = 0
    for i in range(max_steps):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(0.5)
        height = await page.evaluate("document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height

async def prepare(url: str, page: Page) -> None:
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
    except PwTimeout:
        log.warning("goto_timeout", url=url)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await accept_cookies(page)
    await auto_scroll(page)

async def get_links(page: Page) -> list[dict]:
    links = await page.eval_on_selector_all(
        "a[href]", "els => els.map(e=>({href:e.href, text:e.textContent?.trim()}))"
    )
    log.info("links_found", count=len(links))
    return links



JOB_PATTERNS = {
    "wttj": re.compile(r"/fr/companies/[^/]+/jobs/[^/]+"),
    # HelloWork: pages d'offre finissant par .html sous /fr-fr/emploi(s)/
    "hellowork": re.compile(r"/fr-fr/emplois?/[^?#]+\.html$"),
    # APEC: multiple formes d'URL d’offre
    "apec": re.compile(
        r"/(offre-(?:emploi|candidat)|offres?)/[^?#]+|/emploi/fiche-emploi/[^?#]+"
    ),
}

def slug_to_title(href: str) -> str:
    # prenne le dernier segment, retire .html, remplace - par espace
    path = urllib.parse.urlparse(href).path
    seg = path.rstrip("/").split("/")[-1]
    seg = seg.replace(".html", "")
    seg = urllib.parse.unquote(seg)
    seg = re.sub(r"[-_]+", " ", seg)
    # capitalisation simple
    return seg.strip().title()

def is_job_url(href: str, source: str) -> bool:
    pat = JOB_PATTERNS.get(source)
    return bool(pat and pat.search(href or ""))
