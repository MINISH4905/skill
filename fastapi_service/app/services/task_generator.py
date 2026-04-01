"""
task_generator.py
-----------------
Orchestration layer that selects the appropriate backend:
  1. MockGenerator  – default, fast, template-based (no GPU needed)
  2. FLAN-T5        – optional, LLM-powered (enabled via USE_FLAN_T5=true env var)

Both backends honour the uniqueness and project-context contracts.
"""

import os
import uuid
import logging
from typing import Optional

from app.models.schemas import MODULE_NAMES, WEEK_DIFFICULTY, TaskResponse
from app.services.mock_generator import generate_mock_task

logger = logging.getLogger(__name__)

# ─── FLAN-T5 optional import ──────────────────────────────────────────────────
_FLAN_PIPELINE = None

def _load_flan_pipeline():
    """Lazy-load the FLAN-T5 pipeline only when USE_FLAN_T5=true."""
    global _FLAN_PIPELINE
    if _FLAN_PIPELINE is not None:
        return _FLAN_PIPELINE
    try:
        from transformers import pipeline as hf_pipeline
        logger.info("Loading FLAN-T5 model (this may take a moment)…")
        _FLAN_PIPELINE = hf_pipeline(
            "text2text-generation",
            model="google/flan-t5-base",
            max_new_tokens=512,
        )
        logger.info("FLAN-T5 loaded successfully.")
    except ImportError:
        logger.warning(
            "transformers library not installed. Falling back to mock generator."
        )
        _FLAN_PIPELINE = None
    return _FLAN_PIPELINE


def _build_flan_prompt(
    domain: str,
    topic: str,
    week_number: int,
    difficulty: str,
    module_name: str,
    project_goal: str,
) -> str:
    return (
        f"Generate a {difficulty} level project-based task for a {domain} project.\n"
        f"The project goal is: {project_goal}.\n"
        f"Current week: {week_number} ({module_name}).\n"
        f"Topic: {topic}.\n\n"
        f"The task must:\n"
        f"- contribute to the final project\n"
        f"- be unique\n"
        f"- match the difficulty level\n"
        f"- include exactly 2 hints\n"
        f"- include a clear answer\n\n"
        f"Format:\n"
        f"TASK: <task description>\n"
        f"HINT 1: <hint>\n"
        f"HINT 2: <hint>\n"
        f"ANSWER: <answer>"
    )


def _parse_flan_output(raw: str) -> dict:
    """Parse FLAN-T5 free-form output into structured task fields."""
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    task, hints, answer = "", [], ""
    for line in lines:
        if line.upper().startswith("TASK:"):
            task = line.split(":", 1)[1].strip()
        elif line.upper().startswith("HINT 1:") or line.upper().startswith("HINT1:"):
            hints.append(line.split(":", 1)[1].strip())
        elif line.upper().startswith("HINT 2:") or line.upper().startswith("HINT2:"):
            hints.append(line.split(":", 1)[1].strip())
        elif line.upper().startswith("ANSWER:"):
            answer = line.split(":", 1)[1].strip()

    # Fallback if parsing is incomplete
    if not task:
        task = raw[:200]
    if len(hints) < 2:
        hints = (hints + ["Review documentation.", "Test each step incrementally."])[:2]
    if not answer:
        answer = "Implement the task incrementally and validate with tests."

    return {"task": task, "hints": hints, "answer": answer}


def _generate_with_flan(
    domain: str,
    topic: str,
    week_number: int,
    project_id: int,
    difficulty: str,
) -> TaskResponse:
    """Generate a task using FLAN-T5. Falls back to mock on failure."""
    pipe = _load_flan_pipeline()
    if pipe is None:
        logger.warning("FLAN-T5 unavailable, falling back to mock generator.")
        return generate_mock_task(domain, topic, week_number, project_id, difficulty)

    module_name = MODULE_NAMES[week_number]
    project_goal = f"Build a production-grade {domain} {topic} application"

    prompt = _build_flan_prompt(
        domain, topic, week_number, difficulty, module_name, project_goal
    )

    try:
        result = pipe(prompt, max_new_tokens=512)[0]["generated_text"]
        parsed = _parse_flan_output(result)
    except Exception as exc:
        logger.error("FLAN-T5 generation failed: %s. Falling back to mock.", exc)
        return generate_mock_task(domain, topic, week_number, project_id, difficulty)

    return TaskResponse(
        task_id=uuid.uuid4(),
        project_id=project_id,
        week_number=week_number,
        module_name=module_name,
        task=parsed["task"],
        hints=parsed["hints"],
        answer=parsed["answer"],
        difficulty=difficulty,  # type: ignore[arg-type]
        domain=domain,
        topic=topic,
    )


# ─── Public interface ─────────────────────────────────────────────────────────

def generate_task(
    domain: str,
    topic: str,
    week_number: int,
    project_id: int,
    difficulty: Optional[str] = None,
) -> TaskResponse:
    """
    Primary entry point for task generation.

    Routing:
      - USE_FLAN_T5=true  → FLAN-T5 pipeline (with mock fallback)
      - default           → fast mock generator
    """
    resolved_difficulty = difficulty or WEEK_DIFFICULTY[week_number]

    use_flan = os.getenv("USE_FLAN_T5", "false").lower() == "true"
    if use_flan:
        logger.info("Using FLAN-T5 backend for task generation.")
        return _generate_with_flan(
            domain, topic, week_number, project_id, resolved_difficulty
        )

    logger.debug("Using mock generator backend.")
    return generate_mock_task(domain, topic, week_number, project_id, resolved_difficulty)