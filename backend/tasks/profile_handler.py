from .models import UserProfile
from django.contrib.auth import get_user_model

def get_active_profile(request):
    """
    Returns the authenticated profile or a unique per-browser Guest profile 
    Based on the 'X-Session-ID' header.
    """
    if not request:
        return None

    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return profile
    
    # Production Grade: Use X-Session-ID for persistent guest sessions
    session_id = request.headers.get('X-Session-ID') if hasattr(request, 'headers') else None
    
    if not session_id:
        # Fallback for direct browser visits before JS initialization
        session_id = "DefaultGuestSync"

    User = get_user_model()
    
    # Store Guests as ghost users or in a dedicated session table
    guest_username = f"guest_{session_id[:20]}"
    guest_user, _ = User.objects.get_or_create(username=guest_username)
    
    profile, _ = UserProfile.objects.get_or_create(
        user=guest_user, 
        defaults={'coins': 1000, 'lives': 3, 'xp': 0}
    )
    return profile
