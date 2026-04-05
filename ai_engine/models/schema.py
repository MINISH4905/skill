from pydantic import BaseModel, Field
from typing import List, Any, Literal, Optional

class TestCase(BaseModel):
    input: Any
    output: Any

class TaskGenerateRequest(BaseModel):
    level: int
    tier: Literal["beginner", "elementary", "intermediate", "advanced", "expert"]
    topic: str = "Python"
    domain: str = "dsa"
    target_difficulty: int = 50
    season_id: int = 1
    seed: Optional[int] = Field(default=None, description="Reproducible generation; omit for hash-based default")
    temperature: float = Field(default=0.85, ge=0.1, le=1.5, description="LLM flavor variation (templates stay valid)")

class TaskResponse(BaseModel):
    title: str
    description: str
    starter_code: str
    test_cases: List[TestCase]
    difficulty_score: int
    content_hash: str
    generation_source: str = "ai_core"
    hints: List[str] = []
    explanation: str = ""
    type: str = "code_complete"
    solution: str = ""
    domain: str = "dsa"
