import os
import json
from pathlib import Path
from django.conf import settings
import random
import time
import hashlib
import logging
from .models import Season, Level, Task, GenerationLog, UserProfile
from .difficulty_stabilizer import stabilize_season_levels, compute_ideal_difficulty
from .task_vault import VAULT
from .validators import TaskValidator

logger = logging.getLogger("SkillForge")

FASTAPI_URL = os.getenv("FASTAPI_TASKS_URL", "http://127.0.0.1:8001/api/v1/tasks")

SCENARIO_MEMORY_PATH = Path(settings.BASE_DIR) / "scenario_memory.json"

def _load_scenario_memory():
    if not SCENARIO_MEMORY_PATH.exists():
        return []
    try:
        return json.loads(SCENARIO_MEMORY_PATH.read_text(encoding="utf-8"))
    except:
        return []

def _save_scenario_memory(data):
    SCENARIO_MEMORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _is_scenario_duplicate(title, code):
    memory = _load_scenario_memory()
    h = hashlib.sha256(f"{title}|{code}".encode()).hexdigest()
    for entry in memory:
        if entry.get("hash") == h:
            return True
    return False

def _add_to_scenario_memory(title, code, domain, difficulty):
    memory = _load_scenario_memory()
    memory.append({
        "title": title,
        "hash": hashlib.sha256(f"{title}|{code}".encode()).hexdigest(),
        "domain": domain,
        "difficulty": difficulty,
        "timestamp": time.time()
    })
    _save_scenario_memory(memory[-5000:]) # Keep last 5000 global tasks


TIER_RANGES = {
    'beginner': (1, 20),
    'elementary': (21, 40),
    'intermediate': (41, 60),
    'advanced': (61, 80),
    'expert': (81, 100),
}

DOMAINS = ["dsa", "frontend", "backend", "sql", "debugging"]


def get_tier_for_level(level_number: int) -> str:
    for tier, (low, high) in TIER_RANGES.items():
        if low <= level_number <= high:
            return tier
    return 'beginner'


def get_domain_for_level(level_number: int) -> str:
    return DOMAINS[(level_number - 1) % len(DOMAINS)]


def get_active_season() -> Season:
    return Season.objects.filter(is_active=True).first()


def get_vault_task_for_level(level_number: int, season_id: int, tier: str) -> dict:
    pool = VAULT.get(tier, [])
    if not pool:
        return None
    # Monthly rotation: different season -> different offset
    index = ((level_number - 1) + (season_id * 7)) % len(pool)
    return pool[index]


# ─────────────────────────────────────────────
# FIX #1 + #2: AI health probe with cached result.
# Probe once per bulk run; skip all AI retries if offline.
# ─────────────────────────────────────────────
_ai_online = None  # None = unknown, True/False = cached probe result


def get_fastapi_base_url() -> str:
    """
    FASTAPI_TASKS_URL default: http://127.0.0.1:8001/api/v1/tasks
    -> base http://127.0.0.1:8001/api/v1 (health is /health under this prefix).
    """
    u = (FASTAPI_URL or "").rstrip("/")
    if u.endswith("/tasks"):
        return u[: -len("/tasks")]
    return u


def ai_engine_health_url() -> str:
    """
    Single canonical health URL — always .../api/v1/health, never .../api/v1/api/v1/health.
    """
    return f"{get_fastapi_base_url().rstrip('/')}/health"


def ensure_domain_levels(season: Season, domain: str) -> None:
    """Ensure levels 1–100 exist for this season + domain (repairs partial DBs)."""
    have = set(
        Level.objects.filter(season=season, domain=domain).values_list("level_number", flat=True)
    )
    missing = [i for i in range(1, 101) if i not in have]
    if not missing:
        return
    Level.objects.bulk_create(
        [
            Level(
                level_number=i,
                tier=get_tier_for_level(i),
                season=season,
                domain=domain,
            )
            for i in missing
        ]
    )


def probe_ai_engine_once(timeout: float = 5.0) -> bool:
    """Hit canonical health first; then origin fallbacks (no duplicated /api/v1 segments)."""
    primary = ai_engine_health_url()
    try:
        r = requests.get(primary, timeout=timeout)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    base = get_fastapi_base_url().rstrip("/")
    origin = base.split("/api/")[0].rstrip("/") if "/api/" in base else ""
    fallbacks = []
    if origin:
        fallbacks.extend([f"{origin}/health", f"{origin}/api/v1/health"])
    for url in fallbacks:
        if url == primary:
            continue
        try:
            if requests.get(url, timeout=timeout).status_code == 200:
                return True
        except Exception:
            continue
    return False


