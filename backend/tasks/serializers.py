from rest_framework import serializers
from .models import Season, Level, Task, GenerationLog, UserLevelProgress, UserProfile


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'starter_code', 'solution',
            'test_cases', 'hints', 'explanation', 'type', 'difficulty',
            'difficulty_score', 'domain', 'content_hash', 'season',
            'generation_source', 'retries_used', 'generation_time_ms', 'created_at',
        ]


class GenerationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationLog
        fields = '__all__'


class LevelSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)
    has_task = serializers.SerializerMethodField()
    stars = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ['id', 'level_number', 'tier', 'domain', 'season', 'task', 'has_task', 'stars', 'is_unlocked']

    def get_has_task(self, obj):
        return obj.task is not None

    def get_progress(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        # Use prefetched relation when available (list_levels prefetch)
        rel = getattr(obj, 'userlevelprogress_set', None)
        if rel is not None:
            cached = list(rel.all())
            if cached:
                return cached[0]
        from .profile_handler import get_active_profile
        profile = get_active_profile(request)
        if not profile:
            return None
        return UserLevelProgress.objects.filter(profile=profile, level=obj).first()

    def get_stars(self, obj):
        progress = self.get_progress(obj)
        return progress.stars if progress else 0

    def get_is_unlocked(self, obj):
        # Level 1 is always unlocked by default for guests
        if obj.level_number == 1:
            return True
        progress = self.get_progress(obj)
        return progress.is_unlocked if progress else False


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['coins', 'xp', 'lives', 'streak_days', 'selected_domain', 'streak_multiplier', 'total_accuracy']


class SeasonSerializer(serializers.ModelSerializer):
    total_levels = serializers.SerializerMethodField()
    tasks_generated = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = ['id', 'name', 'start_date', 'end_date', 'is_active',
                  'total_levels', 'tasks_generated']

    def get_total_levels(self, obj):
        return obj.levels.count()

    def get_tasks_generated(self, obj):
        return obj.tasks.count()
