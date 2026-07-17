from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api import suppliers, analyses, stream
from backend.api import scheduler as scheduler_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.scheduler.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="FactoryPulse AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(suppliers.router)
app.include_router(analyses.router)
app.include_router(stream.router)
app.include_router(scheduler_api.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env}
