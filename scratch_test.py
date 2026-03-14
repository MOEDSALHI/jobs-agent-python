import asyncio
from app.scrapers import apec, wttj, hellowork

async def main():
    for fn in (apec.scrape, wttj.scrape, hellowork.scrape):
        name = fn.__module__.split('.')[-1]
        print(f"== {name} ==")
        jobs = await fn()
        print(name, "count:", len(jobs))
        for j in jobs[:5]:
            print("-", j.title[:80], j.url)

asyncio.run(main())