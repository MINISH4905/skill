import ast
import logging

logger = logging.getLogger("SkillForge-Validator")

class TaskValidator:
    @staticmethod
    def validate(task_data: dict, target_tier: str = None) -> tuple[bool, str]:
        """
        Validates task content:
        - Python syntax must be valid
        - Starter code must be non-empty
        - Title and description must be reasonably long
        - At least 1 test case (3 recommended)
        - Difficulty score must align with tier (if provided)
        """
        # 1. Title/Desc
        title = task_data.get('title', '')
        if len(title) < 10:
            return False, 'Validation Error: Title too short (min 10 chars).'
            
        description = task_data.get('description', '')
        if len(description) < 20:
            return False, 'Validation Error: Description too short (min 20 chars).'

        # 2. Syntax Check
        code = task_data.get('starter_code', '')
        if not code or len(code.strip()) < 10:
            return False, 'Validation Error: starter_code is empty or too short.'
            
        try:
            ast.parse(code)
        except SyntaxError as e:
            return False, f'Validation Error: Python Syntax Error: {str(e)}'

        # 3. Test Cases (Enforcing Checklist Requirement: 3-5)
        tests = task_data.get('test_cases', [])
        if not isinstance(tests, list) or len(tests) < 3:
            return False, 'Validation Error: Must have at least 3 test cases.'

        # 4. Tier Alignment (Optional but recommended)
        if target_tier:
            score = task_data.get('difficulty_score', 0)
            tier_ranges = {
                'beginner': (1, 35),
                'elementary': (25, 55),
                'intermediate': (45, 75),
                'advanced': (65, 95),
                'expert': (85, 100)
            }
            low, high = tier_ranges.get(target_tier, (0, 100))
            if not (low <= score <= high):
                logger.warning(f"Task score {score} slightly out of range for {target_tier}")

        return True, 'Task is valid.'
