from .evaluators.code_evaluator import evaluate_code
from .evaluators.mcq_evaluator import evaluate_mcq
from .utils.scoring import calculate_time_score, apply_difficulty_weight
from .utils.feedback import generate_feedback
import requests
import os

# Config from environment
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8001")

def evaluate_theory_via_ai(user_ans: str, correct_ans: str) -> dict:
    """
    Proxies semantic theory check to the AI Engine.
    """
    url = f"{FASTAPI_URL}/api/v1/evaluate/theory"
    try:
        response = requests.post(url, json={
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "threshold": 0.75
        }, timeout=10)
        if response.ok:
            return response.json().get("result", {"accuracy": 0})
        return {"accuracy": 0, "error": "AI Engine returned error status"}
    except Exception as e:
        return {"accuracy": 0, "error": f"Connection lost: {str(e)}"}

def evaluate_answer(task_type: str, user_answer: str, correct_answer: str, metadata: dict) -> dict:
    """
    Routes task and combines accuracy + time.
    """
    if task_type == 'code':
        result = evaluate_code(user_answer, metadata.get('test_cases', []))
    elif task_type == 'mcq':
        result = evaluate_mcq(user_answer, correct_answer)
    elif task_type == 'theory':
        result = evaluate_theory_via_ai(user_answer, correct_answer)
    else:
        raise ValueError(f"Unknown: {task_type}")

    accuracy = result.get('accuracy', 0)
    time_score = calculate_time_score(metadata.get('time_taken', 0), metadata.get('expected_time', 60))
    final_score = (0.7 * accuracy) + (0.3 * time_score)
    weighted_score = apply_difficulty_weight(final_score, metadata.get('difficulty', 'medium'))

    return {
        "accuracy_score": float(accuracy),
        "final_score": float(weighted_score),
        "is_correct": accuracy >= 0.7,
        "feedback": generate_feedback(task_type, accuracy),
        "meta": result
    }
