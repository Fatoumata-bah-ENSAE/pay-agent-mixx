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
    """
    Vue principale de la page Transport avec onglets Openers et Animateurs
    """
    # Récupérer la semaine sélectionnée ou prendre la semaine en cours
    semaine_str = request.GET.get('semaine')
    onglet = request.GET.get('onglet', 'openers')
    
    # Liste des semaines disponibles
    semaines_disponibles = TransportService.get_semaines_disponibles()
    
    # Formater les semaines pour l'affichage
    semaines_formatees = []
    for start, end in semaines_disponibles:
        semaines_formatees.append({
            'debut': start,
            'fin': end,
            'label': f"Semaine du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}",
            'value': f"{start.isoformat()}|{end.isoformat()}"
        })
    
    # Déterminer la semaine à afficher
    if semaine_str and '|' in semaine_str:
        start_str, end_str = semaine_str.split('|')
        date_debut = datetime.strptime(start_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(end_str, '%Y-%m-%d').date()
    elif semaines_formatees:
        # Prendre la dernière semaine disponible
        derniere = semaines_formatees[-1]
        date_debut = derniere['debut']
        date_fin = derniere['fin']
    else:
        # Semaine par défaut (avril 2026)
        date_debut = datetime(2026, 4, 13).date()
        date_fin = datetime(2026, 4, 19).date()
    
    context = {
        'onglet_actif': onglet,
        'semaines': semaines_formatees,
        'semaine_selectionnee': f"{date_debut.isoformat()}|{date_fin.isoformat()}",
        'date_debut': date_debut,
        'date_fin': date_fin,
    }

    # Charger les données selon l'onglet
    if onglet == 'openers':
        data = TransportService.calcul_openers_semaine(date_debut, date_fin)
        context.update({
            'agents': data['agents'],
            'total_transport': data['total_transport'],
            'total_agents': data['total_agents'],
            'performance_par_team': data.get('performance_par_team', {}),
            'meilleure_team': data.get('meilleure_team'),
            'service': TransportService,
        })
    else:  # animateurs
        data = TransportService.calcul_animateurs_semaine(date_debut, date_fin)
        context.update({
            'agents': data['agents'],
            'total_transport': data['total_transport'],
            'total_agents': data['total_agents'],
            'service': TransportService,
        })
    
    return render(request, 'paiements/transport.html', context)


@login_required
def get_detail_opener(request):
    """
    Vue AJAX pour récupérer le détail jour par jour d'un opener
    """
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
        
        # Calculer les totaux
        total_realisation = sum(j['realisation'] for j in jours)
        
        # Déterminer le transport
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
    """
    Vue AJAX pour récupérer le détail jour par jour d'un animateur
    """
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
        
        # Calculer les totaux
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
                    'volume': j['volume'],
                    'transport': j['transport']
                }
                for j in jours
            ],
            'total_volume': total_volume,
            'total_transport': total_transport,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def dashboard_view(request):
    """Page placeholder Tableau de bord"""
    return render(request, 'placeholders/dashboard.html')


@login_required
def salaire_view(request):
    """Page placeholder Salaire"""
    return render(request, 'placeholders/salaire.html')

@login_required
def export_excel_view(request):
    """
    Exporte les données au format Excel
    """
    from .exports import ExcelExport
    
    semaine_str = request.GET.get('semaine')
    onglet = request.GET.get('onglet', 'openers')
    
    if semaine_str and '|' in semaine_str:
        start_str, end_str = semaine_str.split('|')
        date_debut = datetime.strptime(start_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(end_str, '%Y-%m-%d').date()
    else:
        # Semaine par défaut
        date_debut = datetime(2026, 4, 13).date()
        date_fin = datetime(2026, 4, 19).date()
    
    if onglet == 'openers':
        return ExcelExport.export_openers(date_debut, date_fin)
    else:
        return ExcelExport.export_animateurs(date_debut, date_fin)