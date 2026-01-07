FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e .

COPY . /app

CMD ["python", "-m", "bot.app"]
