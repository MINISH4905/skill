from tasks.models import Level, Task
import json

def audit_difficulty():
    levels = list(Level.objects.filter(season__is_active=True).select_related('task').order_by('level_number'))
    results = []
    for l in levels:
        results.append({
            "level": l.level_number,
            "title": l.task.title if l.task else "None",
            "diff": l.task.difficulty_score if l.task else 0,
            "tier": l.tier
        })
    with open('audit_diff.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Audit Complete: {len(results)} levels processed. Saved to audit_diff.json")

if __name__ == "__main__":
    audit_difficulty()
