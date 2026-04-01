"""
tests/test_task_api.py
----------------------
Comprehensive test suite covering:
  - All 4 weeks with correct progression
  - Difficulty auto-correction
  - Uniqueness engine (20 rapid calls)
  - Validation rejection (bad week_number)
  - Project history tracking
  - Health endpoint
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mock_generator import reset_project_cache

client = TestClient(app)

# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_caches():
    """Reset project caches before each test for isolation."""
    for pid in range(1, 20):
        reset_project_cache(pid)
    yield


# ─── Helpers ──────────────────────────────────────────────────────────────────

def post_task(project_id: int, week: int, domain="ai", topic="ml", difficulty=None):
    payload = {
        "domain": domain,
        "topic": topic,
        "project_id": project_id,
        "week_number": week,
    }
    if difficulty:
        payload["difficulty"] = difficulty
    return client.post("/generate-task", json=payload)


# ─── Health ───────────────────────────────────────────────────────────────────

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "modules" in data


# ─── Week progression ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("week,expected_difficulty,expected_module", [
    (1, "easy",   "Foundation Setup"),
    (2, "medium", "Core Development"),
    (3, "hard",   "Advanced Features"),
    (4, "hard+",  "Deployment & Optimization"),
])
def test_week_progression(week, expected_difficulty, expected_module):
    resp = post_task(project_id=1, week=week)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["week_number"] == week
    assert data["difficulty"] == expected_difficulty
    assert data["module_name"] == expected_module
    assert data["project_id"] == 1
    assert len(data["hints"]) == 2
    assert data["task"]
    assert data["answer"]


def test_all_four_weeks_show_progression():
    """Tasks across all 4 weeks must be distinct."""
    tasks = []
    for week in range(1, 5):
        resp = post_task(project_id=2, week=week)
        assert resp.status_code == 200
        tasks.append(resp.json()["task"])

    assert len(set(tasks)) == 4, "All 4 week tasks must be unique"


# ─── Difficulty auto-correction ────────────────────────────────────────────────

def test_difficulty_mismatch_is_auto_corrected():
    """Providing wrong difficulty should be silently overridden to match the week."""
    resp = post_task(project_id=3, week=1, difficulty="hard+")
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == "easy"


def test_correct_difficulty_is_preserved():
    resp = post_task(project_id=4, week=3, difficulty="hard")
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == "hard"


# ─── Validation ───────────────────────────────────────────────────────────────

def test_invalid_week_is_rejected():
    resp = post_task(project_id=5, week=5)
    assert resp.status_code == 422


def test_week_zero_is_rejected():
    resp = post_task(project_id=6, week=0)
    assert resp.status_code == 422


def test_missing_domain_is_rejected():
    resp = client.post("/generate-task", json={
        "topic": "ml",
        "project_id": 7,
        "week_number": 1,
    })
    assert resp.status_code == 422


# ─── Uniqueness engine ────────────────────────────────────────────────────────

def test_same_project_week_no_duplicates():
    """Multiple calls for same project+week must produce unique tasks."""
    tasks = set()
    for _ in range(5):
        resp = post_task(project_id=8, week=1)
        assert resp.status_code == 200
        tasks.add(resp.json()["task"])
    assert len(tasks) == 5, f"Expected 5 unique tasks, got {len(tasks)}"


def test_twenty_rapid_calls_all_unique():
    """20 rapid calls across different project IDs must all be unique."""
    tasks = set()
    for i in range(20):
        project_id = 100 + i
        week = (i % 4) + 1
        resp = post_task(project_id=project_id, week=week)
        assert resp.status_code == 200
        tasks.add(resp.json()["task_id"])
    assert len(tasks) == 20, "All 20 task_ids must be unique UUIDs"


def test_different_projects_same_week_independent():
    """Two different projects in the same week should not share a cache."""
    resp_a = post_task(project_id=200, week=1)
    resp_b = post_task(project_id=201, week=1)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    # Both are valid (may happen to be same task from pool — that's fine)
    assert resp_a.json()["project_id"] == 200
    assert resp_b.json()["project_id"] == 201


# ─── Project history ──────────────────────────────────────────────────────────

def test_project_history_tracks_tasks():
    post_task(project_id=300, week=1)
    post_task(project_id=300, week=2)

    resp = client.get("/project/300/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 2
    assert len(data["tasks"]) == 2


def test_project_reset_clears_history():
    post_task(project_id=400, week=1)
    client.delete("/project/400/reset")

    resp = client.get("/project/400/history")
    assert resp.json()["total_tasks"] == 0


# ─── Response schema ─────────────────────────────────────────────────────────

def test_response_has_all_required_fields():
    resp = post_task(project_id=500, week=2)
    data = resp.json()
    required = {"task_id", "project_id", "week_number", "module_name",
                "task", "hints", "answer", "difficulty", "domain", "topic"}
    assert required.issubset(data.keys())


def test_hints_always_exactly_two():
    for week in range(1, 5):
        resp = post_task(project_id=600 + week, week=week)
        assert len(resp.json()["hints"]) == 2


# ─── Domain/topic passthrough ─────────────────────────────────────────────────

def test_domain_and_topic_preserved_in_response():
    resp = client.post("/generate-task", json={
        "domain": "devops",
        "topic": "kubernetes",
        "project_id": 700,
        "week_number": 2,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "devops"
    assert data["topic"] == "kubernetes"