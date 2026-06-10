FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY packages/core packages/core
COPY packages/etl packages/etl

RUN uv pip install --system -e packages/core -e packages/etl

CMD ["celery", "-A", "etl.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
