import logging
import os
import requests
import multiprocessing
import threading
from django.db.models import Prefetch
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Season, Level, Task, GenerationLog, UserProfile, UserLevelProgress, GameSession, DailyChallenge
from .serializers import (
    SeasonSerializer, LevelSerializer, TaskSerializer,
    UserProfileSerializer
)
from .services import (
    initialize_season, get_active_season, generate_task_for_level,
    calculate_stars, process_level_completion, ensure_domain_levels, ai_engine_health_url,
)
from .profile_handler import get_active_profile

logger = logging.getLogger("SkillForge")


def ensure_season():
    """Auto-create a season if none exists (first-time setup)."""
    season = get_active_season()
    if not season:
        month = timezone.now().strftime("%B %Y")
        season = initialize_season(month)
    return season


# ─────────────────────────────────────────────
# User & Progress
# ─────────────────────────────────────────────

@api_view(['GET'])
def user_profile_view(request):
    """Returns the current user/guest coins, xp, and lives."""
    profile = get_active_profile(request)
    # Auto-regen lives
    regen_lives(profile)
    return Response(UserProfileSerializer(profile).data)


def regen_lives(profile):
    """Regenerate lives every 15 minutes, max 5."""
    now = timezone.now()
    if profile.lives < 5:
        delta = (now - profile.last_life_regen).total_seconds()
        regen = int(delta // 900)
        if regen > 0:
            profile.lives = min(5, profile.lives + regen)
            profile.last_life_regen = now
            profile.save()


@api_view(['POST'])
def start_level_attempt(request, level_number):
    """Deducts a life and starts a new game session."""
    season = ensure_season()
    try:
        profile = get_active_profile(request)
        domain = profile.selected_domain or 'dsa'
        level = Level.objects.get(season=season, level_number=level_number, domain=domain)
        regen_lives(profile)

        if profile.lives <= 0:
            return Response(
                {"error": "No lives left! Wait for regeneration or buy more.", "lives_left": 0},
                status=status.HTTP_403_FORBIDDEN
            )

        # Deduct life
        profile.lives -= 1
        profile.save()

        # Deactivate old sessions for this level
        GameSession.objects.filter(profile=profile, level=level, is_active=True).update(is_active=False)

        # Create session
        session = GameSession.objects.create(profile=profile, level=level)

        return Response({
            "success": True,
            "session_id": session.id,
            "lives_left": profile.lives
        })
    except Level.DoesNotExist:
        return Response({"error": f"Level {level_number} not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"start_level_attempt error: {e}")
        return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def use_power_up(request, session_id):
    """Spends coins to apply a power-up."""
    power = request.data.get('power')
    costs = {"hint": 100, "fix": 250, "logic": 350, "time": 150, "skip": 500}

    if power not in costs:
        return Response({"error": "Invalid power."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = get_active_profile(request)
        session = GameSession.objects.get(id=session_id, profile=profile, is_active=True)

        if profile.coins < costs[power]:
            return Response({"error": "Insufficient coins! Complete levels to earn more."}, status=status.HTTP_402_PAYMENT_REQUIRED)

        profile.coins -= costs[power]
        profile.save()

        session.power_multiplier *= 0.9
        session.save()

        # Generate contextual responses
        hints = {
            "hint": "💡 Check your loop boundaries and edge cases carefully.",
            "fix": "🛠 Code Scan: No automatic fix applied. Check your parameter types and return values.",
            "logic": "🧠 The key insight: think about what happens when the input is empty or has one element.",
            "time": "⏱ +2 minutes added to your timer!",
            "skip": "⏭ Level skipped! Moving to next challenge."
        }

        response_data = {
            "success": True,
            "coins_left": profile.coins,
            "message": hints.get(power, "Power applied!"),
            "power": power,
        }

        if power == 'time':
            response_data['extra_time'] = 120

        if power == 'skip':
            # Auto-complete with 1 star
            xp, coins = process_level_completion(profile, session.level, 50, 1)
            session.is_active = False
            session.save()
            response_data['skipped'] = True
            response_data['xp_gained'] = xp
            response_data['coins_gained'] = coins

        return Response(response_data)
    except GameSession.DoesNotExist:
        return Response({"error": "Session expired. Start the level again."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"use_power_up error: {e}")
        return Response({"error": "Something went wrong."}, status=status.HTTP_400_BAD_REQUEST)


from .sandbox import execute_code_worker
from .evaluation_engine import evaluate_submission


@api_view(['POST'])
def run_code(request, session_id):
    """Execute user code against sample test case."""
    try:
        profile = get_active_profile(request)
        session = GameSession.objects.select_related('level__task').get(
            id=session_id, profile=profile, is_active=True
        )
        task = session.level.task
        if not task:
            return Response({"error": "No task loaded for this level."}, status=400)

        user_code = request.data.get('code', '')
        test_cases = task.test_cases or []

        if not test_cases:
            return Response({
                "output": "No test cases available.",
                "results": []
            })

        # Run against first test case only (for Run button)
        tc = test_cases[0]
        test_input = tc.get('input')
        expected = tc.get('output')

        queue = multiprocessing.Queue()
        proc = multiprocessing.Process(target=execute_code_worker, args=(user_code, test_input, queue))
        proc.start()
        proc.join(timeout=5)

        if proc.is_alive():
            proc.terminate()
            proc.join()
            return Response({
                "output": "⏱ Time Limit Exceeded! Your code took too long.",
                "passed": False,
                "results": [{"input": str(test_input), "expected": str(expected), "actual": "TIMEOUT", "passed": False}]
            })

        if queue.empty():
            return Response({
                "output": "❌ Execution failed with no output.",
                "passed": False,
                "results": []
            })

        result = queue.get()

        if 'error' in result:
            return Response({
                "output": f"❌ Error: {result['error']}",
                "passed": False,
                "results": [{"input": str(test_input), "expected": str(expected), "actual": f"ERROR: {result['error']}", "passed": False}]
            })

        actual = result.get('result')
        passed = (str(actual) == str(expected))
        stdout_text = result.get('stdout', '')

        output_lines = []
        if stdout_text:
            output_lines.append(f"📤 stdout: {stdout_text.strip()}")
        output_lines.append(f"Input:    {test_input}")
        output_lines.append(f"Expected: {expected}")
        output_lines.append(f"Actual:   {actual}")
        output_lines.append(f"Status:   {'✅ PASSED' if passed else '❌ FAILED'}")

        return Response({
            "output": "\n".join(output_lines),
            "passed": passed,
            "results": [{"input": str(test_input), "expected": str(expected), "actual": str(actual), "passed": passed}]
        })

    except GameSession.DoesNotExist:
        return Response({"error": "Session expired.", "output": "Session not found."}, status=404)
    except Exception as e:
        logger.error(f"run_code error: {e}")
        return Response({"output": f"❌ System error. Please try again.", "passed": False}, status=500)


# ─────────────────────────────────────────────
# Submit Code (full evaluation)
# ─────────────────────────────────────────────

@api_view(['POST'])
def submit_level_result(request, session_id):
    """Full evaluation: run all test cases, award stars/XP/coins."""
    profile = get_active_profile(request)
    regen_lives(profile)

    session = GameSession.objects.filter(id=session_id, profile=profile, is_active=True).select_related('level__task').first()

    if not session:
        return Response({"error": "Session expired or invalid."}, status=400)

    task = session.level.task
    if not task:
        return Response({"error": "No task loaded."}, status=400)

    user_code = request.data.get('code', '')
    test_cases = task.test_cases or []

    passed_count = 0
    total = len(test_cases) if test_cases else 1
    results = []

    # Domain specific evaluation fallback
    if task.domain in ["frontend", "sql"] or not test_cases:
        expected = test_cases[0].get('output', '') if test_cases else ""
        # Simple heuristic or regex check for non-executable domains
        if task.domain == 'frontend' and 'flex' in user_code.lower() and 'center' in user_code.lower():
            passed_count = 1
            results.append({"input": "HTML", "expected": "Flexbox", "actual": "Valid CSS", "passed": True})
        elif task.domain == 'sql' and 'select' in user_code.lower():
            passed_count = 1
            results.append({"input": "Table", "expected": expected, "actual": "Valid Query", "passed": True})
        elif expected and expected.lower() in user_code.lower():
            passed_count = 1
            results.append({"input": "Text", "expected": expected, "actual": "Match Found", "passed": True})
        else:
            results.append({"input": "Text", "expected": expected, "actual": "Failed syntax/heuristic", "passed": False})
    else:
        # standard python execution
        for tc in test_cases:
            test_input = tc.get('input')
            expected = tc.get('output')

            queue = multiprocessing.Queue()
            proc = multiprocessing.Process(target=execute_code_worker, args=(user_code, test_input, queue))
            proc.start()
            proc.join(timeout=5)

            if proc.is_alive():
                proc.terminate()
                proc.join()
                results.append({"input": str(test_input), "expected": str(expected), "actual": "TIMEOUT", "passed": False})
                continue

            if queue.empty():
                results.append({"input": str(test_input), "expected": str(expected), "actual": "NO OUTPUT", "passed": False})
                continue

            result = queue.get()
            if 'error' in result:
                results.append({"input": str(test_input), "expected": str(expected), "actual": f"ERROR: {result['error']}", "passed": False})
                continue

            actual = result.get('result')
            tc_passed = (str(actual) == str(expected))
            if tc_passed:
                passed_count += 1
            results.append({"input": str(test_input), "expected": str(expected), "actual": str(actual), "passed": tc_passed})

    # Calculate score + structured evaluation metadata
    if total == 0:
        score = 100 if any(k in user_code.lower() for k in ["return", "def", "solve", "fix"]) else 35
        eval_meta = evaluate_submission(
            domain=task.domain,
            user_code=user_code,
            test_cases=[],
            passed_count=1 if score >= 70 else 0,
            total=1,
        )
    else:
        base = int((passed_count / total) * 100)
        eval_meta = evaluate_submission(
            domain=task.domain,
            user_code=user_code,
            test_cases=test_cases,
            passed_count=passed_count,
            total=total,
        )
        # Prefer blended score for text-heavy domains; keep tests as floor for code domains
        if task.domain.lower() in ("sql", "frontend", "css", "ui"):
            score = int(round(eval_meta.score))
        else:
            score = base

    stars = calculate_stars(score)

    profile.total_submissions = (profile.total_submissions or 0) + 1
    if stars >= 1:
        profile.total_correct = (profile.total_correct or 0) + 1
    subs = max(1, profile.total_submissions or 0)
    profile.total_accuracy = round(100.0 * (profile.total_correct or 0) / subs, 2)
    profile.save()

    if stars >= 1:
        # SUCCESS
        xp, coins = process_level_completion(profile, session.level, score, stars)
        session.is_active = False
        session.save()
        return Response({
            "status": "success",
            "score": score,
            "stars": stars,
            "xp_gained": xp,
            "coins_gained": coins,
            "passed": passed_count,
            "total": total,
            "results": results,
            "message": f"🎉 {passed_count}/{total} tests passed!",
            "confidence": eval_meta.confidence,
            "mistake_kind": eval_meta.mistake_kind,
            "feedback": eval_meta.feedback,
            "evaluation_method": eval_meta.method,
        })
    else:
        # FAILURE — deduct life
        profile.lives = max(0, profile.lives - 1)
        profile.save()

        session.attempts_remaining -= 1
        if session.attempts_remaining <= 0:
            session.is_active = False
        session.save()

        return Response({
            "status": "fail",
            "score": score,
            "stars": 0,
            "passed": passed_count,
            "total": total,
            "results": results,
            "lives_remaining": profile.lives,
            "attempts_remaining": session.attempts_remaining,
            "message": f"❌ {passed_count}/{total} tests passed. Keep trying!",
            "confidence": eval_meta.confidence,
            "mistake_kind": eval_meta.mistake_kind,
            "feedback": eval_meta.feedback,
            "evaluation_method": eval_meta.method,
        })


# ─────────────────────────────────────────────
# Season & Level APIs
# ─────────────────────────────────────────────

@api_view(['GET'])
def get_current_season(request):
    season = ensure_season()
    return Response(SeasonSerializer(season).data)


@api_view(['POST'])
def start_new_season(request):
    try:
        month = timezone.now().strftime("%B %Y")
        season = initialize_season(month)
        return Response({
            "success": True,
            "message": f"Season '{month}' started with 100 levels.",
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_levels(request):
    """Returns all levels for the active season and selected domain."""
    season = ensure_season()
    profile = get_active_profile(request)
    
    # Priority: Query param > Profile state > Default 'dsa'
    domain_query = request.GET.get('domain')
    domain = domain_query or profile.selected_domain or 'dsa'

    if domain_query and profile.selected_domain != domain:
        profile.selected_domain = domain
        profile.save()

    ensure_domain_levels(season, domain)
    prog_qs = UserLevelProgress.objects.filter(profile=profile)
    levels = (
        Level.objects.filter(season=season, domain=domain)
        .select_related('task')
        .prefetch_related(Prefetch('userlevelprogress_set', queryset=prog_qs))
        .order_by('level_number')
    )
    data = LevelSerializer(levels, many=True, context={'request': request}).data
    return Response(data)


@api_view(["GET"])
def domain_readiness(request):
    """Progress toward 100 tasks for a domain (for UI polling)."""
    season = ensure_season()
    domain = request.GET.get("domain", "dsa")
    ensure_domain_levels(season, domain)
    n_levels = Level.objects.filter(season=season, domain=domain).count()
    with_tasks = Level.objects.filter(season=season, domain=domain, task__isnull=False).count()
    return Response(
        {
            "domain": domain,
            "levels_total": n_levels,
            "tasks_ready": with_tasks,
            "target": 100,
            "ready": n_levels >= 100 and with_tasks >= 100,
        }
    )


def background_fill_domain_tasks(domain, season_name):
    """
    Fill all 100 level slots for this domain using generate_task_for_level
    (AI + vault fallback — same path as on-demand generation).
    """
    season = Season.objects.filter(name=season_name, is_active=True).first() or get_active_season()
    if not season:
        logger.warning("background_fill_domain_tasks: no season")
        return
    ensure_domain_levels(season, domain)
    empty = (
        Level.objects.filter(season=season, domain=domain, task__isnull=True)
        .select_related("season")
        .order_by("level_number")
    )
    n = empty.count()
    if n == 0:
        logger.info("Domain %s: all 100 levels already have tasks", domain)
        return
    logger.info("Domain %s: generating tasks for %s empty levels", domain, n)
    for level in empty:
        try:
            generate_task_for_level(level)
        except Exception as e:
            logger.error("Domain %s L%s: %s", domain, level.level_number, e)
    logger.info("Domain %s: background fill pass complete", domain)


@api_view(['POST'])
def set_domain(request):
    """Updates the selected domain in UserProfile and triggers background AI batch (logged-in users)."""
    domain = request.data.get('domain')
    if not domain:
        return Response({"error": "Domain required"}, status=400)

    profile = get_active_profile(request)
    profile.selected_domain = domain
    profile.save()

    season = ensure_season()
    ensure_domain_levels(season, domain)
    need_fill = Level.objects.filter(season=season, domain=domain, task__isnull=True).exists()
    if need_fill:
        threading.Thread(target=background_fill_domain_tasks, args=(domain, season.name), daemon=True).start()
        msg = f"Domain {domain} selected. Preparing all 100 challenges..."
    else:
        msg = f"Domain {domain} ready — all 100 challenges loaded."

    return Response({"message": msg, "selected_domain": domain})


@api_view(['GET'])
def get_level_detail(request, level_number):
    season = ensure_season()
    profile = get_active_profile(request)
    domain = profile.selected_domain or 'dsa'
    try:
        level = Level.objects.select_related('task').get(
            season=season, 
            level_number=level_number,
            domain=domain
        )
        return Response(LevelSerializer(level, context={'request': request}).data)
    except Level.DoesNotExist:
        return Response({"error": f"Level {level_number} not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_level_task(request, level_number):
    """Get or generate the task for a level."""
    season = ensure_season()
    profile = get_active_profile(request)
    domain = profile.selected_domain or 'dsa'
    try:
        level = Level.objects.select_related('task').get(
            season=season, 
            level_number=level_number,
            domain=domain
        )
    except Level.DoesNotExist:
        return Response({"error": f"Level {level_number} not found."}, status=status.HTTP_404_NOT_FOUND)

    if level.task:
        return Response({
            "level": level.level_number,
            "tier": level.tier,
            "task": TaskSerializer(level.task).data,
            "cached": True,
        })

    try:
        task = generate_task_for_level(level)
        return Response({
            "level": level.level_number,
            "tier": level.tier,
            "task": TaskSerializer(task).data,
            "cached": False,
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Task generation failed: {e}")
        return Response({
            "error": "AI Engine busy. Try again shortly.",
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@api_view(['GET'])
def api_health_check(request):
    try:
        r = requests.get(ai_engine_health_url(), timeout=3)
        ai_status = "ONLINE" if r.status_code == 200 else "DEGRADED"
    except Exception:
        ai_status = "OFFLINE"

    season = get_active_season()
    return Response({
        "django_status": "ONLINE",
        "fastapi_status": ai_status,
        "active_season": season.name if season else None,
    })


@api_view(['GET'])
def stats_view(request):
    season = get_active_season()
    if not season:
        return Response({"error": "No active season."})

    total_levels = Level.objects.filter(season=season).count()
    tasks_ready = Task.objects.filter(season=season).count()

    return Response({
        "season": season.name,
        "total_levels": total_levels,
        "tasks_ready": tasks_ready,
        "tasks_pending": total_levels - tasks_ready,
    })

@api_view(['GET'])
def daily_challenge_view(request):
    """Today's challenge for the active domain (creates row if missing)."""
    season = ensure_season()
    profile = get_active_profile(request)
    domain = request.GET.get('domain') or profile.selected_domain or 'dsa'
    today = timezone.now().date()

    dc = DailyChallenge.objects.filter(date=today, domain=domain).select_related('task').first()
    if not dc:
        pool = Task.objects.filter(season=season, domain=domain).exclude(test_cases=[]).order_by('?')[:20]
        task = pool.first() if pool else None
        if not task:
            return Response({"error": "No tasks available for daily challenge yet."}, status=503)
        dc = DailyChallenge.objects.create(date=today, task=task, domain=domain, reward_multiplier=2.0)

    return Response({
        "date": str(dc.date),
        "domain": dc.domain,
        "reward_multiplier": dc.reward_multiplier,
        "task": TaskSerializer(dc.task).data,
    })


@api_view(['GET'])
def leaderboard_view(request):
    """Global and Domain-specific leaderboard."""
    domain = request.GET.get('domain', None)
    if domain:
        from .models import DomainProgress
        top = DomainProgress.objects.filter(domain=domain).select_related('profile__user').order_by('-xp', '-accuracy')[:10]
        data = [{"username": p.profile.user.username, "xp": p.xp, "accuracy": p.accuracy, "level": p.level} for p in top]
    else:
        from .models import UserProfile
        top = UserProfile.objects.select_related('user').order_by('-xp')[:10]
        data = [{"username": p.user.username, "xp": p.xp, "streak": p.streak_days, "lives": p.lives} for p in top]
        
    return Response(data)
