from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction
from io import BytesIO
import base64
import qrcode
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
import csv
import uuid
from django.urls import reverse_lazy, reverse
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Event, Category, Registration, EventFeedback, AttendanceSession, AttendanceRecord, ParticipationCertificate
from .passport import attended_events, category_summary, certificate_is_valid, certificate_pdf
from .forms import EventForm, EventSearchForm, FeedbackForm
from .permissions import (
    AdminRequiredMixin, OrganizerRequiredMixin, ManagedEventMixin,
    EventFormUserMixin, managed_events,
)


class HomeView(TemplateView):
    """Home page with featured events and statistics."""
    template_name = 'events/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        context['featured_events'] = Event.objects.filter(
            status='upcoming', featured=True, date__gte=today
        ).select_related('category', 'organizer')[:6]
        context['upcoming_events'] = Event.objects.filter(
            status='upcoming', date__gte=today
        ).select_related('category', 'organizer').order_by('date')[:6]
        context['categories'] = Category.objects.annotate(event_count=Count('events'))[:8]
        context['total_events'] = Event.objects.count()
        context['total_users'] = User.objects.count()
        context['total_registrations'] = Registration.objects.filter(status='confirmed').count()
        context['upcoming_count'] = Event.objects.filter(status='upcoming', date__gte=today).count()
        return context


class EventListView(ListView):
    """Browse all events with filtering and search."""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 9

    def get_queryset(self):
        queryset = Event.objects.select_related('category', 'organizer').all()
        form = EventSearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get('q')
            category = form.cleaned_data.get('category')
            status = form.cleaned_data.get('status')
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')

            if q:
                queryset = queryset.filter(
                    Q(title__icontains=q) |
                    Q(description__icontains=q) |
                    Q(venue__icontains=q) |
                    Q(tags__icontains=q)
                )
            if category:
                queryset = queryset.filter(category=category)
            if status:
                queryset = queryset.filter(status=status)
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = EventSearchForm(self.request.GET)
        context['categories'] = Category.objects.annotate(event_count=Count('events'))
        return context


class EventDetailView(DetailView):
    """Event detail page."""
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        user = self.request.user

        if user.is_authenticated:
            context['user_registration'] = Registration.objects.filter(
                user=user, event=event
            ).first()
            context['user_feedback'] = EventFeedback.objects.filter(
                user=user, event=event
            ).first()

        context['related_events'] = Event.objects.filter(
            category=event.category, status='upcoming'
        ).exclude(pk=event.pk)[:3]
        context['feedback_form'] = FeedbackForm()
        context['registration_open'] = event.status == 'upcoming' and event.date >= timezone.localdate()
        context['can_manage_event'] = user.is_authenticated and user.is_active and (
            user.is_superuser or (user.is_staff and (event.organizer_id == user.pk or event.coordinators.filter(pk=user.pk).exists()))
        )
        context['feedbacks'] = event.feedbacks.select_related('user').order_by('-created_at')[:5]
        return context


class EventRegisterView(LoginRequiredMixin, View):
    """Register a user for an event."""

    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)

        with transaction.atomic():
            event = Event.objects.select_for_update().get(pk=event.pk)
            if event.status != 'upcoming' or event.date < timezone.localdate():
                messages.error(request, 'Registration is closed for this event.')
                return redirect('events:event_detail', slug=slug)
            registration = Registration.objects.filter(user=request.user, event=event).first()
            if registration and registration.status != 'cancelled':
                messages.warning(request, 'You are already registered or on the waitlist.')
                return redirect('events:event_detail', slug=slug)
            status = 'waitlisted' if event.is_full else 'confirmed'
            if registration:
                registration.status = status
                # Rejoining the waitlist goes to the back of the queue.
                registration.registration_date = timezone.now()
            else:
                registration = Registration(user=request.user, event=event, status=status)
            for field in ('branch', 'student_class', 'roll_number'):
                setattr(registration, field, request.POST.get(field, '').strip()[:Registration._meta.get_field(field).max_length])
            registration.save()
        if status == 'waitlisted':
            messages.info(request, 'The event is full. You have joined the waitlist; check your dashboard for updates.')
        else:
            messages.success(request, f'Registration confirmed. Ticket: {registration.ticket_number}')
        return redirect('events:event_detail', slug=slug)


