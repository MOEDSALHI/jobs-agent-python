FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tzdata \
      curl \
      libnss3 \
      libatk-bridge2.0-0 \
      libatk1.0-0 \
      libcups2 \
      libxkbcommon0 \
      libxcomposite1 \
      libxdamage1 \
      libxrandr2 \
      libgbm1 \
      libasound2 \
      libpangocairo-1.0-0 \
      libpango-1.0-0 \
      libcairo2 \
      libx11-6 \
      libxcb1 \
      libxext6 \
      libxfixes3 \
      libdrm2 \
      libglib2.0-0 \
      fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock /app/
RUN poetry install --only main --no-interaction --no-ansi

RUN python -m playwright install chromium

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]