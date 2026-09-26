from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Home
    path('', views.HomeView.as_view(), name='home'),

    # Events
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('events/<slug:slug>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<slug:slug>/register/', views.EventRegisterView.as_view(), name='event_register'),
    path('events/<slug:slug>/cancel/', views.CancelRegistrationView.as_view(), name='cancel_registration'),

    # Dashboard
    path('dashboard/', views.UserDashboardView.as_view(), name='user_dashboard'),

    # Admin Panel
    path('admin-panel/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-panel/events/', views.AdminEventListView.as_view(), name='admin_event_list'),
    path('admin-panel/events/create/', views.EventCreateView.as_view(), name='event_create'),
    path('admin-panel/events/<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_edit'),
    path('admin-panel/events/<slug:slug>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    path('admin-panel/events/<slug:slug>/participants/', views.EventParticipantsView.as_view(), name='event_participants'),
    path('admin-panel/users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('admin-panel/users/<int:pk>/toggle/', views.ToggleUserStatusView.as_view(), name='toggle_user_status'),

    # Category
    path('category/<slug:slug>/', views.CategoryEventView.as_view(), name='category_events'),

    # About
    path('about/', views.AboutView.as_view(), name='about'),
]
