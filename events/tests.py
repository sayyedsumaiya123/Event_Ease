"""
Automated tests for EventEase Event Management System.
Tests cover: models, views, registration logic, admin access control.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, time, timedelta

from .models import Event, Category, Registration, EventFeedback


# ─────────────────────────────────────────
# Helper factories
# ─────────────────────────────────────────

def create_user(username='testuser', password='Test@1234', is_staff=False):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password=password,
        is_staff=is_staff
    )
    return user


def create_category(name='Tech', slug='tech'):
    return Category.objects.create(name=name, slug=slug)


def create_event(organizer, category=None, title='Test Event', status='upcoming',
                 capacity=100, days_ahead=10):
    return Event.objects.create(
        title=title,
        slug=title.lower().replace(' ', '-'),
        description='A test event description',
        category=category,
        date=date.today() + timedelta(days=days_ahead),
        time=time(10, 0),
        venue='Test Venue',
        capacity=capacity,
        status=status,
        organizer=organizer,
    )


# ─────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────

class CategoryModelTest(TestCase):
    def test_category_str(self):
        cat = create_category()
        self.assertEqual(str(cat), 'Tech')

    def test_category_unique_slug(self):
        create_category()
        with self.assertRaises(Exception):
            create_category()  # Duplicate slug should fail


class EventModelTest(TestCase):
    def setUp(self):
        self.organizer = create_user('organizer')
        self.category = create_category()

    def test_event_str(self):
        event = create_event(self.organizer, self.category, title='Tech Fest')
        self.assertEqual(str(event), 'Tech Fest')

    def test_available_seats_initially_equal_capacity(self):
        event = create_event(self.organizer, capacity=50)
        self.assertEqual(event.available_seats, 50)

    def test_available_seats_decreases_on_registration(self):
        event = create_event(self.organizer, capacity=10)
        user = create_user('registrant')
        Registration.objects.create(user=user, event=event, status='confirmed')
        self.assertEqual(event.available_seats, 9)

    def test_is_full_when_capacity_reached(self):
        event = create_event(self.organizer, capacity=1)
        user = create_user('registrant2')
        Registration.objects.create(user=user, event=event, status='confirmed')
        self.assertTrue(event.is_full)

    def test_event_not_full_when_capacity_not_reached(self):
        event = create_event(self.organizer, capacity=10)
        self.assertFalse(event.is_full)

    def test_short_description_auto_generated(self):
        event = create_event(self.organizer, title='Auto Desc Test')
        # Short description should be set from description
        self.assertIsNotNone(event.short_description)

    def test_registration_percentage(self):
        event = create_event(self.organizer, capacity=10)
        user = create_user('pct_user')
        Registration.objects.create(user=user, event=event, status='confirmed')
        self.assertEqual(event.registration_percentage, 10)


class RegistrationModelTest(TestCase):
    def setUp(self):
        self.organizer = create_user('org')
        self.user = create_user('reg_user')
        self.event = create_event(self.organizer, title='Reg Event')

    def test_registration_str(self):
        reg = Registration.objects.create(user=self.user, event=self.event, status='confirmed')
        self.assertIn('reg_user', str(reg))
        self.assertIn('Reg Event', str(reg))

    def test_ticket_number_auto_generated(self):
        reg = Registration.objects.create(user=self.user, event=self.event)
        self.assertTrue(reg.ticket_number.startswith('EE-'))
        self.assertEqual(len(reg.ticket_number), 11)  # 'EE-' + 8 chars

    def test_unique_registration_per_user_event(self):
        Registration.objects.create(user=self.user, event=self.event)
        with self.assertRaises(Exception):
            Registration.objects.create(user=self.user, event=self.event)


# ─────────────────────────────────────────
# View Tests
# ─────────────────────────────────────────

class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_page_loads(self):
        response = self.client.get(reverse('events:home'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_uses_correct_template(self):
        response = self.client.get(reverse('events:home'))
        self.assertTemplateUsed(response, 'events/home.html')


class EventListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = create_user('ev_org')
        self.cat = create_category()
        create_event(self.organizer, self.cat, title='Event A')
        create_event(self.organizer, self.cat, title='Event B')

    def test_event_list_loads(self):
        response = self.client.get(reverse('events:event_list'))
        self.assertEqual(response.status_code, 200)

    def test_event_list_shows_events(self):
        response = self.client.get(reverse('events:event_list'))
        self.assertContains(response, 'Event A')
        self.assertContains(response, 'Event B')

    def test_event_search_by_title(self):
        response = self.client.get(reverse('events:event_list') + '?q=Event+A')
        self.assertContains(response, 'Event A')

    def test_event_filter_by_status(self):
        response = self.client.get(reverse('events:event_list') + '?status=upcoming')
        self.assertEqual(response.status_code, 200)


class EventDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = create_user('det_org')
        self.event = create_event(self.organizer, title='Detail Test Event')

    def test_event_detail_loads(self):
        response = self.client.get(reverse('events:event_detail', kwargs={'slug': self.event.slug}))
        self.assertEqual(response.status_code, 200)

    def test_event_detail_shows_title(self):
        response = self.client.get(reverse('events:event_detail', kwargs={'slug': self.event.slug}))
        self.assertContains(response, 'Detail Test Event')


# ─────────────────────────────────────────
# Registration Tests
# ─────────────────────────────────────────

class EventRegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = create_user('r_org')
        self.user = create_user('r_user')
        self.event = create_event(self.organizer, title='Registration Test', capacity=10)

    def test_registration_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.post(
            reverse('events:event_register', kwargs={'slug': self.event.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_successful_registration(self):
        """Valid credentials and available seats → Registration successful."""
        self.client.login(username='r_user', password='Test@1234')
        response = self.client.post(
            reverse('events:event_register', kwargs={'slug': self.event.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Registration.objects.filter(user=self.user, event=self.event, status='confirmed').exists()
        )

    def test_duplicate_registration_rejected(self):
        """Already registered → Registration rejected."""
        self.client.login(username='r_user', password='Test@1234')
        # Register once
        self.client.post(reverse('events:event_register', kwargs={'slug': self.event.slug}))
        # Try to register again
        self.client.post(reverse('events:event_register', kwargs={'slug': self.event.slug}))
        count = Registration.objects.filter(user=self.user, event=self.event).count()
        self.assertEqual(count, 1)  # Should still be only 1

    def test_full_event_adds_to_waitlist(self):
        """Event full → Registration added to waitlist."""
        # Fill the event
        full_event = create_event(self.organizer, title='Full Event', capacity=1)
        other_user = create_user('other_user')
        Registration.objects.create(user=other_user, event=full_event, status='confirmed')

        self.client.login(username='r_user', password='Test@1234')
        self.client.post(reverse('events:event_register', kwargs={'slug': full_event.slug}))
        reg = Registration.objects.filter(user=self.user, event=full_event).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.status, 'waitlisted')

    def test_cancel_registration(self):
        """User can cancel their own registration."""
        self.client.login(username='r_user', password='Test@1234')
        Registration.objects.create(user=self.user, event=self.event, status='confirmed')
        response = self.client.post(
            reverse('events:cancel_registration', kwargs={'slug': self.event.slug})
        )
        self.assertEqual(response.status_code, 302)
        reg = Registration.objects.get(user=self.user, event=self.event)
        self.assertEqual(reg.status, 'cancelled')


# ─────────────────────────────────────────
# Admin Access Tests
# ─────────────────────────────────────────

class AdminAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.normal_user = create_user('normal')
        self.admin_user = create_user('staff_user', is_staff=True)
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.organizer = create_user('ad_org', is_staff=True)
        self.event = create_event(self.organizer, title='Admin Test Event')

    def test_admin_dashboard_requires_admin(self):
        """Normal users cannot access admin dashboard."""
        self.client.login(username='normal', password='Test@1234')
        response = self.client.get(reverse('events:admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_accessible_by_superuser(self):
        """Administrators can access the global dashboard."""
        self.client.login(username='staff_user', password='Test@1234')
        response = self.client.get(reverse('events:admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_event_create_requires_staff(self):
        """Normal user cannot create events."""
        self.client.login(username='normal', password='Test@1234')
        response = self.client.get(reverse('events:event_create'))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_event(self):
        """Staff user can access event creation form."""
        self.client.login(username='staff_user', password='Test@1234')
        response = self.client.get(reverse('events:event_create'))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_delete_event(self):
        """Staff user can delete events."""
        self.client.login(username='ad_org', password='Test@1234')
        response = self.client.post(
            reverse('events:event_delete', kwargs={'slug': self.event.slug})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(slug=self.event.slug).exists())


class OrganizerPermissionTest(TestCase):
    def setUp(self):
        self.organizer = create_user('owner', is_staff=True)
        self.other = create_user('other-owner', is_staff=True)
        self.member = create_user('member')
        self.admin = User.objects.create_superuser('superadmin', password='Test@1234')
        self.own = create_event(self.organizer, title='Owned Event')
        self.foreign = create_event(self.other, title='Other Event')
        self.client.force_login(self.organizer)

    def test_organizer_cannot_access_admin_or_change_users(self):
        for name in ('events:admin_dashboard', 'events:admin_user_list', 'admin:index', 'admin:login'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        for name in ('events:toggle_user_status', 'events:toggle_organizer_status'):
            self.assertEqual(self.client.post(reverse(name, args=[self.member.pk])).status_code, 403)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)
        self.assertFalse(self.member.is_staff)

    def test_organizer_only_sees_own_events(self):
        response = self.client.get(reverse('events:admin_event_list'))
        self.assertEqual(list(response.context['events']), [self.own])
        self.assertContains(response, 'Manage My Events')
        self.assertNotContains(response, 'dropdown-toggle" href="#" data-bs-toggle="dropdown">Admin')
        self.assertNotContains(response, reverse('events:admin_user_list'))

    def test_foreign_event_get_and_post_are_blocked(self):
        routes = {'event_edit': ('get', 'post'), 'event_delete': ('get', 'post'),
                  'event_participants': ('get',), 'attendance_dashboard': ('get',),
                  'display_qr': ('get',), 'generate_qr': ('post',)}
        for name, methods in routes.items():
            url = reverse('events:' + name, args=[self.foreign.slug])
            for method in methods:
                with self.subTest(name=name, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 404)
        self.assertTrue(Event.objects.filter(pk=self.foreign.pk).exists())
        self.assertFalse(self.foreign.attendance_sessions.exists())

    def test_owner_can_access_event_tools(self):
        for name in ('event_edit', 'event_participants', 'attendance_dashboard', 'display_qr'):
            self.assertEqual(self.client.get(reverse('events:' + name, args=[self.own.slug])).status_code, 200)
        self.assertEqual(self.client.post(reverse('events:generate_qr', args=[self.own.slug])).status_code, 302)

    def event_data(self, title):
        return {'title': title, 'description': 'An event', 'date': '2027-01-01',
                'time': '10:00', 'venue': 'Hall', 'capacity': 20, 'status': 'upcoming',
                'price': '0', 'is_free': True, 'organizer': self.other.pk, 'featured': True}

    def test_create_and_update_cannot_transfer_ownership_or_promote(self):
        response = self.client.post(reverse('events:event_create'), self.event_data('Created Safely'))
        self.assertEqual(response.status_code, 302)
        created = Event.objects.get(title='Created Safely')
        self.assertEqual(created.organizer_id, self.organizer.pk)
        self.assertFalse(created.featured)
        response = self.client.post(reverse('events:event_edit', args=[self.own.slug]), self.event_data('Updated Safely'))
        self.assertEqual(response.status_code, 302)
        self.own.refresh_from_db()
        self.assertEqual(self.own.organizer_id, self.organizer.pk)
        self.assertFalse(self.own.featured)

    def test_event_controls_hidden_for_other_organizer(self):
        for event, allowed in ((self.own, True), (self.foreign, False)):
            response = self.client.get(reverse('events:event_detail', args=[event.slug]))
            self.assertEqual(response.context['can_manage_event'], allowed)

    def test_superuser_retains_full_access(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('events:admin_user_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('events:event_edit', args=[self.foreign.slug])).status_code, 200)
        self.assertEqual(self.client.get(reverse('events:admin_event_list')).context['events'].count(), 2)

    def test_revoked_organizer_cannot_use_event_tools(self):
        self.organizer.is_staff = False
        self.organizer.save()
        self.assertEqual(self.client.get(reverse('events:event_edit', args=[self.own.slug])).status_code, 403)
