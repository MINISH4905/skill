import json
import logging
from typing import List
import os

logger = logging.getLogger("SkillForge-DB")

DATABASE_FILE = "storage/tasks.json"

class MockDBService:
    """
    Simulates Django DB interaction for Level table.
    Ensures tasks.json is always valid.
    """
    def __init__(self):
        if not os.path.exists("storage"):
            os.makedirs("storage")
        if not os.path.exists(DATABASE_FILE) or os.path.getsize(DATABASE_FILE) == 0:
            with open(DATABASE_FILE, "w") as f:
                json.dump([{"content_hash": "seed", "season_id": 0, "level": 0}], f)

    async def is_duplicate(self, content_hash: str, season_id: int) -> bool:
        tasks = self._load_tasks()
        return any(t.get("content_hash") == content_hash and t.get("season_id") == season_id for t in tasks)

    async def save_task(self, task_data: dict):
        tasks = self._load_tasks()
        tasks.append(task_data)
        with open(DATABASE_FILE, "w") as f:
            json.dump(tasks, f, indent=4)

    def _load_tasks(self) -> List[dict]:
        try:
            if not os.path.exists(DATABASE_FILE) or os.path.getsize(DATABASE_FILE) == 0:
                return []
            with open(DATABASE_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Database file '{DATABASE_FILE}' corrupted or empty. Self-healing...")
            return []

db_service = MockDBService()
