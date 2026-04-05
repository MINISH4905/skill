import logging
from django.db import transaction
from .models import Level, Task

# logger = logging.getLogger("SkillForge-Stabilizer")


def compute_ideal_difficulty(level_number: int) -> int:
    """
    Strict monotonic difficulty progression (1-100).
    L1: 10, L20: 29 (Beginner)
    L21: 30, L40: 49 (Elementary)
    L41: 50, L60: 69 (Intermediate)
    L61: 70, L80: 89 (Advanced)
    L81: 90, L100: 100 (Expert)
    """
    tiers = [
        (1, 20, 10, 29),    # Beginner
        (21, 40, 30, 49),   # Elementary
        (41, 60, 50, 69),   # Intermediate
        (61, 80, 70, 89),   # Advanced
        (81, 100, 90, 100), # Expert
    ]
    for low, high, d_low, d_high in tiers:
        if low <= level_number <= high:
            progress = (level_number - low) / (high - low) if (high - low) > 0 else 0
            return int(d_low + progress * (d_high - d_low))
    return level_number


def stabilize_season_levels(season_id: int):
    """
    Ensures that L1 is truly easier than L100.
    Sorts all tasks by difficulty then re-maps them to levels in order.
    """
    with transaction.atomic():
        levels = list(Level.objects.filter(season_id=season_id).order_by('level_number'))
        tasks = list(Task.objects.filter(season_id=season_id))

        if not tasks:
            # logger.warning(f"[Stabilizer] No tasks found for Season {season_id}. Skipping.")
            return

        # Rank all tasks by score, then metadata (complexity)
        tasks.sort(key=lambda t: (t.difficulty_score, len(t.starter_code), t.id))

        # logger.info(f"[Stabilizer] Stabilizing {len(tasks)} tasks across {len(levels)} levels for Season {season_id}...")

        for i, level in enumerate(levels):
            if i < len(tasks):
                task = tasks[i]
                level.task = task

                # Update tier based on level range
                level_num = level.level_number
                if level_num <= 20:
                    level.tier = 'beginner'
                elif level_num <= 40:
                    level.tier = 'elementary'
                elif level_num <= 60:
                    level.tier = 'intermediate'
                elif level_num <= 80:
                    level.tier = 'advanced'
                else:
                    level.tier = 'expert'

                level.save()

        # FIX #3: removed duplicate logger.info line
        # logger.info(f"[Stabilizer] Level re-mapping complete for Season {season_id}.")
