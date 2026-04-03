import requests
import logging

logger = logging.getLogger(__name__)

# Assuming the FastAPI service runs locally on port 8001
FASTAPI_URL = "http://127.0.0.1:8001"

def generate_task_via_ai(domain: str, difficulty: str, topic: str, context_seed: str = "Default") -> dict:
    """
    Communicates with the FastAPI AI Engine via HTTP POST.
    Includes robust timeout and connectivity error handling.
    """
    url = f"{FASTAPI_URL}/generate-task"
    payload = {
        "domain": domain,
        "difficulty": difficulty,
        "topic": topic,
        "context_seed": context_seed
    }
    
    try:
        # Increase to 120s to allow for 3 retry attempts of FLAN-T5 on CPU (approx 20s-30s per attempt)
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("[GSDS API] FastAPI Request Timed Out (120s)")
        return {"error": "AI Engine timeout", "final_task": None}
    except Exception as e:
        logger.error(f"[GSDS API] FastAPI Connection Error: {str(e)}")
        return {"error": str(e), "final_task": None}
