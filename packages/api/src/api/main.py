from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.limits import limiter
from api.routers import campaigns, dev, ingestion, insights, query, reports, sources
from core.config import settings

app = FastAPI(
    title="ingest-insight-act API",
    version="0.1.0",
    description="Multi-tenant marketing ETL, insights, and actions platform",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Parse comma-separated origin list — strip whitespace, drop empties
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(dev.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
