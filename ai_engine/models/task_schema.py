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

class TestCaseItem(BaseModel):
    input: str
    output: str

class TaskResponse(BaseModel):
    id: str
    domain: str
    difficulty: str
    type: str
    title: str
    problem: str
    starter_code: str
    expected_output: str
    test_cases: List[TestCaseItem]
    hints: List[str]
    solution: str
    explanation: str

class TaskWrapperResponse(BaseModel):
    success: bool
    raw_output: str
    parsed: Optional[dict] = None
    final_task: TaskResponse
