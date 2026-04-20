"""
URLs pour l'application de paiements
"""

from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    path('', views.transport_view, name='transport'),
    path('transport/', views.transport_view, name='transport'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('salaire/', views.salaire_view, name='salaire'),
    path('api/detail-opener/', views.get_detail_opener, name='detail_opener'),
    path('api/detail-animateur/', views.get_detail_animateur, name='detail_animateur'),
    path('export-excel/', views.export_excel_view, name='export_excel'),
]