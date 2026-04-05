"""
Seed-based, domain-aware task shells. Ensures valid Python, 3+ test cases, and reproducibility.
Narrative variation comes from industry/context slots + optional LLM flavor text.
"""
from __future__ import annotations

import hashlib
import random
import textwrap
from typing import Any, Dict, List


INDUSTRIES = [
    "FinTech payments",
    "Healthcare records",
    "Logistics routing",
    "E-commerce catalog",
    "Education LMS",
    "Gaming leaderboards",
    "Travel bookings",
    "IoT sensor streams",
]

CONTEXTS = [
    "A production incident report flagged edge cases.",
    "Your team needs this for the next sprint demo.",
    "Scale matters: keep solutions O(n) where possible.",
]


def _seed_from_parts(seed: int | None, level: int, season_id: int, domain: str) -> random.Random:
    if seed is not None:
        return random.Random(seed)
    h = hashlib.sha256(f"{season_id}|{level}|{domain.lower()}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _tier_to_band(tier: str) -> str:
    t = tier.lower()
    if t in ("beginner", "elementary"):
        return "easy"
    if t in ("intermediate",):
        return "medium"
    return "hard"


def _clamp_score(target_difficulty: int, tier: str) -> int:
    lo, hi = {
        "beginner": (5, 40),
        "intermediate": (40, 70),
        "expert": (70, 100),
    }.get(tier.lower(), (10, 90))
    return max(lo, min(hi, int(target_difficulty)))


def _make_test_cases(inputs: List[Any], outputs: List[Any]) -> List[Dict[str, Any]]:
    return [{"input": a, "output": b} for a, b in zip(inputs, outputs)]


def _inject_bug(code: str, rng: random.Random) -> str:
    """Injects 1-2 common logic or syntax bugs into correct code."""
    lines = code.split('\n')
    # Focus on lines with operations
    target_lines = [i for i, line in enumerate(lines) if any(op in line for op in ['+', '-', '*', '/', '==', '>', '<', '=', 'return'])]
    
    if not target_lines: return code
    
    idx = rng.choice(target_lines)
    line = lines[idx]
    
    bug_type = rng.choice(['op', 'bounds', 'bool'])
    if bug_type == 'op':
        if '+' in line: line = line.replace('+', '-')
        elif '-' in line: line = line.replace('-', '+')
        elif '*' in line: line = line.replace('*', '/')
        elif '==' in line: line = line.replace('==', '!=')
    elif bug_type == 'bounds':
        if '<' in line: line = line.replace('<', '<=')
        elif '>' in line: line = line.replace('>', '>=')
    elif bug_type == 'bool':
        if 'True' in line: line = line.replace('True', 'False')
        elif 'False' in line: line = line.replace('False', 'True')
        
    lines[idx] = line
    return '\n'.join(lines)


# ═══════════════════════════════════════════════
# DSA DOMAIN: ALGORITHMS & EFFICIENCY
# ═══════════════════════════════════════════════

def generate_dsa_task(rng: random.Random, tier: str, target_difficulty: int) -> Dict[str, Any]:
    band = _tier_to_band(tier)
    industry = rng.choice(INDUSTRIES)
    difficulty_score = _clamp_score(target_difficulty, tier)

    if band == "easy":
        # Summing elements
        n = rng.randint(3, 10)
        title = f"{industry}: Linear Accumulator"
        desc = "Return the sum of all elements in the list `nums`. If the list is empty, return 0."
        starter = "def list_sum(nums):\n    return 0"
        solution = "def list_sum(nums):\n    return sum(nums) if nums else 0"
        tests = _make_test_cases([([1, 2, 3],), ([],), ([-5, 5, 10],)], [6, 0, 10])
    elif band == "medium":
        # Binary Search / Sorting
        title = f"{industry}: Value Search"
        desc = "Given a sorted list `nums`, return the index of `target`. Return -1 if not found."
        starter = "def find_index(nums, target):\n    return -1"
        solution = "def find_index(nums, target):\n    try: return nums.index(target)\n    except: return -1"
        tests = _make_test_cases([([1, 3, 5], 3), ([1, 3, 5], 6), ([], 1)], [1, -1, -1])
    else:
        # Complex algorithms
        title = f"{industry}: Optimization Quest"
        desc = "Find the maximum subarray sum (Kadane's algorithm). Input is a list of integers."
        starter = "def max_subarray(nums):\n    return 0"
        solution = """def max_subarray(nums):
    if not nums: return 0
    max_so_far = current_max = nums[0]
    for x in nums[1:]:
        current_max = max(x, current_max + x)
        max_so_far = max(max_so_far, current_max)
    return max_so_far"""
        tests = _make_test_cases([([-2, 1, -3, 4, -1, 2],), ([1, 2, 3],), ([-1],)], [6, 6, -1])

    typ = rng.choice(["code_complete", "optimization"])
    return {
        "title": title,
        "description": desc,
        "starter_code": starter,
        "test_cases": tests,
        "difficulty_score": difficulty_score,
        "hints": ["Focus on edge cases like empty lists."],
        "explanation": f"Designed for {industry} core logic.",
        "type": typ,
        "solution": solution,
    }


# ═══════════════════════════════════════════════
# BACKEND DOMAIN: DATA PROCESSING & VALIDATION
# ═══════════════════════════════════════════════

def generate_backend_task(rng: random.Random, tier: str, target_difficulty: int) -> Dict[str, Any]:
    industry = rng.choice(INDUSTRIES)
    difficulty_score = _clamp_score(target_difficulty, tier)

    if _tier_to_band(tier) == "easy":
        title = f"{industry}: Status Mapper"
        desc = "Map list of integers `codes` to statuses: 200 -> 'OK', 404 -> 'NOT_FOUND', others -> 'UNKNOWN'."
        starter = "def get_statuses(codes):\n    return []"
        solution = """def get_statuses(codes):
    mapping = {200: 'OK', 404: 'NOT_FOUND'}
    return [mapping.get(c, 'UNKNOWN') for c in codes]"""
        tests = _make_test_cases([([200, 404, 500],), ([],), ([404],)], [['OK', 'NOT_FOUND', 'UNKNOWN'], [], ['NOT_FOUND']])
    else:
        title = f"{industry}: JSON Filter"
        desc = "Given a list of dicts `records` (with key 'price'), return a list of prices for records where price > 50."
        starter = "def filter_prices(records):\n    return []"
        solution = "def filter_prices(records):\n    return [r['price'] for r in records if r.get('price', 0) > 50]"
        tests = _make_test_cases(
            [([{'price': 20}, {'price': 100}, {'price': 60}],), ([],)],
            [[100, 60], []]
        )

    return {
        "title": title, "description": desc, "starter_code": starter, "test_cases": tests,
        "difficulty_score": difficulty_score, "hints": ["Dict.get() is safer than direct access."],
        "explanation": f"Standard backend data transformation for {industry}.",
        "type": "code_complete", "solution": solution,
    }


# ═══════════════════════════════════════════════
# DEBUGGING DOMAIN: BUG FIXING & REFACTORING
# ═══════════════════════════════════════════════

def generate_debugging_task(rng: random.Random, tier: str, target_difficulty: int) -> Dict[str, Any]:
    industry = rng.choice(INDUSTRIES)
    difficulty_score = _clamp_score(target_difficulty, tier)
    
    # Base logic (valid code)
    title = f"{industry}: Bug Hunt"
    solution = """def validate_user(username, age):
    if len(username) < 3 or age < 18:
        return False
    return True"""
    
    # Broken starter
    starter = _inject_bug(solution, rng)
    
    desc = f"Something is wrong in {industry}'s validation logic. The function `validate_user` should return `True` ONLY if username is at least 3 chars AND age is at least 18."
    tests = _make_test_cases([("ab", 20), ("abc", 17), ("abc", 18)], [False, False, True])

    return {
        "title": title, "description": desc, "starter_code": starter, "test_cases": tests,
        "difficulty_score": difficulty_score, "hints": ["Check logical operators and boundaries."],
        "explanation": "Debugging common logical errors in production logic.",
        "type": "bug_fix", "solution": solution,
    }

# ═══════════════════════════════════════════════
# FRONTEND DOMAIN: CSS & UI LAYOUT
# ═══════════════════════════════════════════════

def generate_frontend_task(rng: random.Random, tier: str, target_difficulty: int) -> Dict[str, Any]:
    industry = rng.choice(INDUSTRIES)
    difficulty_score = _clamp_score(target_difficulty, tier)
    
    if rng.random() > 0.5:
        title = f"{industry}: Flexbox Layout"
        desc = "Add CSS properties to `.container` to display items in a row and center them horizontally."
        starter = ".container {\n    display: block;\n}"
        solution = ".container {\n    display: flex;\n    justify-content: center;\n}"
        search_terms = ["display: flex", "justify-content: center"]
    else:
        title = f"{industry}: Grid Area"
        desc = "Add CSS to `.grid-wrapper` to create a 3-column grid with a 10px gap."
        starter = ".grid-wrapper {\n    display: block;\n}"
        solution = ".grid-wrapper {\n    display: grid;\n    grid-template-columns: repeat(3, 1fr);\n    gap: 10px;\n}"
        search_terms = ["display: grid", "grid-template-columns", "gap: 10px"]

    tests = _make_test_cases(["dummy"], [search_terms]) # Internal evaluator handles this

    return {
        "title": title, "description": desc, "starter_code": starter, "test_cases": tests,
        "difficulty_score": difficulty_score, "hints": ["Use modern CSS layouts."],
        "explanation": f"Responsive layout for {industry} dashboard.",
        "type": "code_complete", "solution": solution,
    }

# ═══════════════════════════════════════════════
# SQL DOMAIN: QUERIES & SCHEMAS
# ═══════════════════════════════════════════════

def generate_sql_task(rng: random.Random, tier: str, target_difficulty: int) -> Dict[str, Any]:
    industry = rng.choice(INDUSTRIES)
    difficulty_score = _clamp_score(target_difficulty, tier)
    
    if _tier_to_band(tier) == "easy":
        title = f"{industry}: Basic Filter"
        desc = "Select all columns from `users` where `active` is 1."
        solution = "SELECT * FROM users WHERE active = 1"
    else:
        title = f"{industry}: Join Query"
        desc = "Join `users` (u) and `orders` (o) on `u.id = o.user_id`. Select `u.username` and `o.amount` where `o.amount` > 100."
        solution = "SELECT u.username, o.amount FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 100"

    starter = "-- Write your SQL query here\nSELECT"
    tests = _make_test_cases(["sql"], [solution])

    return {
        "title": title, "description": desc, "starter_code": starter, "test_cases": tests,
        "difficulty_score": difficulty_score, "hints": ["Follow SQL standard syntax."],
        "explanation": f"Database management for {industry}.",
        "type": "code_complete", "solution": solution,
    }


def build_task(
    domain: str,
    tier: str,
    level: int,
    season_id: int,
    target_difficulty: int,
    seed: int | None,
) -> Dict[str, Any]:
    rng = _seed_from_parts(seed, level, season_id, domain)
    d = domain.lower().strip()
    
    if d == "sql":
        return generate_sql_task(rng, tier, target_difficulty)
    elif d == "frontend":
        return generate_frontend_task(rng, tier, target_difficulty)
    elif d == "backend":
        return generate_backend_task(rng, tier, target_difficulty)
    elif d == "debugging":
        return generate_debugging_task(rng, tier, target_difficulty)
    else:
        # DSA/Default
        return generate_dsa_task(rng, tier, target_difficulty)
