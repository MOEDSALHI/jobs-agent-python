from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class Job(BaseModel):
    title: str
    url: HttpUrl
    source: str
    company: Optional[str] = None
    location: Optional[str] = None
    posted_at: Optional[datetime] = None
    score: float = 0.0
