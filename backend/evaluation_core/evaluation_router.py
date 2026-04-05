from .evaluators.code_evaluator import evaluate_code
from .evaluators.mcq_evaluator import evaluate_mcq
from .evaluators.theory_evaluator import evaluate_theory
from .utils.scoring import calculate_time_score, apply_difficulty_weight
from .utils.feedback import generate_feedback

def evaluate_answer(task_type: str, user_answer: str, correct_answer: str, metadata: dict) -> dict:
    """
    Routes task to the correct evaluator and combines accuracy + time score.
    """
    # 1. Evaluate Accuracy
    if task_type == 'code':
        # Code evaluation requires test cases from metadata
        test_cases = metadata.get('test_cases', [])
        result = evaluate_code(user_answer, test_cases)
        accuracy = result['accuracy']
    elif task_type == 'mcq':
        result = evaluate_mcq(user_answer, correct_answer)
        accuracy = result['accuracy']
    elif task_type == 'theory':
        result = evaluate_theory(user_answer, correct_answer)
        accuracy = result['accuracy']
    else:
        raise ValueError(f"Unknown task type: {task_type}")

    # 2. Calculate Time Score
    time_taken = metadata.get('time_taken', 0)
    expected_time = metadata.get('expected_time', 60) # Default 60s
    time_score = calculate_time_score(time_taken, expected_time)

    # 3. Combine Score
    final_score = (0.7 * accuracy) + (0.3 * time_score)

    # 4. Apply Tier-based Weighting
    tier = metadata.get('tier', 'beginner')
    weighted_score = apply_difficulty_weight(final_score, tier)

    # 5. Generate Feedback
    feedback = generate_feedback(task_type, accuracy)

    return {
        "accuracy_score": float(accuracy),
        "time_score": float(time_score),
        "final_raw_score": float(final_score),
        "final_score": float(weighted_score),
        "difficulty": difficulty,
        "is_correct": accuracy >= 0.7, # Standard threshold
        "feedback": feedback,
        "meta": result # Original raw evaluator data
    }

def final_evaluation(task_type, user_answer, correct_answer, metadata):
    """
    Main entry point for external API integration.
    """
    try:
        return evaluate_answer(task_type, user_answer, correct_answer, metadata)
    except Exception as e:
        return {
            "error": str(e),
            "is_correct": False,
            "final_score": 0.0,
            "feedback": f"Evaluation System Error: {str(e)}"
        }
