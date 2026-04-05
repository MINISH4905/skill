import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from tasks.models import Level, Season
from tasks.services import generate_task_for_level

def generate_intro_levels(count=5):
    season = Season.objects.filter(is_active=True).first()
    if not season:
        print("No active season found.")
        return

    levels = Level.objects.filter(season=season, task__isnull=True).order_by('level_number')[:count]
    print(f"Generating tasks for {len(levels)} levels in {season.name}...")

    for lvl in levels:
        try:
            task = generate_task_for_level(lvl)
            print(f"Level {lvl.level_number}: Success! Task: {task.title}")
        except Exception as e:
            print(f"Level {lvl.level_number}: Failed! Error: {e}")

if __name__ == "__main__":
    generate_intro_levels(10)
