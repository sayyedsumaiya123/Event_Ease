from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, View, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction
from django.contrib.auth.models import User
from events.models import Event

from .forms import RegisterForm, LoginForm, ProfileUpdateForm, CoordinatorRegisterForm, CoordinatorLoginForm
from .models import CoordinatorApplication


class RegisterView(CreateView):
    """User registration view."""
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('events:home')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f'🎉 Welcome to EventEase, {user.first_name}! Your account has been created.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class LoginView(View):
    """Custom login view."""
    template_name = 'accounts/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('events:home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
            next_url = request.GET.get('next', '')
            if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                next_url = 'events:home'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
        return render(request, self.template_name, {'form': form})


class CoordinatorRegisterView(RegisterView):
    form_class = CoordinatorRegisterForm
    template_name = 'accounts/coordinator_register.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Coordinator request submitted. An organizer or administrator will review it.')
        return redirect('accounts:coordinator_panel')


class CoordinatorLoginView(View):
    template_name = 'accounts/coordinator_login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:coordinator_panel')
        return render(request, self.template_name, {'form': CoordinatorLoginForm(request)})

    def post(self, request):
        form = CoordinatorLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('accounts:coordinator_panel')
        return render(request, self.template_name, {'form': form})


class CoordinatorPanelView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/coordinator_panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        application = CoordinatorApplication.objects.filter(user=user).first()
        if not (user.is_staff or user.is_superuser or application):
            raise PermissionDenied('A coordinator account is required.')
        context['application'] = application
        context['coordinator_approved'] = user.is_active and (user.is_staff or user.is_superuser)
        context['can_review_coordinators'] = user.is_active and (user.is_superuser or (user.is_staff and user.profile.is_organizer))
        if context['coordinator_approved']:
            context['own_events'] = Event.objects.filter(organizer=user).order_by('date', 'time')
            context['assigned_events'] = Event.objects.filter(coordinators=user).exclude(organizer=user).select_related('organizer').order_by('date', 'time')
            context['coordinator_directory'] = User.objects.filter(is_active=True, is_staff=True, is_superuser=False, profile__is_organizer=False).order_by('username')
        if context['can_review_coordinators']:
            context['pending_applications'] = CoordinatorApplication.objects.filter(status='pending', user__is_active=True).select_related('user').order_by('created_at')
        return context


class CoordinatorApplicationDecisionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        reviewer = request.user
        if not (reviewer.is_active and (reviewer.is_superuser or (reviewer.is_staff and reviewer.profile.is_organizer))):
            raise PermissionDenied('Organizer access is required to review coordinator applications.')
        decision = request.POST.get('decision')
        if decision not in ('approve', 'reject'):
            raise PermissionDenied('Invalid decision.')
        with transaction.atomic():
            application = get_object_or_404(CoordinatorApplication.objects.select_for_update().select_related('user'), pk=pk)
            if application.status != 'pending' or not application.user.is_active or application.user.is_staff or application.user.is_superuser or application.user.profile.is_organizer:
                messages.warning(request, 'This application is no longer pending.')
            else:
                application.status = 'approved' if decision == 'approve' else 'rejected'
                application.save(update_fields=['status'])
                application.user.is_staff = decision == 'approve'
                application.user.save(update_fields=['is_staff'])
                messages.success(request, f"Coordinator application {application.status} for {application.user.username}.")
        return redirect('accounts:coordinator_panel')


class LogoutView(View):
    """Logout view."""
    def post(self, request):
        logout(request)
        messages.info(request, 'You have been logged out. See you next time!')
        return redirect('events:home')


class ProfileView(LoginRequiredMixin, TemplateView):
    """View user profile."""
    template_name = 'accounts/profile.html'


class ProfileUpdateView(LoginRequiredMixin, View):
    """Update user profile."""
    template_name = 'accounts/profile_edit.html'

    def get(self, request):
        form = ProfileUpdateForm(instance=request.user.profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            # Update User model fields
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        return render(request, self.template_name, {'form': form})
