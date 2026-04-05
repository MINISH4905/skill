import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from tasks.models import Level, Season, Task
from tasks.services import TASK_VAULT
from tasks.evaluators.evaluators.code_evaluator import evaluate_code

print("=" * 60)
print("SKILLFORGE CODE HEALTH CHECK")
print("=" * 60)

# ── 1. Vault Integrity
titles = [t['title'] for t in TASK_VAULT]
codes  = [t['starter_code'] for t in TASK_VAULT]
diffs  = [t['difficulty_score'] for t in TASK_VAULT]
vault_sorted = all(diffs[i] <= diffs[i+1] for i in range(len(diffs)-1))
print(f"\n[VAULT]")
print(f"  Size:           {len(TASK_VAULT)}/100  {'[OK]' if len(TASK_VAULT)==100 else '[!!]'}")
print(f"  Unique Titles:  {len(set(titles))}/100  {'[OK]' if len(set(titles))==100 else '[!!]'}")
print(f"  Unique Codes:   {len(set(codes))}/100  {'[OK]' if len(set(codes))==100 else '[!!]'}")
print(f"  Diff Range:     {min(diffs)} → {max(diffs)}")
print(f"  Vault Sorted:   {vault_sorted}  {'[OK]' if vault_sorted else '[!!]'}")

# ── 2. DB Integrity
active = Season.objects.filter(is_active=True).first()
if not active:
    print("\n[DB] [!!] NO ACTIVE SEASON FOUND")
else:
    db_tasks = list(Task.objects.filter(season=active))
    db_titles = [t.title for t in db_tasks]
    linked    = Level.objects.filter(season=active, task__isnull=False).count()
    db_diffs  = sorted([t.difficulty_score for t in db_tasks])
    mono      = all(db_diffs[i] <= db_diffs[i+1] for i in range(len(db_diffs)-1))
    unique_hashes = len(set(t.content_hash for t in db_tasks))
    print(f"\n[DB — {active.name}]")
    print(f"  Tasks Created:  {len(db_tasks)}/100  {'[OK]' if len(db_tasks)==100 else '[!!]'}")
    print(f"  Unique Titles:  {len(set(db_titles))}/100  {'[OK]' if len(set(db_titles))==100 else '[!!]'}")
    print(f"  Unique Hashes:  {unique_hashes}/100  {'[OK]' if unique_hashes==100 else '[!!]'}")
    print(f"  Linked Levels:  {linked}/100  {'[OK]' if linked==100 else '[!!]'}")
    print(f"  Difficulty Mono:{mono}  {'[OK]' if mono else '[!!]'}")
    print(f"  Diff Range:     {db_diffs[0]} → {db_diffs[-1]}")

    # ── 3. Level Spot Check
    print("\n[LEVEL SPOT CHECK]")
    for lvl_num in [1, 10, 25, 50, 75, 100]:
        lvl = Level.objects.filter(season=active, level_number=lvl_num).select_related('task').first()
        if lvl and lvl.task:
            print(f"  L{lvl_num:3d} [{lvl.tier[:5]}] diff={lvl.task.difficulty_score:3d} | {lvl.task.title[:45]}")
        else:
            print(f"  L{lvl_num:3d} ❌ No task linked")

    # ── 4. Evaluator Quick Test (Level 1)
    print("\n[EVALUATOR TEST — Level 1]")
    lvl1 = Level.objects.filter(season=active, level_number=1).select_related('task').first()
    if lvl1 and lvl1.task:
        result = evaluate_code(lvl1.task.starter_code, lvl1.task.test_cases)
        print(f"  Task: {lvl1.task.title}")
        print(f"  Starter Code: {repr(lvl1.task.starter_code)}")
        print(f"  Test Cases:   {lvl1.task.test_cases}")
        print(f"  Result:       passed={result['passed']}/{result['total']}")
        print(f"  Results:      {result['results']}")

print("\n" + "=" * 60)
print("HEALTH CHECK COMPLETE")
print("=" * 60)
