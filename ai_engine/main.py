import logging
from fastapi import FastAPI
from routers import task_router

# Setup Basic Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GSDS-AI-ENGINE")

app = FastAPI(
    title="GSDS AI Engine",
    description="FastAPI LLM integration for Gamified Skill Detection System",
    version="1.1.0"
)

app.include_router(task_router.router)

@app.on_event("startup")
async def startup_event():
    logger.info("GSDS AI Engine is online and ready for inference.")

@app.get("/")
@app.get("/api/v1/health")
def health_check():
    """
    Service health check for microservice monitoring.
    """
    return {
        "status": "online",
        "service": "GSDS AI Engine",
        "version": "1.1.0",
        "engine": "flan-t5-small"
    }
