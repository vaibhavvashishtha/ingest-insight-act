from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import campaigns, dev, ingestion, insights, query, reports, sources

app = FastAPI(
    title="ingest-insight-act API",
    version="0.1.0",
    description="Multi-tenant marketing ETL, insights, and actions platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
