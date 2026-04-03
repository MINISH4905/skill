from fastapi import APIRouter, HTTPException, Body
from models.task_schema import TaskGenerateRequest, TaskWrapperResponse
from services.llm_service import generate_ai_task

router = APIRouter(
    tags=["Task Generation"]
)

@router.post("/generate-task", response_model=TaskWrapperResponse)
@router.post("/api/v1/tasks/generate", response_model=TaskWrapperResponse)
def generate_task(request: TaskGenerateRequest = Body(...)):
    """
    Generates a task using AI based on provided domain, difficulty, and topic.
    Returns wrapper JSON envelope with raw outputs safely bound.
    """
    try:
        task_data = generate_ai_task(request)
        return task_data
    except ValueError as e:
        # Pydantic or Schema failure
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # General LLM or System failure
        raise HTTPException(status_code=500, detail=f"AI Engine Error: {str(e)}")
