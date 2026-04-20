"""
Commande Django pour synchroniser les données depuis KoboToolbox
Usage: python manage.py sync_kobo
"""

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
        
        self.stdout.write("Début de la synchronisation Kobo...")
        
        try:
            if sync_type == 'creations':
                count = service.sync_creations()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Synchronisation terminée: {count} créations importées")
                )
            elif sync_type == 'suivis':
                count = service.sync_suivis()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Synchronisation terminée: {count} suivis importés")
                )
            else:
                creations, suivis = service.sync_all()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Synchronisation terminée: {creations} créations, {suivis} suivis importés"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Erreur lors de la synchronisation: {str(e)}")
            )
            raise e