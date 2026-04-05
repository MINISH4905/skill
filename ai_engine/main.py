from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import task as task_generator_router

_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "ai_engine.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("SkillForge-AI-Engine")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Models will now load lazily to prevent startup timeouts
    logger.info("SkillForge AI Engine Online (Lazy Loading Enabled)")
    yield
    # Clean up can happen here if needed

app = FastAPI(
    title="SkillForge AI Engine",
    description="High-performance, seasonal AI task generator",
    version="2.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unified routers
app.include_router(task_generator_router.router)


@app.get("/")
@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    """
    Service health check for microservice monitoring.
    """
    return {
        "status": "online",
        "service": "SkillForge AI Engine",
        "version": "2.5.0",
        "engine": "template+optional-flan-t5",
        "models_loaded": True,
    }
