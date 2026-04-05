"""
Multi-method submission evaluation: exact test match, fuzzy similarity on text domains,
and coarse mistake classification for feedback.
"""
from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EvaluationResult:
    score: float  # 0-100
    confidence: float  # 0-1
    mistake_kind: str  # syntax | logic | concept | none | mixed
    feedback: str
    method: str  # exact | similarity | heuristic


def _classify_mistake(user_code: str, passed_ratio: float) -> str:
    code = user_code or ""
    if passed_ratio >= 1.0:
        return "none"
    try:
        ast.parse(code)
    except SyntaxError:
        return "syntax"
    if passed_ratio <= 0.0 and len(code.strip()) < 8:
        return "concept"
    if passed_ratio < 1.0:
        return "logic"
    return "mixed"


def _similarity_score(a: str, b: str) -> float:
    a, b = (a or "").strip(), (b or "").strip()
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(a=a.lower(), b=b.lower()).ratio()


def _sql_heuristic(user_code: str, expected: str) -> Tuple[float, bool]:
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").lower()).strip()

    u, e = norm(user_code), norm(expected)
    if not e:
        return 0.0, False
    ratio = _similarity_score(u, e)
    key_tokens = ["select", "from", "where"]
    has_sql = all(t in u for t in key_tokens) and "select" in u
    hit = ratio >= 0.75 or (has_sql and all(tok in u for tok in ["select", "from"]) and ratio >= 0.55)
    return (100.0 if hit else ratio * 100.0), hit


def _frontend_heuristic(user_code: str, expected: str) -> Tuple[float, bool]:
    u = (user_code or "").lower()
    needed = ["display", "flex", "justify-content", "align-items"]
    hit = all(n in u for n in needed)
    return (100.0 if hit else 40.0), hit


def evaluate_submission(
    *,
    domain: str,
    user_code: str,
    test_cases: List[Dict[str, Any]],
    passed_count: int,
    total: int,
) -> EvaluationResult:
    """Combines test pass ratio with domain heuristics and emits feedback."""
    dom = (domain or "dsa").lower()
    total = max(total, 1)
    ratio = passed_count / total

    if dom in ("sql",):
        exp = ""
        if test_cases:
            exp = str(test_cases[0].get("output", ""))
        score_h, hit = _sql_heuristic(user_code, exp)
        conf = 0.75 + 0.2 * (score_h / 100.0)
        mk = "concept" if not user_code.strip() else ("logic" if not hit else "none")
        fb = (
            "Query structure matches the expected pattern."
            if hit
            else "Review SELECT / WHERE / ORDER BY clauses and required filters."
        )
        return EvaluationResult(
            score=min(100.0, score_h),
            confidence=min(1.0, conf),
            mistake_kind=mk,
            feedback=fb,
            method="similarity",
        )

    if dom in ("frontend", "css", "ui"):
        exp = str(test_cases[0].get("output", "")) if test_cases else ""
        score_h, hit = _frontend_heuristic(user_code, exp)
        conf = 0.7 + 0.25 * (score_h / 100.0)
        mk = "concept" if len((user_code or "").strip()) < 10 else ("logic" if not hit else "none")
        fb = (
            "Flexbox centering looks correct."
            if hit
            else "Ensure the container uses flex with both main-axis and cross-axis alignment."
        )
        return EvaluationResult(
            score=min(100.0, score_h),
            confidence=min(1.0, conf),
            mistake_kind=mk,
            feedback=fb,
            method="heuristic",
        )

    # Code / DSA path: confidence from test pass ratio
    score = ratio * 100.0
    conf = 0.55 + 0.45 * ratio
    mk = _classify_mistake(user_code, ratio)
    if ratio >= 1.0:
        fb = "All tests passed. Nice work - solution is functionally correct."
    elif ratio >= 0.5:
        fb = "More than half of tests passed. Re-read failing cases and trace your algorithm on paper."
    else:
        fb = "Most tests failed. Verify edge cases, return values, and types against the specification."
    return EvaluationResult(
        score=round(score, 2),
        confidence=round(min(1.0, conf), 3),
        mistake_kind=mk,
        feedback=fb,
        method="exact",
    )
