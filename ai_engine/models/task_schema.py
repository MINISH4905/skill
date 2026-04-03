from pydantic import BaseModel
from typing import List, Optional

class TaskGenerateRequest(BaseModel):
    domain: Optional[str] = None
    difficulty: str
    topic: Optional[str] = None
    context_seed: Optional[str] = "Standard"
    
    # Legacy GSDS compatibility
    skill: Optional[str] = None
    language: Optional[str] = None
    count: Optional[int] = 1

class TaskResponse(BaseModel):
    title: str
    domain: str
    difficulty: str
    topic: str
    scenario: str
    given_code: str
    expected_output: str
    constraints: List[str]
    hints: List[str]
    solution: str
    solution_approach: str
    evaluation_criteria: List[str]

class TaskWrapperResponse(BaseModel):
    success: bool
    raw_output: str
    parsed: Optional[dict] = None
    final_task: TaskResponse
