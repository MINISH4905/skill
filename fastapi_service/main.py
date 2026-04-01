"""
main.py
-------
FastAPI application for the Structured Learning Task Generator.

Routes:
  POST /generate-task        – generate a new project task
  GET  /project/{id}/history – view task history for a project
  DELETE /project/{id}/reset – clear task cache (dev/test utility)
  GET  /health               – liveness probe
"""

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import logging

from app.models.schemas import TaskRequest, TaskResponse, MODULE_NAMES
from app.services.task_generator import generate_task
from app.services.mock_generator import get_project_history, reset_project_cache

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Task Generator API starting up...")
    yield
    logger.info("👋 Task Generator API shutting down.")


app = FastAPI(
    title="Structured Learning Task Generator",
    description=(
        "Generates project-based learning tasks that progressively build toward "
        "a complete project goal across 4 weeks of structured modules."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.post(
    "/generate-task",
    response_model=TaskResponse,
    summary="Generate a learning task",
    description=(
        "Generate a unique, project-aligned learning task. "
        "Difficulty is automatically matched to the week number. "
        "Each call returns a distinct task — duplicates are internally prevented."
    ),
)
async def generate_task_endpoint(request: TaskRequest) -> TaskResponse:
    try:
        task = generate_task(
            domain=request.domain,
            topic=request.topic,
            week_number=request.week_number,
            project_id=request.project_id,
            difficulty=request.difficulty,
        )
        logger.info(
            "Task generated | project=%s week=%s domain=%s topic=%s difficulty=%s",
            request.project_id, request.week_number, request.domain,
            request.topic, task.difficulty,
        )
        return task
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during task generation: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/project/{project_id}/history",
    summary="Get task history for a project",
    description="Returns a list of previously generated tasks for the given project.",
)
async def project_history(project_id: int) -> dict:
    history = get_project_history(project_id)
    return {
        "project_id": project_id,
        "total_tasks": len(history),
        "tasks": history,
    }


@app.delete(
    "/project/{project_id}/reset",
    summary="Reset project task cache",
    description="Clears the uniqueness cache for a project. Useful in development and testing.",
)
async def reset_project(project_id: int) -> dict:
    reset_project_cache(project_id)
    logger.info("Project cache reset | project=%s", project_id)
    return {"message": f"Cache cleared for project {project_id}"}


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {
        "status": "ok",
        "modules": MODULE_NAMES,
    }