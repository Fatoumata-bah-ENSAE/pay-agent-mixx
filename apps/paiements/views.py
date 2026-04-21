"""
Vues pour la gestion des paiements de transport
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from datetime import datetime, timedelta
from .services import TransportService


@login_required
def transport_view(request):
    semaine_str = request.GET.get('semaine')
    onglet = request.GET.get('onglet', 'openers')

    semaines_disponibles = TransportService.get_semaines_disponibles()

    semaines_formatees = []
    for start, end in semaines_disponibles:
        semaines_formatees.append({
            'debut': start,
            'fin': end,
            'label': f"Semaine du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}",
            'value': f"{start.isoformat()}|{end.isoformat()}"
        })

    if semaine_str and '|' in semaine_str:
        start_str, end_str = semaine_str.split('|')
        date_debut = datetime.strptime(start_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(end_str, '%Y-%m-%d').date()
    elif semaines_formatees:
        derniere = semaines_formatees[-1]
        date_debut = derniere['debut']
        date_fin = derniere['fin']
    else:
        date_debut = datetime(2026, 4, 13).date()
        date_fin = datetime(2026, 4, 19).date()

    # Toujours charger les deux jeux de données pour que les deux onglets fonctionnent
    openers_data = TransportService.calcul_openers_semaine(date_debut, date_fin)
    animateurs_data = TransportService.calcul_animateurs_semaine(date_debut, date_fin)

    context = {
        'onglet_actif': onglet,
        'semaines': semaines_formatees,
        'semaine_selectionnee': f"{date_debut.isoformat()}|{date_fin.isoformat()}",
        'date_debut': date_debut,
        'date_fin': date_fin,
        # Données openers
        'openers': openers_data['agents'],
        'openers_total_transport': openers_data['total_transport'],
        'openers_total_agents': openers_data['total_agents'],
        'openers_meilleure_team': openers_data.get('meilleure_team'),
        'openers_performance_par_team': openers_data.get('performance_par_team', {}),
        # Données animateurs
        'animateurs': animateurs_data['agents'],
        'animateurs_total_transport': animateurs_data['total_transport'],
        'animateurs_total_agents': animateurs_data['total_agents'],
        'service': TransportService,
    }

    return render(request, 'paiements/transport.html', context)


@login_required
def get_detail_opener(request):
    from django.http import JsonResponse
    from ..agents.models import Agent

    agent_id = request.GET.get('agent_id')
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')

    try:
        agent = Agent.objects.get(id=agent_id)
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()

        jours = TransportService.get_detail_journalier_opener(agent, date_debut, date_fin)

        total_realisation = sum(j['realisation'] for j in jours)

        if total_realisation >= TransportService.SEUIL_OPENER:
            transport = TransportService.TRANSPORT_BASE_OPENER
        else:
            transport = 0

        return JsonResponse({
            'success': True,
            'agent_nom': str(agent),
            'jours': [
                {
                    'date': j['date'].strftime('%d/%m/%Y'),
                    'jour_semaine': j['jour_semaine'],
                    'realisation': j['realisation']
                }
                for j in jours
            ],
            'total_realisation': total_realisation,
            'taux': round((total_realisation / TransportService.OBJECTIF_OPENER) * 100, 1),
            'transport': transport,
            'objectif': TransportService.OBJECTIF_OPENER,
            'seuil': TransportService.SEUIL_OPENER,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_detail_animateur(request):
    from django.http import JsonResponse
    from ..agents.models import Agent

    agent_id = request.GET.get('agent_id')
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')

    try:
        agent = Agent.objects.get(id=agent_id)
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()

        jours = TransportService.get_detail_journalier_animateur(agent, date_debut, date_fin)

        total_volume = sum(j['volume'] for j in jours)
        total_transport = sum(j['transport'] for j in jours)
        total_transport = min(total_transport, TransportService.PLAFOND_ANIMATEUR)

        return JsonResponse({
            'success': True,
            'agent_nom': str(agent),
            'jours': [
                {
                    'date': j['date'].strftime('%d/%m/%Y'),
                    'jour_semaine': j['jour_semaine'],
                    'volume': float(j['volume']),
                    'transport': float(j['transport'])
                }
                for j in jours
            ],
            'total_volume': float(total_volume),
            'total_transport': float(total_transport),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def dashboard_view(request):
    return render(request, 'placeholders/dashboard.html')


@login_required
def salaire_view(request):
    return render(request, 'placeholders/salaire.html')


@login_required
def export_excel_view(request):
    from .exports import ExcelExport
    import traceback

    semaine_str = request.GET.get('semaine')
    onglet = request.GET.get('onglet', 'openers')

    if semaine_str and '|' in semaine_str:
        start_str, end_str = semaine_str.split('|')
        date_debut = datetime.strptime(start_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(end_str, '%Y-%m-%d').date()
    else:
        date_debut = datetime(2026, 4, 13).date()
        date_fin = datetime(2026, 4, 19).date()

    try:
        if onglet == 'openers':
            return ExcelExport.export_openers(date_debut, date_fin)
        else:
            return ExcelExport.export_animateurs(date_debut, date_fin)
    except Exception as e:
        return HttpResponse(
            f"Erreur lors de l'export : {e}\n\n{traceback.format_exc()}",
            content_type='text/plain',
            status=500
        )
