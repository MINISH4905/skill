from django.core.management.base import BaseCommand
from tasks.models import Season, Level, UserProfile, UserLevelProgress
from django.contrib.auth.models import User
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seed 100 levels for the active season'

    def handle(self, *args, **options):
        # 1. Create Active Season
        season, _ = Season.objects.get_or_create(
            name="May 2026",
            defaults={'is_active': True}
        )
        
        # Ensure only this season is active
        Season.objects.exclude(id=season.id).update(is_active=False)
        season.is_active = True
        season.save()

        self.stdout.write(self.style.SUCCESS(f'Active Season: {season.name}'))

        # 2. Define Tiers
        # 1-20: Beginner, 21-40: Elementary, 41-60: Intermediate, 61-80: Advanced, 81-100: Expert
        def get_tier(num):
            if num <= 20: return 'beginner'
            if num <= 40: return 'elementary'
            if num <= 60: return 'intermediate'
            if num <= 80: return 'advanced'
            return 'expert'

        # 3. Generate 100 Levels
        levels_created = 0
        for i in range(1, 101):
            level, created = Level.objects.get_or_create(
                level_number=i,
                season=season,
                defaults={'tier': get_tier(i)}
            )
            if created:
                levels_created += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {levels_created} total levels.'))

        # 4. Handle Guest Progress
        guest_user, _ = User.objects.get_or_create(username='CommunityGuest')
        profile, _ = UserProfile.objects.get_or_create(user=guest_user)
        
        # Unlock Level 1
        lvl1 = Level.objects.get(level_number=1, season=season)
        progress, created = UserLevelProgress.objects.get_or_create(
            profile=profile,
            level=lvl1,
            defaults={'is_unlocked': True}
        )
        if not progress.is_unlocked:
            progress.is_unlocked = True
            progress.save()

        self.stdout.write(self.style.SUCCESS('Community Guest Level 1 Unlocked!'))
