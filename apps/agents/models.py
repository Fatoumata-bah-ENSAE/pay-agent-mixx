"""
Modèles pour la gestion des agents MixxPay
"""

from django.db import models


class Agent(models.Model):
    """
    Agent de terrain (peut être opener, animateur ou les deux)
    """
    numero = models.CharField(max_length=15, unique=True, verbose_name="Numéro de téléphone")
    nom = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nom")
    equipe = models.CharField(max_length=50, blank=True, verbose_name="Équipe (Mixx/Top Image)")
    team = models.CharField(max_length=50, blank=True, verbose_name="Team (TEAMSEYDI, etc.)")
    est_opener = models.BooleanField(default=False, verbose_name="Est opener")
    est_animateur = models.BooleanField(default=False, verbose_name="Est animateur")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.numero} - {self.equipe or 'Sans équipe'}"

    def get_roles(self):
        """Retourne la liste des rôles de l'agent"""
        roles = []
        if self.est_opener:
            roles.append("Opener")
        if self.est_animateur:
            roles.append("Animateur")
        return " / ".join(roles) if roles else "Aucun"


class CreationMarchand(models.Model):
    """
    Soumission de création de marchand (formulaire opener)
    """
    opener = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='creations')
    numero_marchand = models.CharField(max_length=15, unique=True, verbose_name="Numéro marchand")
    nom_structure = models.CharField(max_length=200, blank=True, verbose_name="Nom structure")
    type_structure = models.CharField(max_length=50, blank=True, verbose_name="Type structure")
    profil_marchand = models.CharField(max_length=50, blank=True, verbose_name="Profil marchand")
    equipe = models.CharField(max_length=50, blank=True, verbose_name="Équipe")
    team = models.CharField(max_length=50, blank=True, verbose_name="Team")
    region = models.CharField(max_length=100, blank=True, verbose_name="Région")
    departement = models.CharField(max_length=100, blank=True, verbose_name="Département")
    date_soumission = models.DateTimeField(verbose_name="Date de soumission")
    date_activite = models.DateField(verbose_name="Date d'activité")

    class Meta:
        verbose_name = "Création marchand"
        verbose_name_plural = "Créations marchands"
        ordering = ['-date_activite']

    def __str__(self):
        return f"{self.numero_marchand} - {self.date_activite}"


class SuiviMarchand(models.Model):
    """
    Soumission de suivi marchand (formulaire animateur)
    """
    animateur = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='suivis')
    numero_marchand = models.CharField(max_length=15, verbose_name="Numéro marchand")
    numero_client = models.CharField(max_length=15, verbose_name="Numéro client")
    montant = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Montant")
    application_paiement = models.CharField(max_length=50, verbose_name="Application paiement")
    profil_marchand = models.CharField(max_length=50, blank=True, verbose_name="Profil marchand")
    type_structure = models.CharField(max_length=50, blank=True, verbose_name="Type structure")
    date_soumission = models.DateTimeField(verbose_name="Date de soumission")
    date_activite = models.DateField(verbose_name="Date d'activité")

    class Meta:
        verbose_name = "Suivi marchand"
        verbose_name_plural = "Suivis marchands"
        ordering = ['-date_activite']

    def __str__(self):
        return f"{self.numero_marchand} - {self.montant} FCFA - {self.date_activite}"