def wait_for_ai_engine(max_wait: float = 60.0, interval: float = 2.0) -> bool:
    """
    Retries until the AI engine responds (handles: Django started before Uvicorn, cold bind).
    """
    global _ai_online
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if probe_ai_engine_once(timeout=min(8.0, max(5.0, max_wait / 8))):
            _ai_online = True
            return True
        time.sleep(interval)
    _ai_online = False
    return False


def _probe_ai_health() -> bool:
    """Quick probe; caches result for bulk generation."""
    global _ai_online
    _ai_online = probe_ai_engine_once(timeout=3.0)
    return _ai_online


def generate_task_for_level(level: Level) -> Task:
    """
    Production-ready pipeline:
    1. Probe AI health (cached per bulk run)
    2. If AI online: try up to 5 retries with 30s timeout
    3. Validate & Deduplicate each attempt
    4. Fallback to Vault if AI fails or is offline
    """
    global _ai_online
    MAX_RETRIES = 5
    season = level.season
    tier = level.tier
    domain = level.domain or 'dsa'
    target_difficulty = compute_ideal_difficulty(level.level_number)

    start_total = time.time()

    # ── Step 1: Skip AI entirely if we already know it's offline ──
    if _ai_online is None:
        _probe_ai_health()

    if _ai_online:
        # ── Step 2: AI Loop ──
        for attempt in range(1, MAX_RETRIES + 1):
            attempt_start = time.time()
            try:
                # FIX: Add random seed and temperature for variety
                # If level generation is for a specific user, we could use user_id here.
                # Since this is often bulk or level-based, we use level + time + salt.
                dynamic_seed = int(hashlib.md5(f"{level.level_number}|{time.time()}".encode()).hexdigest(), 16) % (2**32)
                temp = 0.7 + (random.random() * 0.2) # 0.7 - 0.9

                payload = {
                    "level": level.level_number,
                    "tier": tier,
                    "topic": "Python",
                    "domain": domain,
                    "target_difficulty": target_difficulty,
                    "season_id": season.id,
                    "seed": dynamic_seed,
                    "temperature": temp
                }
                res = requests.post(f"{FASTAPI_URL}/generate-task/", json=payload, timeout=30)
                res.raise_for_status()
                data = res.json()

                is_valid, msg = TaskValidator.validate(data, tier)

                # Check global scenario memory (Hard Uniqueness)
                is_duplicate = _is_scenario_duplicate(data.get('title'), data.get('starter_code'))

                if is_valid and not is_duplicate:
                    _add_to_scenario_memory(data.get('title'), data.get('starter_code'), domain, tier)
                    
                    content_hash = hashlib.sha256(
                        f"{data.get('title','')}|{data.get('starter_code','')}|L{level.level_number}".encode()
                    ).hexdigest()[:64]

                    diff_map = {'beginner': 'easy', 'elementary': 'easy', 'intermediate': 'medium', 'advanced': 'hard', 'expert': 'hard'}
                    task = Task.objects.create(
                        title=f"{data.get('title')}",
                        description=data.get('description') or data.get('problem', ''),
                        starter_code=data.get('starter_code'),
                        solution=data.get('solution', '') or '',
                        hints=data.get('hints', []),
                        explanation=data.get('explanation', '') or '',
                        type=data.get('type', 'code_complete'),
                        difficulty=diff_map.get(tier, 'medium'),
                        test_cases=data.get('test_cases', []),
                        difficulty_score=data.get('difficulty_score', target_difficulty),
                        domain=domain,
                        content_hash=content_hash,
                        season=season,
                        generation_source='ai_core',
                        retries_used=attempt - 1,
                        generation_time_ms=int((time.time() - start_total) * 1000),
                    )
                    level.task = task
                    level.save()
                    return task
                else:
                    logger.info(f"Duplicate/Invalid attempt {attempt} for L{level.level_number}: {msg if not is_valid else 'Duplicate'}")

            except requests.exceptions.ConnectionError:
                # logger.warning(f"[AI] Connection refused — marking AI offline")
                _ai_online = False
                break
            except requests.exceptions.ReadTimeout:
                # logger.warning(f"[AI] Timeout for L{level.level_number}")
                break
            except Exception as e:
                # logger.warning(f"[AI] Attempt {attempt} error: {e}")
                pass


    # ── Step 3: Vault Fallback (Salted to ensure level-specific task unique IDs) ──
    vault_data = get_vault_task_for_level(level.level_number, season.id, tier)
    if vault_data:
        # Salt with level to ensure 100 levels -> 100 unique Task objects
        content_hash = hashlib.sha256(
            f"{vault_data.get('title','')}|{vault_data.get('description','')}|{vault_data.get('starter_code','')}|L{level.level_number}".encode()
        ).hexdigest()[:64]

        task, created = Task.objects.get_or_create(
            content_hash=content_hash,
            season=season,
            defaults={
                "title": f"{vault_data.get('title')}",
                "description": vault_data.get('description'),
                "starter_code": vault_data.get('starter_code'),
                "solution": vault_data.get('solution', '') or '',
                "hints": vault_data.get('hints', []),
                "explanation": vault_data.get('explanation', '') or '',
                "type": vault_data.get('type', 'code_complete'),
                "difficulty": vault_data.get('difficulty', 'easy'),
                "test_cases": vault_data.get('test_cases', []),
                "difficulty_score": vault_data.get('difficulty_score', target_difficulty),
                "domain": vault_data.get('domain', domain),
                "generation_source": 'vault',
            },
        )
        level.task = task
        level.save()
        # logger.info(f"[Vault] L{level.level_number} ✓ '{task.title}' (created={created})")
        return task

    raise Exception(f"Failed to generate task for L{level.level_number}: AI offline and vault empty for tier '{tier}'")


