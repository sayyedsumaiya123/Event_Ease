from django import forms
from .models import Event, Category, EventFeedback
from django.utils.text import slugify
from django.utils import timezone


class EventForm(forms.ModelForm):
    """Form for creating/editing events."""

    coordinator = forms.ChoiceField(
        required=False, label='Coordinator for this event', widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Event
        fields = [
            'title',
            'description',
            'short_description',
            'organizer',
            'coordinator',
            'category',
            'date',
            'time',
            'end_date',
            'end_time',
            'venue',
            'venue_address',
            'capacity',
            'image',
            'status',
            'is_free',
            'price',
            'tags',
            'featured',
            'certificates_enabled',
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
            'tags': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'tech, workshop, AI (comma-separated)'}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        # Preserve the displayed schedule when editing historical event details.
        minimum_date = min(today, self.instance.date) if self.instance.pk and self.instance.date else today
        self.fields['date'].widget.attrs['min'] = minimum_date.isoformat()
        self.fields['end_date'].widget.attrs['min'] = minimum_date.isoformat()
        self.fields['date'].widget.format = '%Y-%m-%d'
        self.fields['end_date'].widget.format = '%Y-%m-%d'
        from django.contrib.auth import get_user_model

        User = get_user_model()
        from django.db.models import Q

        self.fields['organizer'].queryset = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True), is_active=True)
        self.fields['organizer'].empty_label = 'Select Organizer'
        available = User.objects.filter(
            is_active=True, is_staff=True, is_superuser=False, profile__is_organizer=False
        ).order_by('username')
        owner_id = self.instance.organizer_id if self.instance.pk else (user.pk if user else None)
        if owner_id:
            available = available.exclude(pk=owner_id)
        existing = list(self.instance.coordinators.order_by('username')) if self.instance.pk else []
        options = [('', 'None')]
        eligible_ids = {person.pk for person in available}
        needs_keep = len(existing) > 1 or any(person.pk not in eligible_ids for person in existing)
        if needs_keep:
            names = ', '.join(person.get_full_name() or person.username for person in existing)
            options.append(('__keep__', f'Keep current: {names}'))
            self.initial['coordinator'] = '__keep__'
            self.coordinator_keep_notice = True
        elif existing:
            self.initial['coordinator'] = str(existing[0].pk)
        options.extend(
            (str(person.pk), f'{person.get_full_name() or person.username} (@{person.username})')
            for person in available
        )
        self.fields['coordinator'].choices = options
        self.coordinator_options_available = bool(eligible_ids)
        if user is not None and not user.is_superuser:
            self.fields['organizer'].queryset = User.objects.filter(pk=owner_id)
            self.fields['organizer'].initial = owner_id
            self.initial['organizer'] = owner_id
            self.fields['organizer'].disabled = True
            self.fields['featured'].disabled = True
            if self.instance.pk and owner_id != user.pk:
                # Assigned coordinators can edit the event but cannot change its team.
                self.fields.pop('coordinator')

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
        save_model_relations = self.save_m2m

        def save_relations():
            save_model_relations()
            if 'coordinator' in self.cleaned_data:
                selection = self.cleaned_data['coordinator']
                if selection != '__keep__':
                    event.coordinators.set([int(selection)] if selection else [])

        self.save_m2m = save_relations
        if commit:
            event.save()
            self.save_m2m()
        return event


class EventSearchForm(forms.Form):
    """Search and filter form for events."""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Search events...',
            }
        ),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status'), ('upcoming', 'Upcoming'), ('ongoing', 'Ongoing'), ('completed', 'Completed')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))


class FeedbackForm(forms.ModelForm):
    """Feedback form for events."""

    class Meta:
        model = EventFeedback
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Share your experience...'}
            ),
        }
