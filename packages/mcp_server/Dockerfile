FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY packages/core packages/core
COPY packages/etl packages/etl
COPY packages/insights packages/insights
COPY packages/mcp_server packages/mcp_server

RUN uv pip install --system -e packages/core -e packages/etl -e packages/insights -e packages/mcp_server

CMD ["python", "-m", "mcp_server.main"]
