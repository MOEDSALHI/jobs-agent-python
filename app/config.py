from pydantic_settings import BaseSettings
from typing import List
import zoneinfo

class Settings(BaseSettings):
    TZ: str = "Europe/Paris"
    KEYWORDS: str = "python,fastapi,django,backend"
    MAIL_SMTP_HOST: str
    MAIL_SMTP_PORT: int = 587
    MAIL_SMTP_USER: str
    MAIL_SMTP_PASS: str
    MAIL_TO: str
    TG_BOT_TOKEN: str | None = None
    TG_CHAT_ID: str | None = None
    JOBS_API_KEY: str = "change_me"
    RUN_AT_HOUR: int = 8
    RUN_AT_MINUTE: int = 10
    DB_PATH: str = "jobs.db"
    MAIL_USE_TLS: bool = False        # TLS implicite (port 465)
    MAIL_USE_STARTTLS: bool = True    # STARTTLS (port 587)
    
    @property
    def keywords(self) -> List[str]:
        return [k.strip().lower() for k in self.KEYWORDS.split(",") if k.strip()]

    class Config:
        env_file = ".env"

S = Settings()
TZINFO = zoneinfo.ZoneInfo(S.TZ)
