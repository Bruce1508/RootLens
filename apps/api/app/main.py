from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import evaluations, health, investigations, metadata, metrics
from app.core.config import Settings

settings = Settings()

app = FastAPI(title="RootLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluations.router)
app.include_router(health.router)
app.include_router(investigations.router)
app.include_router(metadata.router)
app.include_router(metrics.router)
