"""
Vue de synchronisation manuelle avec KoboToolbox
"""

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .services import KoboService


@login_required
@require_POST
def sync_view(request):
    """Déclenche la synchronisation Kobo depuis l'interface"""
    try:
        service = KoboService()
        creations, suivis = service.sync_all()
        return JsonResponse({
            'success': True,
            'message': f'Synchronisation terminée : {creations} créations, {suivis} suivis importés.',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
