"""
Service de synchronisation avec l'API KoboToolbox
Récupération, mapping et insertion des données
"""

import requests
from datetime import datetime, timezone as dt_tz
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.utils import timezone
from ..agents.models import Agent, CreationMarchand, SuiviMarchand

UTC = dt_tz.utc


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

        # Associer chaque champ select à ses choix via son list_name
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

        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')

        dt = datetime.fromisoformat(date_str)

        if dt.tzinfo:
            dt = dt.astimezone(UTC)
        else:
            dt = dt.replace(tzinfo=UTC)

        return dt

    def _upsert_opener(self, numero, nom, equipe, team):
        """
        Crée ou met à jour un agent opener sans écraser est_animateur
        """
        agent, created = Agent.objects.get_or_create(
            numero=numero,
            defaults={
                'nom': nom,
                'est_opener': True,
                'est_animateur': False,
                'equipe': equipe,
                'team': team,
            }
        )
        if not created:
            changed = False
            if not agent.est_opener:
                agent.est_opener = True
                changed = True
            if nom and not agent.nom:
                agent.nom = nom
                changed = True
            if equipe and not agent.equipe:
                agent.equipe = equipe
                changed = True
            if team and not agent.team:
                agent.team = team
                changed = True
            if changed:
                agent.save()
        return agent, created

    def sync_creations(self):
        """
        Synchronise les soumissions du formulaire Création Marchand
        Filtre les données à partir du 2026-04-13
        """
        print("Début synchronisation des créations marchand...")

        mappings = self.get_mappings(settings.KOBO_UID_CREATION)

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

        date_min = datetime(2026, 4, 13, 0, 0, 0, tzinfo=UTC)

        # Trier par date pour garder la première soumission de chaque marchand
        all_data.sort(key=lambda x: x.get('start', ''))

        marchands_vus = set()
        agents_data = {}
        creations_a_inserer = []

        for submission in all_data:
            start_date = self.convert_date(submission.get('start'))
            if not start_date or start_date < date_min:
                continue

            numero_opener = (
                submission.get('identification_agent/numero_opener')
                or submission.get('numero_opener')
            )
            if not numero_opener:
                continue

            numero_marchand = (
                submission.get('infos_marchand/numero_marchand')
                or submission.get('numero_marchand')
            )
            if not numero_marchand:
                continue

            # Déduplication par numero_marchand
            if numero_marchand in marchands_vus:
                continue
            marchands_vus.add(numero_marchand)

            # Équipe : nouveau format direct, ancien format mappé
            nouvelle_equipe = submission.get('identification_agent/agent_equipe', '')
            ancienne_equipe = submission.get('equipes', '')
            if nouvelle_equipe:
                equipe = nouvelle_equipe
            elif ancienne_equipe:
                equipe = 'Mixx' if str(ancienne_equipe) == '1' else 'Top Image'
            else:
                equipe = ''

            team = submission.get('identification_agent/agent_team', '')
            nom_opener = (
                submission.get('identification_agent/nom_opener')
                or submission.get('nom_opener', '')
                or ''
            )

            type_structure_code = (
                submission.get('infos_marchand/type_structure')
                or submission.get('type_structure', '')
            )
            type_structure = mappings.get('type_structure', {}).get(str(type_structure_code), '') if type_structure_code else ''

            profil_code = (
                submission.get('infos_marchand/profil_marchand')
                or submission.get('profil_marchand', '')
            )
            profil_marchand = mappings.get('profil_marchand', {}).get(str(profil_code), '') if profil_code else ''

            nom_structure = (
                submission.get('infos_marchand/nom_structure')
                or submission.get('nom_structure', '')
                or ''
            )
            region = (
                submission.get('contact_localisation/filtre_regions')
                or submission.get('filtre_regions', '')
                or ''
            )
            departement = (
                submission.get('contact_localisation/filtre_departs')
                or submission.get('filtre_departs', '')
                or ''
            )

            # Mémoriser les données agent (on garde la meilleure valeur trouvée)
            if numero_opener not in agents_data:
                agents_data[numero_opener] = {'nom': nom_opener, 'equipe': equipe, 'team': team}
            else:
                if equipe and not agents_data[numero_opener]['equipe']:
                    agents_data[numero_opener]['equipe'] = equipe
                if team and not agents_data[numero_opener]['team']:
                    agents_data[numero_opener]['team'] = team

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

        # Créer/mettre à jour les agents sans écraser est_animateur
        for numero, info in agents_data.items():
            agent, created = self._upsert_opener(numero, info['nom'], info['equipe'], info['team'])
            print(f"  {'Créé' if created else 'Mis à jour'} agent opener: {numero}")

        # Insérer les créations (idempotent via numero_marchand)
        creations_count = 0
        for creation in creations_a_inserer:
            try:
                opener = Agent.objects.get(numero=creation['opener_numero'])
                _, created = CreationMarchand.objects.get_or_create(
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
                if created:
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

        mappings = self.get_mappings(settings.KOBO_UID_SUIVI)

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

        date_min = datetime(2026, 4, 14, 0, 0, 0, tzinfo=UTC)
        suivis_a_inserer = []
        agents_vus = set()

        for submission in all_data:
            start_date = self.convert_date(submission.get('start'))
            if not start_date or start_date < date_min:
                continue

            numero_animateur = submission.get('numero_opener')
            if not numero_animateur:
                continue

            numero_marchand = submission.get('section_marchand/numero_marchand')
            numero_client = submission.get('section_clients/numero_clients')
            montant_raw = submission.get('section_clients/montant')

            if not numero_marchand or not numero_client or montant_raw is None:
                continue

            try:
                montant = Decimal(str(montant_raw).replace(' ', '').replace(',', '.'))
            except InvalidOperation:
                print(f"  Montant invalide ignoré: {montant_raw}")
                continue

            application_code = submission.get('section_clients/application_paiements', '')
            profil_code = submission.get('section_marchand/profil_marchand', '')
            type_code = submission.get('section_marchand/type_structure', '')

            application = mappings.get('application_paiements', {}).get(str(application_code), '') if application_code else ''
            profil = mappings.get('profil_marchand', {}).get(str(profil_code), '') if profil_code else ''
            type_structure = mappings.get('type_structure', {}).get(str(type_code), '') if type_code else ''

            agents_vus.add(numero_animateur)

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

        # Créer les agents animateurs sans écraser est_opener
        for numero in agents_vus:
            agent, created = Agent.objects.get_or_create(
                numero=numero,
                defaults={'est_animateur': True, 'est_opener': False}
            )
            if not created and not agent.est_animateur:
                agent.est_animateur = True
                agent.save()
            if created:
                print(f"  Créé agent animateur: {numero}")

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