class CancelRegistrationView(LoginRequiredMixin, View):
    """Cancel a registration and offer the seat to the earliest waitlisted user."""

    def post(self, request, slug):
        with transaction.atomic():
            event = get_object_or_404(Event.objects.select_for_update(), slug=slug)
            registration = get_object_or_404(Registration, user=request.user, event=event)
            was_confirmed = registration.status == 'confirmed'
            registration.status = 'cancelled'
            registration.save(update_fields=['status'])
            if was_confirmed and event.status == 'upcoming' and event.date >= timezone.localdate():
                while event.available_seats:
                    next_registration = event.registrations.filter(status='waitlisted').order_by('registration_date', 'pk').first()
                    if not next_registration:
                        break
                    next_registration.status = 'confirmed'
                    next_registration.save(update_fields=['status'])
        messages.success(request, f'Registration for "{event.title}" has been cancelled.')
        return redirect('events:user_dashboard')


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """User personal dashboard."""
    template_name = 'events/user_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()

        registrations = Registration.objects.filter(
            user=user
        ).select_related('event', 'event__category').order_by('-registration_date')

        context['registrations'] = registrations
        context['confirmed_count'] = registrations.filter(status='confirmed').count()
        context['upcoming_events'] = registrations.filter(
            status='confirmed', event__date__gte=today
        ).count()
        context['attended_count'] = attended_events(user).count()
        context['cancelled_count'] = registrations.filter(status='cancelled').count()
        return context


class EventPassportView(LoginRequiredMixin, TemplateView):
    template_name = 'events/passport.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        events = list(attended_events(self.request.user))
        context['attended_events'] = events
        context['category_counts'] = category_summary(events)
        context['attended_total'] = len(events)
        return context


class PassportExportView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="eventease-passport.csv"'
        writer = csv.writer(response)
        writer.writerow(['Event', 'Date', 'Category', 'Venue', 'Attendance'])
        def safe(value):
            value = str(value or '')
            return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value
        for event in attended_events(request.user):
            writer.writerow([safe(event.title), event.date.isoformat(), safe(event.category.name if event.category else 'Other'), safe(event.venue), 'Recorded'])
        return response


class CertificateDownloadView(LoginRequiredMixin, View):
    def post(self, request, slug):
        # Lock the registration while issuing; only the attendee can request it.
        with transaction.atomic():
            reg = get_object_or_404(Registration.objects.select_for_update().select_related('event', 'user'), event__slug=slug, user=request.user, status='confirmed')
            if not reg.event.certificates_enabled or reg.event.status == 'cancelled' or not AttendanceRecord.objects.filter(session__event=reg.event, user=request.user, status='present').exists():
                raise Http404('Certificate is not available.')
            cert, _ = ParticipationCertificate.objects.get_or_create(registration=reg, defaults={
                'attendee_name': request.user.get_full_name().strip() or request.user.username,
                'event_title': reg.event.title, 'event_date': reg.event.date,
            })
        verification_url = request.build_absolute_uri(reverse('events:verify_certificate', args=[cert.pk]))
        response = FileResponse(certificate_pdf(cert, verification_url), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="eventease-certificate-{cert.pk}.pdf"'
        response['Cache-Control'] = 'private, no-store'
        return response


class CertificateLookupView(View):
    def get(self, request):
        raw = request.GET.get('id', '').strip()
        if raw:
            try:
                return redirect('events:verify_certificate', certificate_id=uuid.UUID(raw))
            except ValueError:
                return render(request, 'events/certificate_lookup.html', {'error': 'Enter a valid certificate ID.', 'entered_id': raw})
        return render(request, 'events/certificate_lookup.html')


class CertificateVerificationView(View):
    def get(self, request, certificate_id):
        cert = ParticipationCertificate.objects.select_related('registration__event', 'registration__user').filter(pk=certificate_id).first()
        valid = bool(cert and certificate_is_valid(cert))
        response = render(request, 'events/certificate_verify.html', {'certificate': cert if valid else None, 'valid': valid}, status=200 if valid else 404)
        response['Cache-Control'] = 'no-store'
        return response


# ─────────── ADMIN VIEWS ───────────

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Admin statistics dashboard."""
    template_name = 'events/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        context['total_events'] = Event.objects.count()
        context['total_users'] = User.objects.count()
        context['total_registrations'] = Registration.objects.filter(status='confirmed').count()
        context['upcoming_events'] = Event.objects.filter(status='upcoming', date__gte=today).count()
        context['recent_events'] = Event.objects.select_related('category', 'organizer').order_by('-created_at')[:5]
        context['top_events'] = Event.objects.annotate(
            reg_count=Count('registrations')
        ).order_by('-reg_count')[:5]
        context['recent_registrations'] = Registration.objects.select_related(
            'user', 'event'
        ).order_by('-registration_date')[:10]
        context['categories'] = Category.objects.annotate(
            event_count=Count('events')
        )
        return context


class AdminEventListView(LoginRequiredMixin, OrganizerRequiredMixin, ListView):
    """Admin event management list."""
    model = Event
    template_name = 'events/admin_event_list.html'
    context_object_name = 'events'
    paginate_by = 15

    def get_queryset(self):
        return managed_events(self.request.user, Event.objects.select_related('category', 'organizer')).annotate(
            reg_count=Count('registrations', distinct=True)
        ).order_by('-created_at')


class EventCreateView(LoginRequiredMixin, OrganizerRequiredMixin, EventFormUserMixin, CreateView):
    """Create a new event."""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:admin_event_list')

    def get_initial(self):
        initial = super().get_initial()
        initial['organizer'] = self.request.user
        return initial

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            form.instance.organizer = self.request.user
        messages.success(self.request, 'Event created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create New Event'
        context['btn_label'] = 'Create Event'
        return context


class EventUpdateView(LoginRequiredMixin, OrganizerRequiredMixin, ManagedEventMixin, EventFormUserMixin, UpdateView):
    """Update an existing event."""
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:admin_event_list')

    def form_valid(self, form):
        messages.success(self.request, 'Event updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Edit: {self.object.title}'
        context['btn_label'] = 'Save Changes'
        return context


class EventDeleteView(LoginRequiredMixin, OrganizerRequiredMixin, ManagedEventMixin, DeleteView):
    """Delete an event."""
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('events:admin_event_list')

    def get_queryset(self):
        queryset = Event.objects.all()
        return queryset if self.request.user.is_superuser else queryset.filter(organizer=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Event deleted successfully.')
        return super().form_valid(form)


class EventParticipantsView(LoginRequiredMixin, OrganizerRequiredMixin, ManagedEventMixin, DetailView):
    """View participants for a specific event."""
    model = Event
    template_name = 'events/event_participants.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        context['registrations'] = Registration.objects.filter(
            event=event
        ).select_related('user').order_by('status', '-registration_date')
        return context


class AdminUserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin user management."""
    model = User
    template_name = 'events/admin_user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.select_related('coordinator_application').annotate(
            reg_count=Count('registrations')
        ).order_by('-date_joined')


