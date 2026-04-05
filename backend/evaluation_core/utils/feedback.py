"""
Actionable feedback strings for evaluations (theory, code, MCQ).
"""


def generate_feedback(task_type: str, score: float, mistake_kind: str | None = None) -> str:
    """
    score: 0.0-1.0 normalized score for display layers that use ratios.
    """
    mk = (mistake_kind or "none").lower()
    if score >= 0.9:
        return "Strong work: your approach matches the expected behavior across checks."
    if score >= 0.75:
        base = "Good progress: most of the required behavior is present."
    elif score >= 0.5:
        base = "Partial match: tighten the missing cases before optimizing."
    else:
        base = "Significant gaps: re-read the prompt and validate assumptions with examples."

    if mk == "syntax":
        return base + " Start by fixing syntax/runtime errors, then re-run tests."
    if mk == "logic":
        return base + " Focus on the failing tests: trace inputs/outputs step-by-step."
    if mk == "concept":
        return base + " Revisit the core concept for this task type, then implement incrementally."
    return base


def detail_feedback_lines(
    *,
    passed: int,
    total: int,
    mistake_kind: str,
    confidence: float,
) -> list[str]:
    lines = [
        f"Tests passed: {passed}/{total}.",
        f"Primary issue category: {mistake_kind}.",
        f"Evaluator confidence: {confidence:.0%}.",
    ]
    return lines
