import logging
import time
from fastapi import APIRouter, HTTPException
from models.schema import TaskGenerateRequest, TaskResponse
from services.ai_service import ai_service
from services.hash_service import generate_task_hash

router = APIRouter(prefix="/api/v1/tasks", tags=["SkillForge Task Generation"])
logger = logging.getLogger("SkillForge-Router")

# ─────────────────────────────────────────────
# Tier-aware fallback pool (Massively Expanded)
# ─────────────────────────────────────────────
FALLBACK_TASKS = {
    "beginner": [
        {"title": "Fix Greeting", "description": "Fix the parameter usage.", "starter_code": "def greet(n): return 'Hi!'", "test_cases": [{"input": "A", "output": "Hello, A!"}], "difficulty_score": 10},
        {"title": "Square Fix", "description": "Fix the multiplier.", "starter_code": "def sq(n): return n", "test_cases": [{"input": 3, "output": 9}], "difficulty_score": 12},
        {"title": "Even Check", "description": "Fix the modulo.", "starter_code": "def is_e(n): return True", "test_cases": [{"input": 3, "output": False}], "difficulty_score": 15},
        {"title": "List First", "description": "Fix the index.", "starter_code": "def first(l): return l[1]", "test_cases": [{"input": [1,2], "output": 1}], "difficulty_score": 10},
        {"title": "String Upper", "description": "Fix the case.", "starter_code": "def up(s): return s.lower()", "test_cases": [{"input": "a", "output": "A"}], "difficulty_score": 12},
    ],
    "elementary": [
        {"title": "Positive Sum", "description": "Fix the filter.", "starter_code": "def sum_p(l): return sum(l)", "test_cases": [{"input": [1,-1], "output": 1}], "difficulty_score": 35},
        {"title": "Max Finder", "description": "Fix the initial value.", "starter_code": "def m(l): return 0", "test_cases": [{"input": [-5,-2], "output": -2}], "difficulty_score": 38},
        {"title": "Average Fix", "description": "Fix the division.", "starter_code": "def avg(l): return sum(l)", "test_cases": [{"input": [10,20], "output": 15}], "difficulty_score": 32},
    ],
    "intermediate": [
        {"title": "Deduplicate", "description": "Fix the order loss.", "starter_code": "def dedup(l): return list(set(l))", "test_cases": [{"input": [2,1,2], "output": [2,1]}], "difficulty_score": 55},
        {"title": "Dict Merge", "description": "Fix the key overwrite.", "starter_code": "def m(a,b): return a", "test_cases": [{"input": "({'a':1},{'b':2})", "output": "{'a':1,'b':2}"}], "difficulty_score": 52},
    ],
}


@router.post("/generate-task/", response_model=TaskResponse)
async def generate_task_endpoint(request: TaskGenerateRequest):
    """
    Generates a unique task for a specific season/level.
    - Uses domain and target_difficulty from Django.
    """
    start_time = time.time()
    logger.info(f"[Forge] AI Request | S{request.season_id} | L{request.level} | {request.domain} | Diff: {request.target_difficulty}")

    # 1. AI Generation
    # We pass target_difficulty and domain to nudge towards uniqueness
    task_data = await ai_service.generate_task(
        tier=request.tier,
        topic=request.topic,
        level=request.level,
        domain=request.domain,
        target_difficulty=request.target_difficulty,
        season_id=request.season_id,
        seed=request.seed,
        temperature=request.temperature,
    )

    if task_data:
        content_hash = generate_task_hash(
            task_data.get("title", ""), 
            task_data.get("description", ""), 
            task_data.get("starter_code", "")
        )
        
        # We don't check duplicate in FastAPI anymore; Django does it (to save on FastAPI complexity)
        # But we still return the hash and source for Django to use.
        
        elapsed = int((time.time() - start_time) * 1000)
        logger.info(f"[Forge] AI Task '{task_data.get('title')}' generated in {elapsed}ms")

        return {
            **task_data,
            "content_hash": content_hash,
            "generation_source": "ai_core",
        }

    # 2. Local Fallback (if AI fails)
    # This is a 'safety net' — Django also has a Vault fallback.
    tier_fallbacks = FALLBACK_TASKS.get(request.tier, FALLBACK_TASKS["beginner"])
    fallback = tier_fallbacks[request.level % len(tier_fallbacks)]
    
    title = f"{fallback['title']} (AI Fallback L{request.level})"
    content_hash = generate_task_hash(title, fallback["description"], fallback["starter_code"])
    
    logger.warning(f"[Forge] AI failed. Local Fallback used for level {request.level}")

    return {**fallback, "title": title, "content_hash": content_hash, "generation_source": "fallback"}

