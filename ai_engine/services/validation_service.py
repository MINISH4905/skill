import ast
import logging
from typing import List, Dict, Any

logger = logging.getLogger("SkillForge-Validation")

class ValidationService:
    @staticmethod
    def validate_python_syntax(code: str) -> bool:
        """
        Validates the provided starter_code for proper Python syntax.
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.warning(f"Syntax validation failed: {str(e)}")
            return False

    @staticmethod
    def validate_difficulty_tier(tier: str, difficulty_score: int) -> bool:
        """
        Ensures the generated difficulty_score aligns with the requested tier.
        TIER RANGE:
        - beginner: 1-35
        - elementary: 25-55
        - intermediate: 45-75
        - advanced: 65-95
        - expert: 85-100
        """
        mapping = {
            "beginner": (1, 35),
            "elementary": (25, 55),
            "intermediate": (45, 75),
            "advanced": (65, 95),
            "expert": (85, 100)
        }
        low, high = mapping.get(tier, (0, 100))
        return low <= difficulty_score <= high

    @staticmethod
    def validate_test_cases(test_cases: List[Dict[str, Any]]) -> bool:
        """
        Ensures test cases are not empty and follow standard schema.
        """
        if not test_cases or len(test_cases) < 3:
            return False
        
        for case in test_cases:
            if "input" not in case or "output" not in case:
                return False
        
        return True

validation_service = ValidationService()
