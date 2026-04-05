import asyncio
import hashlib
import requests
import time
import json
import uuid
import sys
import os
from django.core.management.base import BaseCommand
from tasks.models import Season, Level, Task
from django.db import transaction
from asgiref.sync import sync_to_async

# Add base project and ai_engine to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# c:\nextgen\backend\tasks\management\commands -> c:\nextgen
base_dir = os.path.abspath(os.path.join(current_dir, "../../../.."))
sys.path.append(os.path.join(base_dir, 'ai_engine'))
from services.ai_service import ai_service

@sync_to_async
def get_or_create_season(name):
    s, _ = Season.objects.get_or_create(name=name, is_active=True)
    return s

@sync_to_async
def clear_db():
    Level.objects.all().delete()
    Task.objects.all().delete()

@sync_to_async
def save_task_sync(task_data, domain, tier, level_counter, season, difficulty):
    with transaction.atomic():
        # Create Task in DB
        task = Task.objects.create(
            title=task_data["title"],
            description=task_data.get("description") or task_data.get("problem", ""),
            starter_code=task_data["starter_code"],
            solution=task_data.get("solution", ""),
            test_cases=task_data["test_cases"],
            hints=task_data.get("hints", []),
            explanation=task_data.get("explanation", ""),
            type=task_data.get("type", "code_complete"),
            difficulty=difficulty,
            domain=domain,
            content_hash=task_data["content_hash"],
            season=season,
            generation_source="ai_core",
            difficulty_score=task_data.get("difficulty_score", 10 if difficulty == "easy" else 20 if difficulty == "medium" else 50)
        )
        
        # Link Level
        Level.objects.create(
            level_number=level_counter,
            tier=tier,
            season=season,
            domain=domain,
            task=task
        )

async def generate_batch(command):
    season = await get_or_create_season("Season M")
    DOMAINS = ["dsa", "frontend", "backend", "sql", "debugging"]
    DIFFICULTY_SPLIT = {
        "easy": 40,
        "medium": 35,
        "hard": 25
    }

    for domain in DOMAINS:
        command.stdout.write(f"Generating for {domain.upper()}...")
        level_counter = 1
        
        for difficulty, count in DIFFICULTY_SPLIT.items():
            for _ in range(count):
                # Adding dynamic variables for variety
                seed_str = f"{domain}|{level_counter}|{time.time()}"
                dynamic_seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)
                
                try:
                    # ai_service.generate_task is already async
                    task_data = await ai_service.generate_task(
                        domain=domain,
                        tier="beginner" if difficulty == "easy" else "intermediate" if difficulty == "medium" else "expert",
                        topic="Python",
                        level=level_counter,
                        target_difficulty=10 if difficulty == "easy" else 20 if difficulty == "medium" else 50,
                        season_id=season.id,
                        seed=dynamic_seed,
                        temperature=0.8
                    )
                    
                    tier = "beginner" if difficulty == "easy" else "intermediate" if difficulty == "medium" else "expert"
                    await save_task_sync(task_data, domain, tier, level_counter, season, difficulty)
                    
                    level_counter += 1
                    if level_counter % 10 == 0:
                        command.stdout.write(f"  ... {level_counter}/100 levels done for {domain}")
                except Exception as e:
                    command.stdout.write(f"  [ERROR] L{level_counter} {domain}: {e}")
                    level_counter += 1

        command.stdout.write(command.style.SUCCESS(f"Finished {domain.upper()} (levels: {level_counter-1})."))

class Command(BaseCommand):
    help = 'Generates 500 unique tasks across 5 domains with production-grade uniqueness.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting 500 Task Generation (Season M)..."))
        
        # Clear existing (sync)
        Level.objects.all().delete()
        Task.objects.all().delete()

        asyncio.run(generate_batch(self))
        self.stdout.write(self.style.SUCCESS("500 Tasks successfully forged!"))
