import json
import logging
import os
import re
import hashlib
import difflib
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

logger = logging.getLogger("SkillForge-Memory")

# Default under ai_engine/storage/
_STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
_DEFAULT_MEMORY = _STORAGE_DIR / "scenario_memory.json"
_MAX_ENTRIES = 4000
_MAX_COMPARE = 600  # compare new text against last N entries only (performance)


def _normalize(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"\s+", " ", t)
    return t.strip()


class MemoryService:
    """
    Persistent de-duplication: exact content hashes + fuzzy similarity (difflib).
    Avoids sklearn/TFIDF refit-on-every-call anti-pattern.
    """

    def __init__(self, memory_file: os.PathLike | str | None = None):
        self.memory_file = Path(memory_file) if memory_file else _DEFAULT_MEMORY
        self.scenarios: List[Dict[str, Any]] = []
        self._hashes: set[str] = set()
        self._lock = Lock()
        self._ensure_storage()
        self._load_memory()

    def _ensure_storage(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_file.exists():
            self.memory_file.write_text("[]", encoding="utf-8")

    def _load_memory(self) -> None:
        try:
            raw = self.memory_file.read_text(encoding="utf-8")
            self.scenarios = json.loads(raw) if raw.strip() else []
            self._hashes = {s.get("content_hash", "") for s in self.scenarios if s.get("content_hash")}
            logger.info("Loaded %s scenario fingerprints from %s", len(self.scenarios), self.memory_file)
        except Exception as e:
            logger.error("Error loading memory: %s", e)
            self.scenarios = []
            self._hashes = set()

    def _save_memory(self) -> None:
        try:
            data = self.scenarios[-_MAX_ENTRIES:]
            self.memory_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Error saving memory: %s", e)

    def content_fingerprint(self, title: str, description: str, starter_code: str) -> str:
        blob = f"{_normalize(title)}|{_normalize(description)}|{starter_code.strip()}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def is_scenario_unique(self, problem_text: str, threshold: float = 0.82) -> bool:
        """
        Returns False if fuzzy similarity to a recent stored problem exceeds threshold.
        """
        norm = _normalize(problem_text)
        if len(norm) < 12:
            return True
        recent = self.scenarios[-_MAX_COMPARE:]
        best = 0.0
        for s in recent:
            prev = s.get("problem_norm") or _normalize(s.get("problem", ""))
            if not prev:
                continue
            ratio = difflib.SequenceMatcher(a=norm, b=prev).ratio()
            if ratio > best:
                best = ratio
            if best >= threshold:
                logger.warning("Similarity %.3f >= %.3f — treat as duplicate.", best, threshold)
                return False
        return True

    def add_scenario(self, task_data: Dict[str, Any]) -> None:
        with self._lock:
            title = task_data.get("title", "")
            desc = task_data.get("description") or task_data.get("problem", "")
            starter = task_data.get("starter_code", "")
            ch = task_data.get("content_hash") or self.content_fingerprint(title, desc, starter)
            if ch in self._hashes:
                return
            prob_norm = _normalize(desc)
            entry = {
                "id": task_data.get("id"),
                "title": title,
                "problem": desc,
                "problem_norm": prob_norm,
                "domain": task_data.get("domain", ""),
                "content_hash": ch,
            }
            self.scenarios.append(entry)
            self._hashes.add(ch)
            self._save_memory()


memory_service = MemoryService()
