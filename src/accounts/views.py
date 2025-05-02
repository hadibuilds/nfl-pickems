# accounts/views.py

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from games.models import Game
from django.http import JsonResponse

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('dashboard')  # Redirect to login page after signup
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        # Save the new user
        user = form.save()
        # Automatically log in the user
        login(self.request, user)
        return redirect(self.success_url)  # Redirect to dashboard

class CustomLoginView(LoginView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')  # Redirect logged-in users to the dashboard
        return super().dispatch(request, *args, **kwargs)

        
@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})

@login_required
def dashboard_view(request):
    """Display a list of weeks that have games."""
    weeks = Game.objects.values_list('week', flat=True).distinct().order_by('week')
    print(f"DEBUG: Retrieved weeks - {list(weeks)}")  # ✅ Debugging output
    return render(request, 'accounts/dashboard.html', {'weeks': weeks})


@login_required
def whoami(request):
    user = request.user
    print(f"Debug: Logged-in user: {user.username}")  # Print the logged-in user's username
    return JsonResponse({'username': user.username, 'email': user.email})