"""
Commande Django pour synchroniser les données depuis KoboToolbox
Usage: python manage.py sync_kobo
"""

import traceback
from django.core.management.base import BaseCommand
from apps.kobo_sync.services import KoboService


class Command(BaseCommand):
    help = 'Synchronise les données depuis les formulaires KoboToolbox'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['creations', 'suivis', 'all'],
            default='all',
            help='Type de données à synchroniser'
        )

    def handle(self, *args, **options):
        service = KoboService()
        sync_type = options['type']

        self.stdout.write("Debut de la synchronisation Kobo...")

        try:
            if sync_type == 'creations':
                count = service.sync_creations()
                self.stdout.write(f"OK - Synchronisation terminee: {count} creations importees")
            elif sync_type == 'suivis':
                count = service.sync_suivis()
                self.stdout.write(f"OK - Synchronisation terminee: {count} suivis importes")
            else:
                creations, suivis = service.sync_all()
                self.stdout.write(
                    f"OK - Synchronisation terminee: {creations} creations, {suivis} suivis importes"
                )
        except Exception as e:
            self.stdout.write(f"ERREUR: {str(e)}")
            self.stdout.write(traceback.format_exc())
            raise e
