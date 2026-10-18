from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import EventForm
from .models import Event


class EventScheduleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('schedule-owner', is_staff=True)
        self.now = timezone.make_aware(datetime(2030, 6, 15, 12, 0))
        self.localtime = patch('events.models.timezone.localtime', return_value=self.now)
        self.localdate = patch('events.forms.timezone.localdate', return_value=self.now.date())
        self.localtime.start()
        self.localdate.start()
        self.addCleanup(self.localtime.stop)
        self.addCleanup(self.localdate.stop)

    def data(self, **changes):
        data = {'title': 'Valid Schedule', 'description': 'An event with a schedule',
                'organizer': self.user.pk, 'date': '2030-06-16', 'time': '14:00',
                'venue': 'Hall', 'capacity': 20, 'status': 'upcoming', 'price': '0'}
        data.update(changes)
        return data

    def test_rejects_yesterday_and_previous_year(self):
        for day in ('2030-06-14', '2029-06-15'):
            form = EventForm(self.data(date=day), user=self.user)
            self.assertFalse(form.is_valid())
            self.assertIn('date', form.errors)

    def test_today_requires_future_time(self):
        for start in ('11:00', '12:00'):
            form = EventForm(self.data(date='2030-06-15', time=start), user=self.user)
            self.assertFalse(form.is_valid())
            self.assertIn('time', form.errors)
        self.assertTrue(EventForm(self.data(date='2030-06-15', time='13:00'), user=self.user).is_valid())

    def test_end_must_follow_start(self):
        for changes, field in (({'end_date': '2030-06-15'}, 'end_date'),
                               ({'end_time': '13:00'}, 'end_time'),
                               ({'end_time': '14:00'}, 'end_time')):
            form = EventForm(self.data(**changes), user=self.user)
            self.assertFalse(form.is_valid())
            self.assertIn(field, form.errors)
        self.assertTrue(EventForm(self.data(end_date='2030-06-17', end_time='09:00'), user=self.user).is_valid())

    def test_direct_post_cannot_bypass_date_picker(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('events:event_create'), self.data(date='2029-01-01'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Events cannot start in the past.')
        self.assertFalse(Event.objects.exists())

    def test_historical_event_can_be_edited_without_rescheduling_into_past(self):
        event = Event.objects.create(title='Historical', slug='historical', description='Past',
                                     organizer=self.user, date=self.now.date() - timedelta(days=10),
                                     time='10:00', venue='Hall')
        event.refresh_from_db()
        form = EventForm(self.data(date=event.date.isoformat(), time='10:00', title='Updated history'), instance=event, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        form = EventForm(self.data(date='2029-01-01'), instance=event, user=self.user)
        self.assertFalse(form.is_valid())

    def test_model_validation_covers_django_admin(self):
        event = Event(title='Past', organizer=self.user, date=self.now.date() - timedelta(days=365), time='10:00')
        with self.assertRaises(ValidationError):
            event.clean()

    def test_new_form_picker_starts_at_local_today(self):
        self.assertEqual(EventForm(user=self.user).fields['date'].widget.attrs['min'], '2030-06-15')
