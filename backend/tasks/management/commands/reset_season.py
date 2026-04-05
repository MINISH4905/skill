from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.services import initialize_season
import logging

logger = logging.getLogger("SkillForge-Reset")

class Command(BaseCommand):
    help = 'Starts a new monthly SkillForge season with 100 unique tasks.'

    def handle(self, *args, **options):
        month_name = timezone.now().strftime("%B %Y")
        self.stdout.write(self.style.NOTICE(f"=== Starting Monthly Reset: {month_name} ==="))
        
        try:
            season = initialize_season(month_name)
            self.stdout.write(self.style.SUCCESS(f"Successfully initialized Season: {season.id} ({season.name})"))
            self.stdout.write(self.style.SUCCESS(f"100 Levels created and task generation complete."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Reset Failed: {str(e)}"))
            logger.error(f"Season reset failed: {e}")
