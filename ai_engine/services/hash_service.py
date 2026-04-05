import hashlib
import json

def generate_task_hash(title: str, description: str, starter_code: str) -> str:
    """
    Combines title, description, and starter_code to generate a SHA256 hash.
    Used for de-duplication logic.
    """
    combined_content = f"{title.strip()}|{description.strip()}|{starter_code.strip()}"
    return hashlib.sha256(combined_content.encode('utf-8')).hexdigest()
