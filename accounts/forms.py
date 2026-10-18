from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserProfile, CoordinatorApplication
from django.db import transaction


class RegisterForm(UserCreationForm):
    """Custom registration form with email and phone."""
    first_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    phone = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number (optional)'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            user.profile.phone = self.cleaned_data.get('phone', '')
            user.profile.save()
        return user


class CoordinatorRegisterForm(RegisterForm):
    username = forms.RegexField(
        regex=r'^[A-Za-z0-9_]{3,30}$', max_length=30,
        help_text='3–30 letters, numbers or underscores.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'pattern': '[A-Za-z0-9_]{3,30}'}),
        error_messages={'invalid': 'Use 3–30 letters, numbers or underscores.'},
    )
    phone = forms.RegexField(
        regex=r'^\+?[0-9]{10,15}$', max_length=16,
        help_text='10–15 digits, optionally starting with +.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'tel', 'maxlength': 16}),
        error_messages={'invalid': 'Enter 10–15 digits, optionally starting with +.'},
    )
    organization = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    event_type = forms.ChoiceField(label='What type of events will you organize?', choices=[('', 'Choose event type')] + CoordinatorApplication.EVENT_TYPES, widget=forms.Select(attrs={'class': 'form-select'}))
    expected_attendees = forms.IntegerField(label='How many attendees do you expect?', min_value=1, max_value=100000, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    event_plan = forms.CharField(label='Tell us about the events you plan to organize', min_length=20, max_length=1000, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    class Meta(RegisterForm.Meta):
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'organization',
                  'event_type', 'expected_attendees', 'event_plan', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.profile.organization = self.cleaned_data['organization']
            user.profile.save(update_fields=['organization'])
            CoordinatorApplication.objects.create(
                user=user, organization=self.cleaned_data['organization'],
                event_type=self.cleaned_data['event_type'],
                expected_attendees=self.cleaned_data['expected_attendees'],
                event_plan=self.cleaned_data['event_plan'],
            )
        return user


class LoginForm(AuthenticationForm):
    """Custom login form."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class CoordinatorLoginForm(LoginForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff or user.is_superuser or CoordinatorApplication.objects.filter(user=user).exists()):
            raise forms.ValidationError('This account is not registered as an event coordinator.', code='not_coordinator')


class ProfileUpdateForm(forms.ModelForm):
    """User profile update form."""
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ['phone', 'bio', 'organization', 'location', 'website', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }
