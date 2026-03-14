from .models import Job

def score(job: Job, keywords: list[str]) -> float:
    title = (job.title or "").lower()
    s = sum(1 for k in keywords if k in title)
    if job.location and "remote" in job.location.lower():
        s += 1.5
    if any(w in title for w in ["senior", "lead"]):
        s += 1
    return float(s)
