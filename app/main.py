from fastapi import FastAPI, Header, HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import structlog

from .config import S, TZINFO
from .logging import setup_logging
from .models import Job
from .notify_email import send_email
from .runner import run_once

setup_logging()
log = structlog.get_logger()

app = FastAPI(title="jobs-agent")

MET_NEW = Counter("jobs_new_total", "New jobs saved")
MET_LAST = Gauge("jobs_last_run_ts", "Last run timestamp (epoch seconds)")


@app.on_event("startup")
async def _sched():
    sch = AsyncIOScheduler(timezone=TZINFO)
    sch.add_job(run_once, CronTrigger(hour=S.RUN_AT_HOUR, minute=S.RUN_AT_MINUTE))
    sch.start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/run")
async def run_now(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != S.JOBS_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    new = await run_once()
    MET_NEW.inc(len(new))
    MET_LAST.set_to_current_time()
    return {"inserted": len(new)}


@app.post("/test-email")
async def test_email(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != S.JOBS_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    dummy = Job(title="Test email jobs-agent", url="https://example.com", source="test")
    await send_email([dummy])
    return {"status": "sent"}