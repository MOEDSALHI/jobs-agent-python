from typing import List
from .models import Job
from .config import S
from telegram import Bot

async def send_tg(jobs: List[Job]) -> None:
    if not S.TG_BOT_TOKEN or not S.TG_CHAT_ID or not jobs:
        return
    bot = Bot(S.TG_BOT_TOKEN)
    txt = "Offres Python du jour:\n" + "\n".join(f"• {j.title}\n{j.url}" for j in jobs[:20])
    await bot.send_message(chat_id=S.TG_CHAT_ID, text=txt, disable_web_page_preview=True)
