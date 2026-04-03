import os
import django
from django.urls import resolve, get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

resolver = get_resolver()
print("Listing all registered URLs:")
for pattern in resolver.url_patterns:
    print(f"Pattern: {pattern}")
    if hasattr(pattern, 'url_patterns'):
         for sub in pattern.url_patterns:
             print(f"  -> {sub}")

try:
    print("\nAttempting to resolve /health/:")
    match = resolve('/health/')
    print(f"Match found: {match.view_name}")
except Exception as e:
    print(f"Error resolving /health/: {e}")

try:
    print("\nAttempting to resolve /api/v1/health/:")
    match = resolve('/api/v1/health/')
    print(f"Match found: {match.view_name}")
except Exception as e:
    print(f"Error resolving /api/v1/health/: {e}")
