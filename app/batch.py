from __future__ import annotations

import asyncio
import sys

from app.logging import setup_logging
from app.runner import run_once


async def main() -> int:
    setup_logging()
    new_jobs = await run_once()
    print({"inserted": len(new_jobs)})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))