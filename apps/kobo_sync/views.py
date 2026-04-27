"""
Vue de synchronisation manuelle avec KoboToolbox
"""

import threading
import time
import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .services import KoboService

logger = logging.getLogger(__name__)

_sync_lock = threading.Lock()
_sync_running = False
_sync_started_at = None   # timestamp de démarrage
SYNC_TIMEOUT = 600        # 10 minutes max avant reset automatique


@login_required
@require_POST
def sync_view(request):
    """Déclenche la synchronisation Kobo en arrière-plan pour éviter le timeout HTTP."""
    global _sync_running, _sync_started_at

    with _sync_lock:
        # Reset automatique si la sync tourne depuis plus de SYNC_TIMEOUT secondes
        if _sync_running and _sync_started_at:
            elapsed = time.time() - _sync_started_at
            if elapsed > SYNC_TIMEOUT:
                logger.warning(f"Sync bloquée depuis {elapsed:.0f}s — reset forcé.")
                _sync_running = False

        if _sync_running:
            elapsed = int(time.time() - _sync_started_at) if _sync_started_at else 0
            return JsonResponse({
                'success': False,
                'message': f'Synchronisation déjà en cours ({elapsed}s écoulées). Réessayez dans quelques instants.'
            })

        _sync_running = True
        _sync_started_at = time.time()

    def run_sync():
        global _sync_running, _sync_started_at
        try:
            service = KoboService()
            service.sync_all()
        except Exception as e:
            logger.error(f"Erreur sync Kobo: {e}", exc_info=True)
        finally:
            _sync_running = False
            _sync_started_at = None

    t = threading.Thread(target=run_sync, daemon=True)
    t.start()

    return JsonResponse({
        'success': True,
        'message': 'Synchronisation lancée. Rechargez la page dans 2-3 minutes pour voir les nouvelles données.',
        'async': True,
    })
