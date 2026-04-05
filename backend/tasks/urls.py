from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from . import auth_views

urlpatterns = [
    # Auth
    path('auth/register/', auth_views.register_user, name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', auth_views.get_me, name='get_me'),
    path('auth/select-domain/', auth_views.select_domain, name='select_domain'),

    # Health
    path('health/', views.api_health_check, name='api_health_check'),

    # Season management
    path('season/', views.get_current_season, name='current_season'),
    path('season/start/', views.start_new_season, name='start_season'),

    # Levels
    path('levels/', views.list_levels, name='list_levels'),
    path('levels/<int:level_number>/start/', views.start_level_attempt, name='start_level'),
    path('levels/<int:level_number>/task/', views.get_level_task, name='level_task'),
    path('domain/set/', views.set_domain, name='set_domain'),
    path('domain/readiness/', views.domain_readiness, name='domain_readiness'),

    # User & Progress
    path('user/profile/', views.user_profile_view, name='user_profile'),

    # Game Loop
    path('game/powers/<int:session_id>/', views.use_power_up, name='use_power'),
    path('game/run/<int:session_id>/', views.run_code, name='run_code'),
    path('game/submit/<int:session_id>/', views.submit_level_result, name='submit_result'),

    # Stats
    path('stats/', views.stats_view, name='stats'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('daily-challenge/', views.daily_challenge_view, name='daily_challenge'),
]
