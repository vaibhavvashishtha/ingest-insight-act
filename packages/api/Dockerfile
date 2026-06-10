FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY packages/core packages/core
COPY packages/etl packages/etl
COPY packages/insights packages/insights
COPY packages/api packages/api

RUN uv pip install --system -e packages/core -e packages/etl -e packages/insights -e packages/api

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
