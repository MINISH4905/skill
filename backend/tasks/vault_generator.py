import os
import random
import json

DOMAINS = ["finance", "e-commerce", "gaming", "logging", "social_media", "inventory", "weather", "iot", "health", "education"]

TIERS = {
    "beginner": (10, 29),
    "elementary": (30, 49),
    "intermediate": (50, 69),
    "advanced": (70, 89),
    "expert": (90, 100)
}

def generate_task_vault():
    vault = {tier: [] for tier in TIERS}
    
    for tier, (min_diff, max_diff) in TIERS.items():
        for i in range(1, 101):
            domain = random.choice(DOMAINS)
            difficulty = min_diff + int(((i-1)/99) * (max_diff - min_diff))
            
            # Template selection based on tier
            if tier == "beginner":
                task = {
                    "title": f"Basic {domain.replace('_',' ').title()} Fix #{i}",
                    "description": f"Correct the {domain} calculation logic in this simple function.",
                    "starter_code": f"def calculate_{domain}_metric(n):\n    # TODO: Double the value\n    return n + 2",
                    "test_cases": [{"input": 5, "output": 10}],
                    "difficulty_score": difficulty,
                    "domain": domain
                }
            elif tier == "elementary":
                task = {
                    "title": f"Enhanced {domain.replace('_',' ').title()} Logic #{i}",
                    "description": f"Process the {domain} data list but ignore negative values.",
                    "starter_code": f"def filter_{domain}_entries(data):\n    # BUG: Including negatives\n    return [x for x in data]",
                    "test_cases": [{"input": [10, -5, 20], "output": [10, 20]}],
                    "difficulty_score": difficulty,
                    "domain": domain
                }
            elif tier == "intermediate":
                task = {
                    "title": f"Intermediate {domain.replace('_',' ').title()} Processing #{i}",
                    "description": f"Deduplicate the {domain} records while maintaining original order.",
                    "starter_code": f"def process_{domain}_records(records):\n    # BUG: Using set loses order\n    return list(set(records))",
                    "test_cases": [{"input": [1, 2, 2, 3, 1], "output": [1, 2, 3]}],
                    "difficulty_score": difficulty,
                    "domain": domain
                }
            elif tier == "advanced":
                task = {
                    "title": f"Advanced {domain.replace('_',' ').title()} Algorithm #{i}",
                    "description": f"Implement a recursive {domain} calculation with memoization.",
                    "starter_code": f"memo = {{}}\ndef compute_{domain}_recursive(n):\n    # BUG: Missing base case or memo check\n    if n == 0: return 0\n    return n + compute_{domain}_recursive(n-1)",
                    "test_cases": [{"input": 5, "output": 15}],
                    "difficulty_score": difficulty,
                    "domain": domain
                }
            else: # Expert
                task = {
                    "title": f"Expert {domain.replace('_',' ').title()} Optimization #{i}",
                    "description": f"Optimize the {domain} data structure with double-buffered locking.",
                    "starter_code": f"import threading\nclass {domain.title()}Expert:\n    def __init__(self): self.val = 0\n    def update(self): self.val += 1 # BUG: Race condition",
                    "test_cases": [{"input": None, "output": None}],
                    "difficulty_score": difficulty,
                    "domain": domain
                }
            
            vault[tier].append(task)
            
    vault_file_content = f"VAULT = {repr(vault)}"
    with open('c:/nextgen/backend/tasks/task_vault.py', 'w') as f:
        f.write(vault_file_content)

if __name__ == "__main__":
    generate_task_vault()
