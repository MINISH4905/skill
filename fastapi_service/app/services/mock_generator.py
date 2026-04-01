"""
mock_generator.py
-----------------
Project-aware task generator with:
  - Template-based task pools per domain/week
  - Uniqueness engine (in-memory cache keyed by project_id + week_number)
  - Fallback variation logic when template pool is exhausted
"""

import json
import uuid
import random
import hashlib
from pathlib import Path
from typing import Optional

from app.models.schemas import MODULE_NAMES, WEEK_DIFFICULTY, TaskResponse

# ─── Load templates ───────────────────────────────────────────────────────────
from pathlib import Path

_TEMPLATE_PATH = Path(__file__).parent.parent / "data" / "task_templates.json"
with _TEMPLATE_PATH.open() as f:
    TEMPLATES: dict = json.load(f)

# ─── Uniqueness cache ─────────────────────────────────────────────────────────
# Structure: { (project_id, week_number): set[task_fingerprint] }
_USED_TASKS: dict[tuple[int, int], set[str]] = {}

# ─── History for cross-week context ──────────────────────────────────────────
# Structure: { project_id: [list of completed task summaries] }
_PROJECT_HISTORY: dict[int, list[str]] = {}


def _fingerprint(task_text: str) -> str:
    """Create a compact identity hash for deduplication."""
    return hashlib.md5(task_text.strip().lower().encode()).hexdigest()


def _get_project_goal(domain: str) -> str:
    domain_data = TEMPLATES.get(domain)
    if domain_data:
        return domain_data.get("project_goal", f"Build a complete {domain} project")
    return f"Build a production-grade {domain} application"


def _get_template_pool(domain: str, week_number: int) -> list[dict]:
    week_key = f"week{week_number}"
    domain_data = TEMPLATES.get(domain, {})
    return domain_data.get(week_key, [])


def _generate_fallback_task(
    domain: str,
    topic: str,
    week_number: int,
    difficulty: str,
    module_name: str,
    project_goal: str,
    attempt: int,
) -> dict:
    """
    Produce a varied fallback task when all templates are exhausted.
    Uses rotating angles so repeated calls produce meaningfully different tasks.
    """
    angles = [
        "refactor",
        "document",
        "optimise",
        "test",
        "benchmark",
        "secure",
        "monitor",
        "automate",
        "review",
        "extend",
    ]
    angle = angles[attempt % len(angles)]

    task_text = (
        f"[{module_name}] {angle.capitalize()} the {topic} component of your {domain} project. "
        f"This is a {difficulty} task aligned with the goal: '{project_goal}'. "
        f"Focus on production-grade quality, edge-case handling, and clear documentation."
    )
    hints = [
        f"Break the {angle} work into small, testable increments rather than one large change.",
        f"Write a brief design doc before coding to clarify scope and acceptance criteria.",
    ]
    answer = (
        f"Identify the {topic} sub-component requiring {angle}. "
        f"Apply the change incrementally, write/update tests, and document the outcome in the project README."
    )
    return {"task": task_text, "hints": hints, "answer": answer}


def generate_mock_task(
    domain: str,
    topic: str,
    week_number: int,
    project_id: int,
    difficulty: Optional[str] = None,
) -> TaskResponse:
    """
    Generate a unique, project-aware task for the given context.
    """
    # Resolve difficulty and module from week
    resolved_difficulty = difficulty or WEEK_DIFFICULTY[week_number]
    module_name = MODULE_NAMES[week_number]
    project_goal = _get_project_goal(domain)

    # Initialise caches for this project/week combination
    cache_key = (project_id, week_number)
    if cache_key not in _USED_TASKS:
        _USED_TASKS[cache_key] = set()
    if project_id not in _PROJECT_HISTORY:
        _PROJECT_HISTORY[project_id] = []

    used_fingerprints = _USED_TASKS[cache_key]

    # ── Try templates first ───────────────────────────────────────────────────
    pool = _get_template_pool(domain, week_number)
    random.shuffle(pool)  # rotate order for variety

    selected: Optional[dict] = None
    for candidate in pool:
        fp = _fingerprint(candidate["task"])
        if fp not in used_fingerprints:
            selected = candidate
            used_fingerprints.add(fp)
            break

    # ── Fallback generation if templates exhausted ────────────────────────────
    if selected is None:
        attempt = len(used_fingerprints)
        max_retries = 15
        for i in range(attempt, attempt + max_retries):
            candidate = _generate_fallback_task(
                domain, topic, week_number, resolved_difficulty,
                module_name, project_goal, i
            )
            fp = _fingerprint(candidate["task"])
            if fp not in used_fingerprints:
                selected = candidate
                used_fingerprints.add(fp)
                break

    # Should never be None after fallback, but guard just in case
    if selected is None:
        raise RuntimeError(
            f"Could not generate a unique task for project={project_id}, week={week_number}"
        )

    # ── Record in project history ─────────────────────────────────────────────
    _PROJECT_HISTORY[project_id].append(
        f"Week {week_number} | {module_name}: {selected['task'][:80]}..."
    )

    # ── Build and return the response ─────────────────────────────────────────
    return TaskResponse(
        task_id=uuid.uuid4(),
        project_id=project_id,
        week_number=week_number,
        module_name=module_name,
        task=selected["task"],
        hints=selected["hints"][:2],   # enforce exactly 2 hints
        answer=selected["answer"],
        difficulty=resolved_difficulty,  # type: ignore[arg-type]
        domain=domain,
        topic=topic,
    )


def get_project_history(project_id: int) -> list[str]:
    """Return a summary of all tasks generated so far for a project."""
    return _PROJECT_HISTORY.get(project_id, [])


def reset_project_cache(project_id: int) -> None:
    """Clear task history for a project (useful in tests)."""
    for week in range(1, 5):
        _USED_TASKS.pop((project_id, week), None)
    _PROJECT_HISTORY.pop(project_id, None)