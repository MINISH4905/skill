from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from .forms import CustomUserCreationForm, ProfileUpdateForm


# ✅ REGISTER
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully!")
            return redirect('accounts:login')

    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


# ✅ LOGIN
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        print("USERNAME:", username)
        print("PASSWORD:", password)

        user = authenticate(request, username=username, password=password)

        print("USER OBJECT:", user)  # 👈 IMPORTANT

        if user:
            login(request, user)
            print("LOGIN SUCCESS")   # 👈 DEBUG
            return redirect('accounts:profile')
        else:
            print("LOGIN FAILED")   # 👈 DEBUG

    return render(request, 'accounts/login.html')

# ✅ LOGOUT (POST only)
@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


# ✅ PROFILE
@login_required
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated!")

    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'accounts/profile.html', {'form': form})