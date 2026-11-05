from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import CoordinatorRegisterForm
from .models import CoordinatorApplication


class CoordinatorFlowTests(TestCase):
    def data(self, **changes):
        data = dict(first_name='Event', last_name='Coordinator', username='event_coordinator',
                    email='coordinator@example.com', phone='+919876543210', organization='Event Club',
                    event_type='technical', expected_attendees=100,
                    event_plan='We plan hands-on technical workshops for students.',
                    password1='StrongDemoPass!829', password2='StrongDemoPass!829')
        data.update(changes)
        return data

    def apply(self):
        response = self.client.post(reverse('accounts:coordinator_register'), self.data(is_staff=True, is_superuser=True))
        self.assertRedirects(response, reverse('accounts:coordinator_panel'))
        return User.objects.get(username='event_coordinator')

    def test_registration_stores_answers_without_granting_permissions(self):
        user = self.apply()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.coordinator_application.status, 'pending')
        self.assertEqual(user.coordinator_application.event_type, 'technical')
        self.assertEqual(user.profile.phone, '+919876543210')
        self.assertContains(self.client.get(reverse('accounts:coordinator_panel')), 'pending administrator approval')
        self.assertEqual(self.client.get(reverse('events:event_create')).status_code, 403)

    def test_regex_and_question_validation(self):
        for bad in (dict(username='bad name!'), dict(phone='not-a-phone'), dict(phone='123'),
                    dict(event_type='unknown'), dict(expected_attendees=0), dict(event_plan='short')):
            with self.subTest(bad=bad):
                self.assertFalse(CoordinatorRegisterForm(self.data(**bad)).is_valid())
        self.assertFalse(User.objects.exists())

    def test_duplicate_email_case_is_rejected(self):
        User.objects.create_user('existing', email='COORDINATOR@example.com')
        self.assertFalse(CoordinatorRegisterForm(self.data()).is_valid())

    def test_member_cannot_use_coordinator_login_or_panel(self):
        user = User.objects.create_user('attendee', password='StrongDemoPass!829')
        response = self.client.post(reverse('accounts:coordinator_login'), dict(username=user.username, password='StrongDemoPass!829'))
        self.assertContains(response, 'not registered as an event coordinator')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('accounts:coordinator_panel')).status_code, 403)

    def test_pending_applicant_can_login_and_admin_can_approve_and_revoke(self):
        user = self.apply()
        self.client.logout()
        response = self.client.post(reverse('accounts:coordinator_login'), dict(username=user.username, password='StrongDemoPass!829'))
        self.assertRedirects(response, reverse('accounts:coordinator_panel'))
        admin = User.objects.create_superuser('reviewer', password='StrongDemoPass!829')
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('events:admin_user_list')), 'Approve Coordinator')
        self.client.post(reverse('events:toggle_organizer_status', args=[user.pk]))
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(CoordinatorApplication.objects.get(user=user).status, 'approved')
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('accounts:coordinator_panel')), 'Events I created')
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 403)
        self.client.force_login(admin)
        self.client.post(reverse('events:toggle_organizer_status', args=[user.pk]))
        self.assertEqual(CoordinatorApplication.objects.get(user=user).status, 'revoked')
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('accounts:coordinator_panel')), 'has been revoked')
        self.assertEqual(self.client.get(reverse('events:event_create')).status_code, 403)

    def test_legacy_organizer_without_application_can_login(self):
        User.objects.create_user('legacy', password='StrongDemoPass!829', is_staff=True)
        self.assertRedirects(self.client.post(reverse('accounts:coordinator_login'), dict(username='legacy', password='StrongDemoPass!829')), reverse('accounts:coordinator_panel'))

    def test_guest_can_find_coordinator_buttons(self):
        for route in ('accounts:login', 'accounts:register'):
            response = self.client.get(reverse(route))
            self.assertContains(response, 'Register as Coordinator')
            self.assertContains(response, reverse('accounts:coordinator_login'))

class CoordinatorReviewAndPanelTests(TestCase):
    def setUp(self):
        from events.models import Event
        from datetime import timedelta, time
        from django.utils import timezone
        self.organizer = User.objects.create_user('review_organizer', password='StrongDemoPass!829', is_staff=True)
        self.organizer.profile.is_organizer = True
        self.organizer.profile.save()
        self.coordinator = User.objects.create_user('approved_coordinator', password='StrongDemoPass!829', is_staff=True)
        self.candidate = User.objects.create_user('pending_candidate', password='StrongDemoPass!829')
        self.application = CoordinatorApplication.objects.create(user=self.candidate, organization='Campus Club', event_type='technical', expected_attendees=40, event_plan='Plan a hands-on workshop for students.')
        self.event = Event.objects.create(title='Owned Event', slug='owned-event', description='A test', date=timezone.localdate()+timedelta(days=10), time=time(12), venue='Hall', organizer=self.organizer)
        self.event.coordinators.add(self.coordinator)
        self.url = reverse('accounts:coordinator_application_decision', args=[self.application.pk])

    def test_organizer_sees_directory_assignments_and_can_approve(self):
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('accounts:coordinator_panel'))
        for text in ('Coordinator applications', 'pending_candidate', 'approved_coordinator', 'Owned Event'):
            self.assertContains(response, text)
        self.assertEqual(self.client.post(self.url, {'decision': 'approve'}).status_code, 302)
        self.application.refresh_from_db()
        self.candidate.refresh_from_db()
        self.assertEqual(self.application.status, 'approved')
        self.assertTrue(self.candidate.is_staff)
        self.assertFalse(self.candidate.profile.is_organizer)

    def test_organizer_can_reject_without_granting_access(self):
        self.client.force_login(self.organizer)
        self.client.post(self.url, {'decision': 'reject'})
        self.application.refresh_from_db()
        self.candidate.refresh_from_db()
        self.assertEqual(self.application.status, 'rejected')
        self.assertFalse(self.candidate.is_staff)
        self.client.force_login(self.candidate)
        self.assertContains(self.client.get(reverse('accounts:coordinator_panel')), 'was not approved')

    def test_coordinator_cannot_review_applications(self):
        self.client.force_login(self.coordinator)
        self.assertEqual(self.client.post(self.url, {'decision': 'approve'}).status_code, 403)
        self.assertNotContains(self.client.get(reverse('accounts:coordinator_panel')), 'Coordinator applications')
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')

    def test_coordinator_sees_assigned_event_but_not_other_teams(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('accounts:coordinator_panel'))
        self.assertContains(response, 'Events assigned to me')
        self.assertContains(response, 'Owned Event')
        self.assertNotContains(response, 'Coordinator access by event')

    def test_organizer_does_not_see_coordinator_assignment_card(self):
        self.client.force_login(self.organizer)
        response = self.client.get(reverse('accounts:coordinator_panel'))
        self.assertNotContains(response, 'Events assigned to me')
        self.assertContains(response, 'Events I created')
        self.client.force_login(self.coordinator)
        self.assertContains(self.client.get(reverse('accounts:coordinator_panel')), 'Events assigned to me')
