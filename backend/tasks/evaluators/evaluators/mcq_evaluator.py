def evaluate_mcq(user_answer: str, correct_answer: str) -> dict:
    """
    Case-insensitive match for MCQ.
    """
    is_correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()
    return {"accuracy": 1.0 if is_correct else 0.0, "is_correct": is_correct}
