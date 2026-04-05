import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger("GSDS-AI-ENGINE")

# Load model locally (shared with memory)
_model = None

def get_sentence_model():
    global _model
    if _model is None:
        logger.info("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def evaluate_theory_logic(user_ans: str, correct_ans: str, threshold: float = 0.75) -> dict:
    """
    Evaluates descriptive answers via semantic similarity.
    """
    if not user_ans.strip():
        return {"accuracy": 0.0, "similarity": 0.0, "is_correct": False, "feedback": "Answer is empty."}

    model = get_sentence_model()
    embeddings = model.encode([user_ans, correct_ans])
    sim_score = cosine_similarity(embeddings[0], embeddings[1])

    is_correct = sim_score >= threshold
    feedback = "Semantic match found." if is_correct else "Answer is semantically weak or incorrect."

    return {
        "accuracy": float(sim_score),
        "similarity": float(sim_score),
        "is_correct": is_correct,
        "feedback": feedback
    }
