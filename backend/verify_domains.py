import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillforge.settings')
django.setup()

from tasks.models import Task

def verify():
    print("--- Domain Alignment Verification ---")
    domains = ["dsa", "frontend", "backend", "sql", "debugging"]
    for domain in domains:
        t = Task.objects.filter(domain=domain).order_by('-id').first()
        if t:
            print(f"Domain: {t.domain.upper()}")
            print(f"  Title: {t.title}")
            print(f"  Type:  {t.type}")
            print(f"  Starter: {t.starter_code[:60]}...")
            print("-" * 30)
        else:
            print(f"Domain: {domain.upper()} - No tasks generated yet.")

if __name__ == "__main__":
    verify()
