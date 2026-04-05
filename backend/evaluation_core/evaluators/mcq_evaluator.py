def evaluate_mcq(user_answer: str, correct_answer: str) -> dict:
    """
    Evaluates MCQ answers via case-insensitive string matching.
    """
    is_correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()
    return {
        "accuracy": 1.0 if is_correct else 0.0,
        "is_correct": is_correct,
        "feedback": "Correct Answer!" if is_correct else "Incorrect selection."
    }