class ToggleUserStatusView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Toggle user active/inactive status."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User "{user.username}" has been {status}.')
        return redirect('events:admin_user_list')


class ToggleOrganizerStatusView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Toggle user organizer (staff) status."""
    
    def post(self, request, pk):
        if not request.user.is_superuser:
            messages.error(request, "Only Superusers can grant or revoke organizer access.")
            return redirect('events:admin_user_list')
            
        user = get_object_or_404(User, pk=pk)
        if user == request.user or user.is_superuser:
            messages.error(request, "You cannot modify organizer status for this user.")
        else:
            user.is_staff = not user.is_staff
            user.save()
            from accounts.models import CoordinatorApplication
            CoordinatorApplication.objects.filter(user=user).update(
                status='approved' if user.is_staff else 'revoked'
            )
            status = 'granted organizer access to' if user.is_staff else 'revoked organizer access from'
            messages.success(request, f'Successfully {status} "{user.username}".')
        return redirect('events:admin_user_list')


class CategoryEventView(ListView):
    """Events filtered by category."""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 9

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return Event.objects.filter(category=self.category).select_related('category', 'organizer')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.category
        context['search_form'] = EventSearchForm()
        context['categories'] = Category.objects.annotate(event_count=Count('events'))
        return context


class AboutView(TemplateView):
    """About page."""
    template_name = 'events/about.html'


# ─────────── ATTENDANCE VIEWS ───────────

class AttendanceDashboardView(LoginRequiredMixin, OrganizerRequiredMixin, ManagedEventMixin, DetailView):
    model = Event
    template_name = 'events/attendance_dashboard.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        session = event.attendance_sessions.filter(is_active=True).first()
        if not session:
            session = event.attendance_sessions.order_by('-created_at').first()
            
        context['session'] = session
        context['session_active'] = bool(session and session.is_active and session.token_expires_at and session.token_expires_at > timezone.now())

        # Stats
        total_registered = event.registrations.filter(status='confirmed').count()
        present = AttendanceRecord.objects.filter(session__event=event, user__registrations__event=event, user__registrations__status='confirmed').values('user_id').distinct().count()
        absent = total_registered - present
        percentage = round((present / total_registered * 100), 1) if total_registered > 0 else 0
        
        context['total_registered'] = total_registered
        context['present_count'] = present
        context['absent_count'] = absent
        context['attendance_percentage'] = percentage
        context['recent_checkins'] = AttendanceRecord.objects.filter(session__event=event).select_related('user').order_by('-scanned_at')[:50]
        
        return context


class AttendanceExportView(LoginRequiredMixin, OrganizerRequiredMixin, View):
    """Download one attendance row per confirmed participant."""
    def get(self, request, slug):
        event = get_object_or_404(managed_events(request.user, Event.objects.all()), slug=slug)
        present_ids = set(AttendanceRecord.objects.filter(session__event=event).values_list('user_id', flat=True))
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="attendance.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Username', 'Branch', 'Class / year', 'Roll number', 'Attendance'])
        def safe(value):
            value = str(value or '')
            return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value
        for reg in event.registrations.filter(status='confirmed').select_related('user').order_by('user__username'):
            writer.writerow([safe(reg.user.get_full_name()), safe(reg.user.username), safe(reg.branch), safe(reg.student_class), safe(reg.roll_number), 'Present' if reg.user_id in present_ids else 'Absent'])
        return response


class GenerateQRView(LoginRequiredMixin, OrganizerRequiredMixin, View):
    def post(self, request, slug):
        event = get_object_or_404(managed_events(request.user, Event.objects.all()), slug=slug)
        session = event.attendance_sessions.order_by('-created_at').first()
        if not session:
            session = AttendanceSession.objects.create(event=event)
        event.attendance_sessions.exclude(pk=session.pk).filter(is_active=True).update(is_active=False)
        session.generate_new_token(duration_minutes=5)
        messages.success(request, 'New Attendance QR Generated!')
        return redirect('events:display_qr', slug=slug)


class DisplayQRView(LoginRequiredMixin, OrganizerRequiredMixin, ManagedEventMixin, DetailView):
    model = Event
    template_name = 'events/qr_display.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        session = event.attendance_sessions.filter(is_active=True).first()
        
        if session and session.token_expires_at and session.token_expires_at > timezone.now():
            url = self.request.build_absolute_uri(reverse_lazy('events:scan_qr', kwargs={'token': session.current_qr_token}))
            context['qr_data'] = url
            image = qrcode.make(url)
            output = BytesIO()
            image.save(output, format='PNG')
            context['qr_image'] = base64.b64encode(output.getvalue()).decode('ascii')
            context['local_address'] = self.request.get_host().split(':')[0] in ('localhost', '127.0.0.1', '0.0.0.0', '[::1]')
            context['session'] = session
            # seconds left
            context['seconds_left'] = int((session.token_expires_at - timezone.now()).total_seconds())
        else:
            context['qr_data'] = None
            if session:
                session.is_active = False
                session.save()
        return context


class ParticipantScannerView(LoginRequiredMixin, TemplateView):
    template_name = 'events/participant_scanner.html'


class ScanQRView(LoginRequiredMixin, View):
    def get(self, request, token):
        session = AttendanceSession.objects.filter(current_qr_token=token, is_active=True).first()
        
        if not session:
            messages.error(request, 'This attendance QR has expired or is invalid.')
            return render(request, 'events/scan_error.html', {'error': 'Invalid or expired QR code.'})
            
        if not session.token_expires_at or session.token_expires_at <= timezone.now():
            session.is_active = False
            session.save()
            messages.error(request, 'This attendance QR has expired.')
            return render(request, 'events/scan_error.html', {'error': 'QR code has expired.'})
            
        event = session.event
        
        # Check registration
        if not Registration.objects.filter(event=event, user=request.user, status='confirmed').exists():
            messages.error(request, 'You are not registered for this event.')
            return render(request, 'events/scan_error.html', {'error': 'Not registered for this event.'})
            
        # Check if already marked
        if AttendanceRecord.objects.filter(session=session, user=request.user).exists():
            messages.warning(request, 'Attendance has already been recorded.')
            return render(request, 'events/scan_error.html', {'error': 'Attendance already recorded.'})
            
        return render(request, 'events/scan_confirm.html', {'event': event, 'token': token})


class ConfirmAttendanceView(LoginRequiredMixin, View):
    def post(self, request, token):
        session = AttendanceSession.objects.filter(current_qr_token=token, is_active=True).first()
        if not session or not session.token_expires_at or session.token_expires_at <= timezone.now():
            messages.error(request, 'QR expired. Please scan the latest QR on the screen.')
            return redirect('events:home')
            
        if not Registration.objects.filter(event=session.event, user=request.user, status='confirmed').exists():
            messages.error(request, 'You are not registered for this event.')
            return redirect('events:home')
            
        # Prevent duplicate
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={'status': 'present'}
        )
        
        if created:
            messages.success(request, f'✓ Your attendance has been recorded successfully for {session.event.title}.')
        else:
            messages.info(request, 'Attendance was already marked.')
            
        return redirect('events:user_dashboard')
