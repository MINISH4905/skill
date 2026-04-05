import json
import re

def parse_llm_json(raw_text: str) -> dict:
    """
    Extracts valid JSON from a raw LLM response.
    Includes retry logic/parsing strategies for markdown backticks or malformed strings.
    """
    try:
        # Easy case: perfect JSON
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass
        
    # Attempt to extract json from markdown ```json \n {...} \n ```
    match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    if not match:
        # Try finding the first { and the last }
        match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
    
    if match:
        try:
            # Clean possible markdown noise within the match
            clean_json = match.group(1).strip()
            
            # Strategy 2: Fix single quotes if they are used as delimiters
            # (risky but common in small model outputs)
            if "'" in clean_json and '"' not in clean_json:
                clean_json = clean_json.replace("'", '"')
            
            return json.loads(clean_json)
        except json.JSONDecodeError:
            pass
            
    # Final effort: try to find anything like {"title": ...}
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0).replace("'", '"'))
        except:
            pass
            
    raise ValueError("Failed to parse valid JSON from LLM response.")
