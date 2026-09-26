from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """Event category model."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-calendar-event')
    color = models.CharField(max_length=20, default='#6366f1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Event(models.Model):
    """Main event model."""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    date = models.DateField()
    time = models.TimeField()
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=300)
    venue_address = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=100)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return self.title

    @property
    def available_seats(self):
        registered = self.registrations.filter(status='confirmed').count()
        return max(0, self.capacity - registered)

    @property
    def is_full(self):
        return self.available_seats == 0

    @property
    def total_registrations(self):
        return self.registrations.filter(status='confirmed').count()

    @property
    def is_past(self):
        return self.date < timezone.now().date()

    @property
    def registration_percentage(self):
        if self.capacity == 0:
            return 0
        return int((self.total_registrations / self.capacity) * 100)

    def save(self, *args, **kwargs):
        if not self.short_description and self.description:
            self.short_description = self.description[:297] + '...' if len(self.description) > 300 else self.description
        super().save(*args, **kwargs)


class Registration(models.Model):
    """Event registration model."""
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('waitlisted', 'Waitlisted'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    notes = models.TextField(blank=True)
    ticket_number = models.CharField(max_length=20, unique=True, blank=True)

    class Meta:
        unique_together = ['user', 'event']
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.user.username} → {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            import uuid
            self.ticket_number = 'EE-' + str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)


class EventFeedback(models.Model):
    """Feedback/rating for attended events."""
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'event']

    def __str__(self):
        return f"{self.user.username} rated {self.event.title}: {self.rating}/5"
