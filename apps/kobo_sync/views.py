"""
Vue de synchronisation manuelle avec KoboToolbox
"""

import threading
import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .services import KoboService

logger = logging.getLogger(__name__)

_sync_lock = threading.Lock()
_sync_running = False


@login_required
@require_POST
def sync_view(request):
    """Déclenche la synchronisation Kobo en arrière-plan pour éviter le timeout HTTP."""
    global _sync_running

    with _sync_lock:
        if _sync_running:
            return JsonResponse({
                'success': False,
                'message': 'Synchronisation déjà en cours, veuillez patienter.'
            })
        _sync_running = True

    def run_sync():
        global _sync_running
        try:
            service = KoboService()
            service.sync_all()
        except Exception as e:
            logger.error(f"Erreur sync Kobo: {e}", exc_info=True)
        finally:
            _sync_running = False

    t = threading.Thread(target=run_sync, daemon=True)
    t.start()

    return JsonResponse({
        'success': True,
        'message': 'Synchronisation lancée. Rechargez la page dans 2-3 minutes pour voir les nouvelles données.',
        'async': True,
    })
