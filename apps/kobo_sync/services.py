"""
Service de synchronisation avec l'API KoboToolbox
Récupération, mapping et insertion des données
"""

import requests
from datetime import datetime, timezone as utc
from django.conf import settings
from django.utils import timezone
from ..agents.models import Agent, CreationMarchand, SuiviMarchand


class KoboService:
    """
    Service d'intégration avec l'API KoboToolbox
    """
    
    def __init__(self):
        self.base_url = settings.KOBO_BASE_URL
        self.headers = {
            'Authorization': f'Token {settings.KOBO_TOKEN}'
        }
    
    def get_mappings(self, uid):
        """
        Récupère les mappings codes -> labels depuis l'API Kobo
        """
        url = f"{self.base_url}/api/v2/assets/{uid}/?format=json"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        mappings = {}

        # Construire d'abord le dictionnaire list_name -> {code: label}
        list_mappings = {}
        for choice in data.get('content', {}).get('choices', []):
            list_name = choice.get('list_name')
            code = choice.get('name')
            label = choice.get('label')
            if label and isinstance(label, list):
                label = next((l for l in label if l), code)
            if list_name and code:
                if list_name not in list_mappings:
                    list_mappings[list_name] = {}
                list_mappings[list_name][code] = label

        # Associer chaque champ select à ses choix via son list_name (utiliser name, pas $kuid)
        for item in data.get('content', {}).get('survey', []):
            if 'select_from_list_name' in item:
                field_name = item.get('name')
                list_name = item['select_from_list_name']
                if field_name and list_name in list_mappings:
                    mappings[field_name] = list_mappings[list_name]

        return mappings
    
    def convert_date(self, date_str):
        """
        Convertit une date ISO avec timezone en datetime UTC
        """
        if not date_str:
            return None
        
        # Remplacer Z par +00:00 si nécessaire
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        
        # Parser la date
        dt = datetime.fromisoformat(date_str)
        
        # Convertir en UTC
        if dt.tzinfo:
            dt = dt.astimezone(utc.UTC)
        else:
            dt = dt.replace(tzinfo=utc.UTC)
        
        return dt
    
    def sync_creations(self):
        """
        Synchronise les soumissions du formulaire Création Marchand
        Filtre les données à partir du 2026-04-13
        """
        print("Début synchronisation des créations marchand...")
        
        # Récupérer les mappings
        mappings = self.get_mappings(settings.KOBO_UID_CREATION)
        
        # Récupérer les données paginées
        url = f"{self.base_url}/api/v2/assets/{settings.KOBO_UID_CREATION}/data/?format=json"
        all_data = []
        
        while url:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            all_data.extend(results)
            
            url = data.get('next')
            print(f"  Récupéré {len(results)} soumissions...")
        
        print(f"Total soumissions récupérées: {len(all_data)}")
        
        # Filtrer et traiter les données
        date_min = datetime(2026, 4, 13, 0, 0, 0, tzinfo=utc.UTC)
        creations_a_inserer = []
        agents_a_mettre_a_jour = {}
        
        # Trier par date pour la déduplication (on garde la première)
        all_data.sort(key=lambda x: x.get('start', ''))
        
        # Pour la déduplication des marchands
        marchands_vus = set()
        
        for submission in all_data:
            # Vérifier la date
            start_date = self.convert_date(submission.get('start'))
            if not start_date or start_date < date_min:
                continue
            
            # Extraire le numéro opener
            # Ancien format: champ 'numero_opener'
            # Nouveau format: 'identification_agent/numero_opener'
            numero_opener = submission.get('numero_opener') or submission.get('identification_agent/numero_opener')
            if not numero_opener:
                continue
            
            # Extraire le numéro marchand
            numero_marchand = submission.get('numero_marchand') or submission.get('infos_marchand/numero_marchand')
            if not numero_marchand:
                continue
            
            # Déduplication par numero_marchand
            if numero_marchand in marchands_vus:
                continue
            marchands_vus.add(numero_marchand)
            
            # Extraire l'équipe
            # Ancien format: equipes (1=Mixx, 2=Top Image)
            # Nouveau format: identification_agent/agent_equipe (valeur directe)
            ancienne_equipe = submission.get('equipes')
            nouvelle_equipe = submission.get('identification_agent/agent_equipe')
            
            if nouvelle_equipe:
                equipe = nouvelle_equipe  # Déjà "Mixx"
            elif ancienne_equipe:
                equipe = 'Mixx' if ancienne_equipe == '1' else 'Top Image'
            else:
                equipe = ''
            
            # Extraire la team (uniquement nouveau format)
            team = submission.get('identification_agent/agent_team', '')
            
            # Extraire les autres champs avec mapping
            type_structure_code = submission.get('type_structure') or submission.get('infos_marchand/type_structure')
            type_structure = mappings.get('type_structure', {}).get(type_structure_code, '') if type_structure_code else ''
            
            profil_marchand_code = submission.get('profil_marchand') or submission.get('infos_marchand/profil_marchand')
            profil_marchand = mappings.get('profil_marchand', {}).get(profil_marchand_code, '') if profil_marchand_code else ''
            
            nom_opener = submission.get('nom_opener') or submission.get('identification_agent/nom_opener', '')
            nom_structure = submission.get('nom_structure') or submission.get('infos_marchand/nom_structure', '')
            region = submission.get('filtre_regions') or submission.get('contact_localisation/filtre_regions', '')
            departement = submission.get('filtre_departs') or submission.get('contact_localisation/filtre_departs', '')
            
            # Créer ou mettre à jour l'agent
            if numero_opener not in agents_a_mettre_a_jour:
                agents_a_mettre_a_jour[numero_opener] = {
                    'numero': numero_opener,
                    'nom': nom_opener,
                    'est_opener': True,
                    'est_animateur': False,
                    'equipe': equipe,
                    'team': team,
                }
            else:
                # Mettre à jour l'équipe si elle n'était pas définie
                if equipe and not agents_a_mettre_a_jour[numero_opener]['equipe']:
                    agents_a_mettre_a_jour[numero_opener]['equipe'] = equipe
                if team and not agents_a_mettre_a_jour[numero_opener]['team']:
                    agents_a_mettre_a_jour[numero_opener]['team'] = team
            
            # Préparer la création marchand
            creations_a_inserer.append({
                'kobo_id': str(submission.get('_id', '')),
                'numero_marchand': numero_marchand,
                'opener_numero': numero_opener,
                'nom_structure': nom_structure,
                'type_structure': type_structure,
                'profil_marchand': profil_marchand,
                'equipe': equipe,
                'team': team,
                'region': region,
                'departement': departement,
                'date_soumission': start_date,
                'date_activite': start_date.date(),
            })
        
        # Mettre à jour les agents
        for numero, agent_data in agents_a_mettre_a_jour.items():
            agent, created = Agent.objects.update_or_create(
                numero=numero,
                defaults=agent_data
            )
            if created:
                print(f"  Créé agent opener: {numero}")
            else:
                print(f"  Mis à jour agent: {numero}")
        
        # Insérer les créations (déjà dédoublonnées)
        creations_count = 0
        for creation in creations_a_inserer:
            try:
                opener = Agent.objects.get(numero=creation['opener_numero'])
                CreationMarchand.objects.get_or_create(
                    numero_marchand=creation['numero_marchand'],
                    defaults={
                        'kobo_id': creation['kobo_id'],
                        'opener': opener,
                        'nom_structure': creation['nom_structure'],
                        'type_structure': creation['type_structure'],
                        'profil_marchand': creation['profil_marchand'],
                        'equipe': creation['equipe'],
                        'team': creation['team'],
                        'region': creation['region'],
                        'departement': creation['departement'],
                        'date_soumission': creation['date_soumission'],
                        'date_activite': creation['date_activite'],
                    }
                )
                creations_count += 1
            except Agent.DoesNotExist:
                print(f"  Erreur: Agent {creation['opener_numero']} non trouvé")
        
        print(f"Créations insérées: {creations_count}")
        return creations_count
    
    def sync_suivis(self):
        """
        Synchronise les soumissions du formulaire Suivi Marchand
        Filtre les données à partir du 2026-04-14
        """
        print("Début synchronisation des suivis marchand...")
        
        # Récupérer les mappings
        mappings = self.get_mappings(settings.KOBO_UID_SUIVI)
        
        # Récupérer les données paginées
        url = f"{self.base_url}/api/v2/assets/{settings.KOBO_UID_SUIVI}/data/?format=json"
        all_data = []
        
        while url:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            all_data.extend(results)
            
            url = data.get('next')
            print(f"  Récupéré {len(results)} soumissions...")
        
        print(f"Total soumissions récupérées: {len(all_data)}")
        
        # Filtrer et traiter les données
        date_min = datetime(2026, 4, 14, 0, 0, 0, tzinfo=utc.UTC)
        suivis_a_inserer = []
        agents_a_mettre_a_jour = {}
        
        for submission in all_data:
            # Vérifier la date
            start_date = self.convert_date(submission.get('start'))
            if not start_date or start_date < date_min:
                continue
            
            # Extraire le numéro animateur (même champ 'numero_opener')
            numero_animateur = submission.get('numero_opener')
            if not numero_animateur:
                continue
            
            # Extraire les données de la section
            numero_marchand = submission.get('section_marchand/numero_marchand')
            numero_client = submission.get('section_clients/numero_clients')
            montant = submission.get('section_clients/montant')
            application_code = submission.get('section_clients/application_paiements')
            profil_code = submission.get('section_marchand/profil_marchand')
            type_code = submission.get('section_marchand/type_structure')
            
            if not numero_marchand or not numero_client or not montant:
                continue
            
            # Mapper les codes
            application = mappings.get('application_paiements', {}).get(application_code, '')
            profil = mappings.get('profil_marchand', {}).get(profil_code, '')
            type_structure = mappings.get('type_structure', {}).get(type_code, '')
            
            # Créer ou mettre à jour l'agent (animateur)
            if numero_animateur not in agents_a_mettre_a_jour:
                agents_a_mettre_a_jour[numero_animateur] = {
                    'numero': numero_animateur,
                    'est_opener': False,
                    'est_animateur': True,
                }
            
            # Préparer le suivi
            suivis_a_inserer.append({
                'kobo_id': str(submission.get('_id', '')),
                'animateur_numero': numero_animateur,
                'numero_marchand': numero_marchand,
                'numero_client': numero_client,
                'montant': montant,
                'application_paiement': application,
                'profil_marchand': profil,
                'type_structure': type_structure,
                'date_soumission': start_date,
                'date_activite': start_date.date(),
            })
        
        # Mettre à jour les agents sans écraser est_opener si déjà True
        for numero, agent_data in agents_a_mettre_a_jour.items():
            agent, created = Agent.objects.get_or_create(
                numero=numero,
                defaults={'est_animateur': True, 'est_opener': False}
            )
            if created:
                print(f"  Créé agent animateur: {numero}")
            elif not agent.est_animateur:
                agent.est_animateur = True
                agent.save()
                print(f"  Mis à jour agent (ajout rôle animateur): {numero}")
        
        # Insérer les suivis (idempotent via kobo_id)
        suivis_count = 0
        for suivi in suivis_a_inserer:
            try:
                animateur = Agent.objects.get(numero=suivi['animateur_numero'])
                _, created = SuiviMarchand.objects.get_or_create(
                    kobo_id=suivi['kobo_id'],
                    defaults={
                        'animateur': animateur,
                        'numero_marchand': suivi['numero_marchand'],
                        'numero_client': suivi['numero_client'],
                        'montant': suivi['montant'],
                        'application_paiement': suivi['application_paiement'],
                        'profil_marchand': suivi['profil_marchand'],
                        'type_structure': suivi['type_structure'],
                        'date_soumission': suivi['date_soumission'],
                        'date_activite': suivi['date_activite'],
                    }
                )
                if created:
                    suivis_count += 1
            except Agent.DoesNotExist:
                print(f"  Erreur: Agent animateur {suivi['animateur_numero']} non trouvé")
        
        print(f"Suivis insérés: {suivis_count}")
        return suivis_count
    
    def sync_all(self):
        """
        Synchronise tous les formulaires
        """
        print("=== Début synchronisation complète ===")
        creations = self.sync_creations()
        suivis = self.sync_suivis()
        print(f"=== Synchronisation terminée: {creations} créations, {suivis} suivis ===")
        return creations, suivis