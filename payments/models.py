import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    """Paiement mobile money via PawaPay (dépôt initié par le client)."""

    class Type(models.TextChoices):
        STANDARD = "standard", "Annonce standard (500 FCFA / 5 jours)"
        BOOST = "boost", "Boost premium (700 FCFA / 7 jours + remontée 2h/jour)"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente de confirmation"
        COMPLETED = "completed", "Paiement confirmé"
        FAILED = "failed", "Paiement échoué"

    # PawaPay deposit ID (UUID v4 généré par nous)
    deposit_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Utilisateur"),
    )
    ad = models.ForeignKey(
        "ads.Ad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name=_("Annonce"),
    )
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        verbose_name=_("Type"),
    )
    amount = models.PositiveIntegerField(verbose_name=_("Montant (FCFA)"))
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Statut"),
    )
    # Numéro mobile money (format E164 sans le +) et opérateur
    phone = models.CharField(max_length=20, verbose_name=_("Numéro mobile money"))
    correspondent = models.CharField(
        max_length=30,
        verbose_name=_("Opérateur"),
        help_text="MTN_MOMO_CIV ou ORANGE_CIV",
    )
    # Réponse brute PawaPay (pour audit/debug)
    pawapay_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        indexes = [
            models.Index(fields=["deposit_id"], name="payment_deposit_idx"),
            models.Index(fields=["user", "status"], name="payment_user_status_idx"),
            models.Index(fields=["ad", "type"], name="payment_ad_type_idx"),
        ]

    def __str__(self) -> str:
        return f"Payment({self.deposit_id}) {self.type} {self.status}"
