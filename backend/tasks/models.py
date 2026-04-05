from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Season(models.Model):
    """Monthly season container. Only one season can be active at a time."""
    name = models.CharField(max_length=100)  # e.g. "April 2026"
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"Season {self.id}: {self.name} ({'Active' if self.is_active else 'Archived'})"


class UserProfile(models.Model):
    """Lifetime user statistics and game currency."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    coins = models.IntegerField(default=1000)
    xp = models.IntegerField(default=0)
    lives = models.IntegerField(default=5)
    last_life_regen = models.DateTimeField(auto_now_add=True)
    streak_days = models.IntegerField(default=0)
    streak_multiplier = models.FloatField(default=1.0)
    last_active = models.DateField(auto_now=True)
    total_accuracy = models.FloatField(default=0.0)
    total_submissions = models.IntegerField(default=0)
    total_correct = models.IntegerField(default=0)
    selected_domain = models.CharField(max_length=50, default='dsa')
    recent_task_cache = models.TextField(default="[]", help_text="JSON list of last 50 task hashes for this user")

    def total_completed_levels(self):
        return self.progress.filter(stars__gt=0).count()

    def __str__(self):
        return f"{self.user.username} (Level {self.xp // 1000})"


class Task(models.Model):
    """Coding task, unique per season via content_hash."""
    SOURCE_CHOICES = [
        ('vault', 'Vault-based'),
        ('ai_core', 'AI-generated'),
        ('fallback', 'Static Fallback'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    TYPE_CHOICES = [
        ('bug_fix', 'Bug Fix'),
        ('code_complete', 'Code Complete'),
        ('output_prediction', 'Output Prediction'),
        ('optimization', 'Optimization'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    starter_code = models.TextField()
    solution = models.TextField(blank=True, default='')
    test_cases = models.JSONField(default=list)
    hints = models.JSONField(default=list)
    explanation = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='code_complete')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='easy')
    difficulty_score = models.IntegerField(default=10)
    domain = models.CharField(max_length=100, default='dsa', db_index=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='tasks')
    generation_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='vault')
    retries_used = models.IntegerField(default=0)
    generation_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('content_hash', 'season')

    def __str__(self):
        return f"{self.title} (S{self.season_id} - {self.generation_source})"


class Level(models.Model):
    """One of 100 levels per season, optionally linked to a generated Task."""
    TIER_CHOICES = [
        ('beginner', 'Beginner'),
        ('elementary', 'Elementary'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    level_number = models.IntegerField()
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='levels')
    domain = models.CharField(max_length=100, default='dsa', db_index=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('level_number', 'season', 'domain')
        ordering = ['level_number']

    def __str__(self):
        status = "✅" if self.task else "⬜"
        return f"{status} Level {self.level_number} [{self.tier}] (Season {self.season_id})"


class UserLevelProgress(models.Model):
    """Tracks a user's completion status and score for a specific level."""
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='progress')
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    stars = models.IntegerField(default=0)  # 0-3 stars
    high_score = models.FloatField(default=0.0)
    is_unlocked = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('profile', 'level')


class GameSession(models.Model):
    """Temporary record of an active level attempt."""
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    attempts_remaining = models.IntegerField(default=3)
    power_multiplier = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)


class GenerationLog(models.Model):
    """Records every generation attempt (success or fail) for monitoring."""
    level_number = models.IntegerField()
    tier = models.CharField(max_length=20)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    attempt_number = models.IntegerField()
    was_duplicate = models.BooleanField(default=False)
    was_invalid = models.BooleanField(default=False)
    error_msg = models.TextField(null=True, blank=True)
    source = models.CharField(max_length=20)
    duration_ms = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class DomainProgress(models.Model):
    """Tracks progress for a specific domain for a user."""
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='domain_progress')
    domain = models.CharField(max_length=100)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    accuracy = models.FloatField(default=0.0)
    completed_levels = models.IntegerField(default=0)

    class Meta:
        unique_together = ('profile', 'domain')

    def __str__(self):
        return f"{self.profile.user.username} - {self.domain} Progress"


class DailyChallenge(models.Model):
    """Daily rotating challenge (one row per calendar day **per domain**)."""
    date = models.DateField(db_index=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    domain = models.CharField(max_length=100, db_index=True)
    reward_multiplier = models.FloatField(default=2.0)

    class Meta:
        unique_together = ("date", "domain")

    def __str__(self):
        return f"Daily Challenge: {self.date} ({self.domain})"
