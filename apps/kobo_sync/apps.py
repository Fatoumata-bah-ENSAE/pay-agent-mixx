"""
Configuration de l'application kobo_sync
"""

from django.apps import AppConfig


class KoboSyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.kobo_sync'
    verbose_name = "Synchronisation Kobo"