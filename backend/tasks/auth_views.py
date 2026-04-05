from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if not username or not password or not email:
        return Response({"error": "Username, email, and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username is already taken."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.create_user(username=username, email=email, password=password)
        # Create Profile
        UserProfile.objects.create(user=user)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "success": True,
            "message": "User registered successfully.",
            "token": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_me(request):
    user = request.user
    profile = user.profile
    
    # Get domain progress
    domains = profile.domain_progress.all()
    domain_data = {}
    for dom in domains:
        domain_data[dom.domain] = {
            "level": dom.level,
            "xp": dom.xp,
            "accuracy": dom.accuracy,
            "completed_levels": dom.completed_levels
        }

    return Response({
        "username": user.username,
        "email": user.email,
        "coins": profile.coins,
        "xp": profile.xp,
        "lives": profile.lives,
        "streak_days": profile.streak_days,
        "total_accuracy": profile.total_accuracy,
        "selected_domain": profile.selected_domain,
        "domains": domain_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_domain(request):
    """
    Updates the user's selected domain.
    POST /api/v1/auth/select-domain/
    """
    domain = request.data.get('domain')
    if not domain:
        return Response({"error": "Domain is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    valid_domains = ["dsa", "frontend", "backend", "sql", "debugging"]
    if domain not in valid_domains:
        return Response({"error": f"Invalid domain. Must be one of: {', '.join(valid_domains)}"}, status=status.HTTP_400_BAD_REQUEST)
    
    profile = request.user.profile
    profile.selected_domain = domain
    profile.save()
    
    return Response({
        "success": True,
        "selected_domain": domain,
        "message": f"Domain successfully updated to {domain}."
    })

