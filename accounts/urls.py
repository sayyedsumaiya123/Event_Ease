from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('coordinator/register/', views.CoordinatorRegisterView.as_view(), name='coordinator_register'),
    path('coordinator/login/', views.CoordinatorLoginView.as_view(), name='coordinator_login'),
    path('coordinator/', views.CoordinatorPanelView.as_view(), name='coordinator_panel'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
]
