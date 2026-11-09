from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import admin, auth, map, analytics, ingest, alerts, alert_records, assessments, cases, chat, vessels, reports, weather, sar, ocean, aisstream, gfw, environment, sources, triage, v1
from app.api.auth import require_viewer

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["Administration"])
viewer = [Depends(require_viewer)]
app.include_router(map.router, prefix=f"{settings.API_V1_PREFIX}/map", tags=["Map"], dependencies=viewer)
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}/analytics", tags=["Analytics"], dependencies=viewer)
app.include_router(ingest.router, prefix=f"{settings.API_V1_PREFIX}/ingest", tags=["Ingest"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alerts"], dependencies=viewer)
app.include_router(alert_records.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Alert lifecycle"])
app.include_router(assessments.router, prefix=f"{settings.API_V1_PREFIX}/alerts", tags=["Assessments"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Chat"])
app.include_router(vessels.router, prefix=f"{settings.API_V1_PREFIX}/vessels", tags=["Vessels"], dependencies=viewer)
app.include_router(reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["Reports"])
app.include_router(cases.router, prefix=f"{settings.API_V1_PREFIX}/cases", tags=["Cases"])
app.include_router(weather.router, prefix=f"{settings.API_V1_PREFIX}/weather", tags=["Weather"], dependencies=viewer)
app.include_router(sar.router, prefix=f"{settings.API_V1_PREFIX}/sar", tags=["SAR"])
app.include_router(ocean.router, prefix=f"{settings.API_V1_PREFIX}/ocean", tags=["Ocean"], dependencies=viewer)
app.include_router(aisstream.router, prefix=f"{settings.API_V1_PREFIX}/aisstream", tags=["AISStream"], dependencies=viewer)
app.include_router(gfw.router, prefix=f"{settings.API_V1_PREFIX}/gfw", tags=["Global Fishing Watch"], dependencies=viewer)
app.include_router(environment.router, prefix=f"{settings.API_V1_PREFIX}/environment", tags=["Environment"], dependencies=viewer)
app.include_router(sources.router, prefix=f"{settings.API_V1_PREFIX}/sources", tags=["Sources"])
app.include_router(triage.router, prefix=f"{settings.API_V1_PREFIX}/triage", tags=["Triage"], dependencies=viewer)
app.include_router(v1.router, prefix=settings.API_V1_PREFIX, tags=["V1 operations"])

@app.get("/")
async def root():
    return {
        "message": "SamudraSense API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
