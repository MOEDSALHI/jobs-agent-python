from __future__ import annotations

import asyncio
from collections import defaultdict
from email.message import EmailMessage
from typing import List

import structlog
from aiosmtplib import SMTP
from aiosmtplib.errors import SMTPException
from jinja2 import Template

from .config import S
from .models import Job

log = structlog.get_logger()


def _format_date(job: Job) -> str:
    if not job.posted_at:
        return "Date non disponible"
    return job.posted_at.strftime("%d/%m/%Y")


def _format_company(job: Job) -> str:
    return job.company.strip() if job.company else "Entreprise non disponible"


def _format_location(job: Job) -> str:
    return job.location.strip() if job.location else "Localisation non disponible"


def _group_jobs_by_source(jobs: List[Job]) -> dict[str, List[Job]]:
    grouped: dict[str, List[Job]] = defaultdict(list)
    for job in jobs:
        grouped[job.source].append(job)

    # Tri interne par score décroissant
    for source in grouped:
        grouped[source] = sorted(grouped[source], key=lambda j: -j.score)

    return dict(sorted(grouped.items(), key=lambda item: item[0]))


TPL = Template(
    """
    <html>
    <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
      <h2 style="margin-bottom: 8px;">Offres Python du jour ({{ total }})</h2>
      <p style="margin-top: 0; color: #666;">
        Voici les nouvelles offres détectées, regroupées par job board.
      </p>

      {% for source, jobs in grouped_jobs.items() %}
        <h3 style="margin-top: 24px; margin-bottom: 8px; color: #0f172a;">
          {{ source|upper }} ({{ jobs|length }})
        </h3>

        <table cellpadding="8" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; margin-bottom: 16px;">
          <thead>
            <tr style="background-color: #f3f4f6; text-align: left;">
              <th>Titre</th>
              <th>Entreprise</th>
              <th>Lieu</th>
              <th>Date</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {% for j in jobs %}
              <tr style="border-bottom: 1px solid #e5e7eb;">
                <td>
                  <a href="{{ j.url }}" style="color: #2563eb; text-decoration: none;">
                    {{ j.title }}
                  </a>
                </td>
                <td>{{ j.company_display }}</td>
                <td>{{ j.location_display }}</td>
                <td>{{ j.date_display }}</td>
                <td>{{ "%.1f"|format(j.score) }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      {% endfor %}
    </body>
    </html>
    """
)


async def send_email(jobs: List[Job]) -> None:
    if not jobs:
        log.info("email_skip_empty")
        return

    enriched_jobs = []
    for job in jobs:
        enriched_jobs.append(
            {
                "title": job.title,
                "url": str(job.url),
                "source": job.source,
                "score": job.score,
                "company_display": _format_company(job),
                "location_display": _format_location(job),
                "date_display": _format_date(job),
            }
        )

    # Reconstruction en dict par source
    grouped_jobs: dict[str, List[dict]] = defaultdict(list)
    for job in enriched_jobs:
        grouped_jobs[job["source"]].append(job)

    grouped_jobs = dict(sorted(grouped_jobs.items(), key=lambda item: item[0]))
    for source in grouped_jobs:
        grouped_jobs[source] = sorted(grouped_jobs[source], key=lambda j: -j["score"])

    email_msg = EmailMessage()
    email_msg["From"] = S.MAIL_SMTP_USER
    email_msg["To"] = S.MAIL_TO
    email_msg["Subject"] = f"Offres Python du jour ({len(jobs)})"
    email_msg["Reply-To"] = S.MAIL_SMTP_USER

    html = TPL.render(grouped_jobs=grouped_jobs, total=len(jobs))
    email_msg.set_content("Votre client mail ne supporte pas la version HTML.")
    email_msg.add_alternative(html, subtype="html")

    host = S.MAIL_SMTP_HOST
    port = S.MAIL_SMTP_PORT

    use_tls = port == 465
    use_starttls = port == 587

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
            log.info("email_connected")

            if use_starttls:
                try:
                    await asyncio.wait_for(s.starttls(), timeout=20)
                    log.info("email_starttls_ok")
                except SMTPException as e:
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