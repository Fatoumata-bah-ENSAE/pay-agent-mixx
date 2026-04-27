"""
Services de calcul des paiements de transport
Logique métier pour openers et animateurs
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from ..agents.models import Agent, CreationMarchand, SuiviMarchand

JOURS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


class TransportService:
    """
    Service de calcul des transports pour openers et animateurs
    """

    # Constantes
    OBJECTIF_OPENER = 5  # 5 créations par semaine
    SEUIL_OPENER = 3     # Seuil minimal pour toucher le transport
    TRANSPORT_BASE_OPENER = 6000  # 6000 FCFA fixe
    PLAFOND_ANIMATEUR = Decimal('50000')  # 50000 FCFA max par semaine
    TAUX_ANIMATEUR = Decimal('0.10')     # 10% du volume journalier

    @staticmethod
    def get_semaine_dates(date_reference):
        """
        Retourne les dates de début et fin de semaine (lundi au dimanche)
        """
        if isinstance(date_reference, str):
            date_reference = datetime.strptime(date_reference, '%Y-%m-%d').date()
        
        # Trouver le lundi de la semaine
        start_of_week = date_reference - timedelta(days=date_reference.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        return start_of_week, end_of_week

    @staticmethod
    def get_semaines_disponibles():
        """
        Retourne la liste des semaines depuis le début du projet jusqu'à
        la semaine en cours — même si certaines n'ont pas encore de données.
        On ajoute aussi toutes les semaines qui ont des données réelles.
        """
        from datetime import date as date_type

        semaines = set()

        # ── Semaines avec données réelles ────────────────────────────────
        for d in CreationMarchand.objects.filter(
            date_activite__gte='2026-04-13'
        ).dates('date_activite', 'week'):
            semaines.add(TransportService.get_semaine_dates(d))

        for d in SuiviMarchand.objects.filter(
            date_activite__gte='2026-04-14'
        ).dates('date_activite', 'week'):
            semaines.add(TransportService.get_semaine_dates(d))

        # ── Toujours inclure toutes les semaines depuis le lancement ─────
        # (lundi 13 avril 2026 = première semaine du projet)
        lundi_lancement = date_type(2026, 4, 13)
        today = date_type.today()
        lundi_courant = today - timedelta(days=today.weekday())

        lundi = lundi_lancement
        while lundi <= lundi_courant:
            semaines.add((lundi, lundi + timedelta(days=6)))
            lundi += timedelta(weeks=1)

        return sorted(list(semaines), key=lambda x: x[0])

    @staticmethod
    def calcul_openers_semaine(date_debut_semaine, date_fin_semaine):
        """
        Calcule les performances et transports des openers pour une semaine donnée
        
        Retourne un dictionnaire avec :
        - agents : liste des openers avec leurs stats
        - total_transport : somme totale des transports
        - total_agents : nombre d'agents openers
        - performance_par_team : agrégation par team
        - meilleure_team : team avec le plus de créations
        """
        
        # Récupérer tous les agents qui ont le rôle opener
        openers = Agent.objects.filter(est_opener=True)
        
        resultats = []
        total_transport = 0
        performance_par_team = {}
        
        for opener in openers:
            # Compter les créations dans la semaine
            creations = CreationMarchand.objects.filter(
                opener=opener,
                date_activite__gte=date_debut_semaine,
                date_activite__lte=date_fin_semaine
            ).count()
            
            # Calcul du transport
            if creations >= TransportService.SEUIL_OPENER:
                transport = TransportService.TRANSPORT_BASE_OPENER
                statut = "Atteint"
                couleur_statut = "#22C55E"
            else:
                transport = 0
                statut = "Non atteint"
                couleur_statut = "#EF4444"
            
            # Taux de réalisation
            taux = (creations / TransportService.OBJECTIF_OPENER) * 100 if creations > 0 else 0
            
            agent_data = {
                'agent': opener,
                'realisation': creations,
                'taux': round(taux, 1),
                'transport_base': TransportService.TRANSPORT_BASE_OPENER,
                'transport_net': transport,
                'statut': statut,
                'couleur_statut': couleur_statut,
                'objectif': TransportService.OBJECTIF_OPENER,
                'seuil': TransportService.SEUIL_OPENER,
            }
            
            resultats.append(agent_data)
            total_transport += transport
            
            # Agrégation par team
            team = opener.team if opener.team else "Sans team"
            if team not in performance_par_team:
                performance_par_team[team] = {
                    'creations': 0,
                    'agents': 0,
                    'transport': 0
                }
            performance_par_team[team]['creations'] += creations
            performance_par_team[team]['agents'] += 1
            performance_par_team[team]['transport'] += transport
        
        # Trier par performance (réalisation décroissante)
        resultats.sort(key=lambda x: x['realisation'], reverse=True)
        
        # Trouver la meilleure team
        meilleure_team = None
        meilleur_score = -1
        for team, stats in performance_par_team.items():
            if stats['creations'] > meilleur_score:
                meilleur_score = stats['creations']
                meilleure_team = {
                    'nom': team,
                    'creations': stats['creations'],
                    'agents': stats['agents']
                }
        
        return {
            'agents': resultats,
            'total_transport': total_transport,
            'total_agents': len(resultats),
            'performance_par_team': performance_par_team,
            'meilleure_team': meilleure_team,
            'date_debut': date_debut_semaine,
            'date_fin': date_fin_semaine,
        }

    @staticmethod
    def get_detail_journalier_opener(opener, date_debut_semaine, date_fin_semaine):
        """
        Retourne le détail jour par jour des créations d'un opener
        """
        jours = []
        current_date = date_debut_semaine
        
        while current_date <= date_fin_semaine:
            creations_jour = CreationMarchand.objects.filter(
                opener=opener,
                date_activite=current_date
            ).count()
            
            jours.append({
                'date': current_date,
                'jour_semaine': JOURS_FR[current_date.weekday()],
                'realisation': creations_jour,
            })
            current_date += timedelta(days=1)
        
        return jours

    @staticmethod
    def calcul_animateurs_semaine(date_debut_semaine, date_fin_semaine):
        """
        Calcule les performances et transports des animateurs pour une semaine donnée
        
        Retourne un dictionnaire avec :
        - agents : liste des animateurs avec leurs stats
        - total_transport : somme totale des transports
        - total_agents : nombre d'agents animateurs
        """
        
        # Récupérer tous les agents qui ont le rôle animateur
        animateurs = Agent.objects.filter(est_animateur=True)
        
        resultats = []
        total_transport = 0
        
        for animateur in animateurs:
            # Récupérer tous les paiements de la semaine
            paiements = SuiviMarchand.objects.filter(
                animateur=animateur,
                date_activite__gte=date_debut_semaine,
                date_activite__lte=date_fin_semaine
            )
            
            # Calcul du volume total
            volume_total = paiements.aggregate(total=Sum('montant'))['total'] or 0
            
            # Calcul du transport (10% du volume, plafonné)
            transport = min(volume_total * TransportService.TAUX_ANIMATEUR, TransportService.PLAFOND_ANIMATEUR)
            
            agent_data = {
                'agent': animateur,
                'volume_realise': volume_total,
                'transport': transport,
            }
            
            resultats.append(agent_data)
            total_transport += transport
        
        # Trier par volume réalisé décroissant
        resultats.sort(key=lambda x: x['volume_realise'], reverse=True)
        
        return {
            'agents': resultats,
            'total_transport': total_transport,
            'total_agents': len(resultats),
            'date_debut': date_debut_semaine,
            'date_fin': date_fin_semaine,
        }

    @staticmethod
    def get_detail_journalier_animateur(animateur, date_debut_semaine, date_fin_semaine):
        """
        Retourne le détail jour par jour des volumes d'un animateur
        """
        jours = []
        current_date = date_debut_semaine
        
        while current_date <= date_fin_semaine:
            # Volume journalier
            volume_jour = SuiviMarchand.objects.filter(
                animateur=animateur,
                date_activite=current_date
            ).aggregate(total=Sum('montant'))['total'] or 0
            
            # Transport journalier (10% du volume)
            transport_jour = volume_jour * TransportService.TAUX_ANIMATEUR
            
            jours.append({
                'date': current_date,
                'jour_semaine': JOURS_FR[current_date.weekday()],
                'volume': volume_jour,
                'transport': transport_jour,
            })
            current_date += timedelta(days=1)
        
        return jours