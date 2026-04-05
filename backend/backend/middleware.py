"""
SkillForge Guest Session Middleware
- Exempts /api/ routes from CSRF verification
- Ensures guest sessions work without authentication
"""

from django.utils.deprecation import MiddlewareMixin


class GuestSessionMiddleware(MiddlewareMixin):
    """Exempt all API endpoints from CSRF for guest session support."""

    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
