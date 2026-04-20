"""
Configuration de l'interface d'administration pour les agents
"""

from django.contrib import admin
from .models import Agent, CreationMarchand, SuiviMarchand


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nom', 'equipe', 'team', 'get_roles', 'date_creation']
    list_filter = ['equipe', 'team', 'est_opener', 'est_animateur']
    search_fields = ['numero', 'nom']
    readonly_fields = ['date_creation', 'date_modification']


@admin.register(CreationMarchand)
class CreationMarchandAdmin(admin.ModelAdmin):
    list_display = ['numero_marchand', 'opener', 'equipe', 'team', 'date_activite']
    list_filter = ['equipe', 'team', 'type_structure', 'profil_marchand']
    search_fields = ['numero_marchand', 'opener__numero']
    readonly_fields = ['date_soumission']


@admin.register(SuiviMarchand)
class SuiviMarchandAdmin(admin.ModelAdmin):
    list_display = ['animateur', 'numero_marchand', 'montant', 'date_activite']
    list_filter = ['application_paiement', 'type_structure', 'profil_marchand']
    search_fields = ['animateur__numero', 'numero_marchand', 'numero_client']
    readonly_fields = ['date_soumission']