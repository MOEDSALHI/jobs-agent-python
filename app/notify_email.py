from __future__ import annotations

import asyncio
from email.message import EmailMessage
from typing import List

import structlog
from aiosmtplib import SMTP
from aiosmtplib.errors import SMTPException
from jinja2 import Template

from .config import S
from .models import Job

log = structlog.get_logger()

TPL = Template(
    """
<h3>Offres Python du jour ({{jobs|length}})</h3>
<ol>
{% for j in jobs %}
<li><a href="{{j.url}}">{{j.title}}</a> — <i>{{j.source}}</i></li>
{% endfor %}
</ol>
"""
)


async def send_email(jobs: List[Job]) -> None:
    if not jobs:
        log.info("email_skip_empty")
        return

    # Construire le message
    email_msg = EmailMessage()
    email_msg["From"] = S.MAIL_SMTP_USER
    email_msg["To"] = S.MAIL_TO
    email_msg["Subject"] = "Offres Python du jour"
    email_msg["Reply-To"] = S.MAIL_SMTP_USER

    html = TPL.render(jobs=jobs)
    email_msg.set_content("Voir version HTML.")
    email_msg.add_alternative(html, subtype="html")

    host = S.MAIL_SMTP_HOST
    port = S.MAIL_SMTP_PORT

    # Règle simple:
    # - 465 => TLS implicite
    # - 587 => STARTTLS
    use_tls = (port == 465)
    use_starttls = (port == 587)

    log.info(
        "email_connect_start",
        host=host,
        port=port,
        use_tls=use_tls,
        use_starttls=use_starttls,
        count=len(jobs),
        to=S.MAIL_TO,
    )

    try:
        async with SMTP(hostname=host, port=port, use_tls=use_tls, timeout=20) as s:
            # NOTE: ne pas appeler s.connect() ici (le context manager le gère)
            log.info("email_connected")

            if use_starttls:
                try:
                    await asyncio.wait_for(s.starttls(), timeout=20)
                    log.info("email_starttls_ok")
                except SMTPException as e:
                    # cas fréquent: la connexion est déjà TLS => on continue
                    if "already using tls" in str(e).lower():
                        log.info("email_starttls_skip_already_tls")
                    else:
                        raise

            await asyncio.wait_for(
                s.login(S.MAIL_SMTP_USER, S.MAIL_SMTP_PASS),
                timeout=20,
            )
            log.info("email_login_ok")

            await asyncio.wait_for(s.send_message(email_msg), timeout=20)
            log.info("email_sent_ok")

    except Exception as e:
        log.error("email_send_failed", err=repr(e))
        raise
