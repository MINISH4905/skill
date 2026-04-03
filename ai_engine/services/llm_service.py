import logging
import torch
import json
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from models.task_schema import TaskGenerateRequest, TaskResponse, TaskWrapperResponse
from utils.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

# Lazy initialization variables for native PyTorch implementation
flan_tokenizer = None
flan_model = None

def get_flan_t5():
    global flan_tokenizer, flan_model
    if flan_model is None:
        logger.warning("Initializing Lightweight Local FLAN-T5 (Small) for CPU Reliability...")
        
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        model_name = "google/flan-t5-small"
        
        flan_tokenizer = AutoTokenizer.from_pretrained(model_name)
        flan_model = AutoModelForSeq2SeqLM.from_pretrained(model_name, tie_word_embeddings=False).to(device)
        
        logger.warning(f"Successfully Loaded FLAN-T5-small on {device}")
    return flan_tokenizer, flan_model

FALLBACK_POOL = [
    {
        "title": "Inconsistent Batch Processing Results",
        "domain": "Systems",
        "difficulty": "Medium",
        "topic": "Async Logic",
        "scenario": "The batch processor API returns unpredictable nested dictionary lists when iterating through user telemetry nodes.",
        "given_code": "def process_telemetry(payload):\n    out = []\n    for i in range(len(payload)):\n        if 'node_id' in payload[i]:\n             out.append({'id': payload[i]['node_id'], 'v': payload[i].get('value')})\n    return out",
        "expected_output": "[{'id': 'ax', 'v': 99}, {'id': 'bx', 'v': 102}]",
        "constraints": ["Do not import libraries", "O(n) complexity"],
        "hints": ["Check for duplicate node IDs in the results", "A set or dict could track seen IDs efficiently"],
        "solution": "seen = set(); out = []\nfor item in payload:\n    id = item.get('node_id')\n    if id and id not in seen:\n        seen.add(id); out.append({'id': id, 'v': item.get('value', 0)})\nreturn out",
        "solution_approach": "Leverage a hash set to enforce uniqueness during a single pass iteration, reducing complexity from O(n^2) to O(n).",
        "evaluation_criteria": ["Correctness", "Performance"]
    },
    {
        "title": "Recursive Node Tree Corruption",
        "domain": "Algorithms",
        "difficulty": "Hard",
        "topic": "Recursion",
        "scenario": "A recursive tree walker hits a stack overflow on balanced trees of size 100.",
        "given_code": "def walk(node):\n    print(node.name)\n    for child in node.children:\n        walk(child)",
        "expected_output": "Root\nChild1",
        "constraints": ["Implement iteratively", "Memory limit 128MB"],
        "hints": ["Use an explicit stack instead of function recursion", "Verify the order of node visitation matches DFS"],
        "solution": "stack = [root]\nwhile stack:\n    curr = stack.pop()\n    print(curr.name)\n    stack.extend(curr.children)",
        "solution_approach": "Convert recursive depth-first search to an iterative approach using an explicit LIFO stack.",
        "evaluation_criteria": ["Depth check removed", "Stack usage correct"]
    },
    {
        "title": "Ad-Exchange Impression Skew",
        "domain": "Systems",
        "difficulty": "Hard",
        "topic": "Precision Math",
        "scenario": "The bidding engine is losing 0.1% of revenue due to floating point truncation in CPM calculations.",
        "given_code": "def calc_cost(bids):\n    total = 0.0\n    for price in bids:\n        total += float(price)\n    return total",
        "expected_output": "10.05",
        "constraints": ["Use Decimal for precision", "O(n) complexity"],
        "hints": ["Float math is not accurate for financial data", "The decimal module is built-in"],
        "solution": "from decimal import Decimal\ntotal = sum(Decimal(str(p)) for p in bids)",
        "solution_approach": "Switch from float to Decimal to ensure bit-accurate financial calculations.",
        "evaluation_criteria": ["Decimal used", "Rounding correct"]
    },
    {
        "title": "Satellite Telemetry Sync Failure",
        "domain": "Embedded",
        "difficulty": "Medium",
        "topic": "Timing",
        "scenario": "The ground station drops packets because the sequence clock isn't adjusted for relativistic drift.",
        "given_code": "def sync(t):\n    return t + 0.1",
        "expected_output": "1.1",
        "constraints": ["Apply time-dilation formula", "Zero-latency lock"],
        "hints": ["The adjustment is non-linear", "Check the drift constant in settings"],
        "solution": "def sync(t, v): return t * (1 - (v**2/c**2))**0.5",
        "solution_approach": "Apply Lorentz contraction factors to the synchronization pulse.",
        "evaluation_criteria": ["Physics correct"]
    }
]
def generate_ai_task(request: TaskGenerateRequest) -> dict:
    """
    Generates a technical task using AI with an internal 3-attempt retry loop.
    Ensures variety by enforcing context_seed and rejecting repetitive scenarios.
    """
    actual_domain = request.domain or request.skill or "General System"
    actual_topic = request.topic or request.language or "Core Logic"
    
    # Internal Retry Loop (Max 3 attempts)
    for attempt in range(1, 4):
        logger.info(f"AI Generation Attempt {attempt}/3 for Seed: {request.context_seed}")
        
        prompt = f"""You are an advanced coding challenge generator.
Goal: Generate a COMPLETELY UNIQUE technical task.

SYSTEM CONTEXT: {request.context_seed}
Domain: {actual_domain}
Topic: {actual_topic}
Difficulty: {request.difficulty}

STRICT RULES:
1. The scenario MUST strictly relate to the SYSTEM CONTEXT: {request.context_seed}.
2. SCENARIO VARIETY: Explicitly forbid generic 'logging pipelines' or 'telemetry trackers' unless requested.
3. Use DIFFERENT real-world entities, variables, and logic structures from previous turns.
4. Output ONLY valid JSON matching the format below.

OUTPUT FORMAT (STRICT JSON):
{{
  "title": "<String - Unique name>",
  "domain": "{actual_domain}",
  "difficulty": "{request.difficulty}",
  "topic": "{actual_topic}",
  "scenario": "<String - Detailed context centered on {request.context_seed}>",
  "given_code": "<String - Python code with logical bugs>",
  "expected_output": "<String>",
  "constraints": ["<String>", "<String>"],
  "hints": ["Hint 1", "Hint 2"],
  "solution": "<String - The fixed Python code>",
  "solution_approach": "<String - Expert perspective>",
  "evaluation_criteria": ["<String>", "<String>"]
}}
"""
        raw_output = ""
        try:
            tokenizer, model = get_flan_t5()
            device = next(model.parameters()).device
            inputs = tokenizer(prompt, return_tensors="pt", max_length=1000, truncation=True).to(device)
            
            outputs = model.generate(
                **inputs, 
                max_new_tokens=1000, # Lowered from 1500 for CPU optimization
                min_length=150,      
                do_sample=True,
                temperature=0.7,     # Lowered for more determinism
                num_beams=1,         # Greedy search (much faster than beam search)
                early_stopping=True,
            )
            raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Parse and Validate
            parsed_dict = parse_llm_json(raw_output)
            TaskResponse(**parsed_dict) # Schema check
            
            # Scenario Validation: Ensure context_seed wasn't ignored
            scenario_text = parsed_dict.get('scenario', '').lower()
            seed_words = request.context_seed.lower().split()
            if any(word in scenario_text for word in seed_words):
                logger.info(f"Successful Generation on Attempt {attempt}")
                return {
                    "success": True,
                    "raw_output": raw_output,
                    "parsed": parsed_dict,
                    "final_task": parsed_dict
                }
            else:
                logger.warning(f"Attempt {attempt} Rejected: Scenario ignored the context seed '{request.context_seed}'")
                
        except Exception as e:
            logger.error(f"Attempt {attempt} Failed: {str(e)}")
            raw_output = f"Trace: {str(e)}"

    # If all 3 attempts fail, resort to global fallback pool
    logger.warning("All 3 AI Generation attempts failed. Issuing Fallback.")
    import random
    final_task = random.choice(FALLBACK_POOL)
    return {
        "success": False,
        "raw_output": "MAX RETRIES EXCEEDED: AI Engine could not fulfill the uniqueness/schema constraints after 3 attempts.",
        "parsed": None,
        "final_task": final_task,
        "error": "Internal AI Reliability Failure"
    }