def initialize_season(season_name: str) -> Season:
    """
    Monthly reset: deactivate old season, create new one, bulk-generate 100 tasks.
    """
    global _ai_online
    _ai_online = None  # Reset cached health for new bulk run

    Season.objects.filter(is_active=True).update(is_active=False)
    new_season = Season.objects.create(name=season_name, is_active=True)

    # Monthly reset: build 500 levels (100 per main domain)
    levels = []
    for dom in DOMAINS:
        for i in range(1, 101):
            levels.append(Level(
                level_number=i, 
                tier=get_tier_for_level(i), 
                season=new_season,
                domain=dom
            ))
    
    Level.objects.bulk_create(levels)

    # logger.info(f"[SkillForge] Bulk generating 100 tasks for '{season_name}'...")
    success = 0
    for lvl in Level.objects.filter(season=new_season).order_by('level_number'):
        try:
            generate_task_for_level(lvl)
            success += 1
        except Exception as e:
            # logger.error(f"[SkillForge] L{lvl.level_number} FAILED: {e}")
            pass

    # logger.info(f"[SkillForge] Generated {success}/100 tasks. Running stabilizer...")
    stabilize_season_levels(new_season.id)
    # logger.info(f"[SkillForge] Season '{season_name}' ready.")
    return new_season


def calculate_stars(score: float) -> int:
    """
    Maps a 0-100 score to 0-3 stars according to game rules:
    0-39: 0
    40-69: 1
    70-89: 2
    90-100: 3
    """
    if score >= 90: return 3
    if score >= 70: return 2
    if score >= 40: return 1
    return 0


def process_level_completion(profile, level, score, stars):
    """
    Consolidated logic to update progress and rewards in a single flow.
    """
    from .models import UserLevelProgress, Level, DomainProgress
    from django.utils import timezone as dj_tz

    # 1. Update Progress
    progress, _ = UserLevelProgress.objects.get_or_create(
        profile=profile,
        level=level,
        defaults={'is_unlocked': True}
    )
    if stars > progress.stars:
        progress.stars = stars
    if score > progress.high_score:
        progress.high_score = score
    if stars >= 1 and not progress.completed_at:
        progress.completed_at = dj_tz.now()
    progress.save()

    # 2. Award Rewards
    diff = 10
    if level.task:
        diff = level.task.difficulty_score or 10
    xp_gain = int(diff * stars * 0.5)
    coin_gain = stars * 15
    profile.xp += xp_gain
    profile.coins += coin_gain
    profile.save()

    dom = getattr(level, 'domain', None) or 'dsa'
    dp, _ = DomainProgress.objects.get_or_create(profile=profile, domain=dom, defaults={'xp': 0, 'level': 1})
    dp.xp += xp_gain
    if stars >= 1:
        dp.completed_levels = (dp.completed_levels or 0) + 1
    dp.save()
    
    # 3. Unlock Next (same domain track)
    if stars >= 1:
        dom = getattr(level, 'domain', None) or 'dsa'
        next_lvl = Level.objects.filter(
            season=level.season,
            level_number=level.level_number + 1,
            domain=dom,
        ).first()
        if next_lvl:
            UserLevelProgress.objects.get_or_create(profile=profile, level=next_lvl, defaults={'is_unlocked': True})
            
    return xp_gain, coin_gain
