from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Literal
from uuid import UUID

# ─── Week → Module mapping ───────────────────────────────────────────────────
MODULE_NAMES = {
    1: "Foundation Setup",
    2: "Core Development",
    3: "Advanced Features",
    4: "Deployment & Optimization",
}

# ─── Week → Auto difficulty ───────────────────────────────────────────────────
WEEK_DIFFICULTY = {
    1: "easy",
    2: "medium",
    3: "hard",
    4: "hard+",
}

DifficultyType = Literal["easy", "medium", "hard", "hard+"]


class TaskRequest(BaseModel):
    domain: str
    topic: str
    difficulty: Optional[DifficultyType] = None
    project_id: int
    week_number: int

    @field_validator("week_number")
    @classmethod
    def validate_week(cls, v: int) -> int:
        if v not in range(1, 5):
            raise ValueError("week_number must be between 1 and 4")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def auto_correct_difficulty(self) -> "TaskRequest":
        correct = WEEK_DIFFICULTY[self.week_number]
        if self.difficulty and self.difficulty != correct:
            # Auto-override with week-appropriate difficulty
            self.difficulty = correct
        elif not self.difficulty:
            self.difficulty = correct
        return self


class TaskResponse(BaseModel):
    task_id: UUID
    project_id: int
    week_number: int
    module_name: str
    task: str
    hints: list[str]
    answer: str
    difficulty: DifficultyType
    domain: str
    topic: str