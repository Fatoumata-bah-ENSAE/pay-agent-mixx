"""
Configuration des URLs principales du projet
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from apps.kobo_sync.views import sync_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('sync/', sync_view, name='sync_kobo'),
    path('', include('apps.paiements.urls')),
]