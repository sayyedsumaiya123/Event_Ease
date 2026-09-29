from django import forms
from .models import Event, Category, EventFeedback
from django.utils.text import slugify


class EventForm(forms.ModelForm):
    """Form for creating/editing events."""

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'short_description', 'organizer', 'category',
            'date', 'time', 'end_date', 'end_time',
            'venue', 'venue_address', 'capacity',
            'image', 'status', 'is_free', 'price', 'tags', 'featured'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'organizer': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue name'}),
            'venue_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tech, workshop, AI (comma-separated)'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tech, workshop, AI (comma-separated)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['organizer'].queryset = User.objects.filter(is_staff=True)
        self.fields['organizer'].empty_label = "Select Organizer"

    def save(self, commit=True):
        event = super().save(commit=False)
        if not event.slug:
            base_slug = slugify(event.title)
            slug = base_slug
            counter = 1
            from .models import Event
            while Event.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            event.slug = slug
        if commit:
            event.save()
        return event


class EventSearchForm(forms.Form):
    """Search and filter form for events."""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search events...',
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status'), ('upcoming', 'Upcoming'), ('ongoing', 'Ongoing'), ('completed', 'Completed')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class FeedbackForm(forms.ModelForm):
    """Feedback form for events."""

    class Meta:
        model = EventFeedback
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Share your experience...'}),
        }
