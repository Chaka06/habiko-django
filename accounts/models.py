from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import random


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        PROVIDER = "provider", _("Provider")
        MODERATOR = "moderator", _("Moderator")
        ADMIN = "admin", _("Admin")

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.PROVIDER,
        help_text=_("User role. Only providers can sign up publicly."),
    )
    phone_e164 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^\+[1-9]\d{1,14}$", message=_("Enter a valid E.164 phone."))],
        help_text=_("Phone number in E.164 format, e.g., +2250700000000"),
    )
    is_verified = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=120)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio_sanitized = models.TextField(blank=True, default="")
    whatsapp_e164 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^\+[1-9]\d{1,14}$", message=_("Enter a valid E.164 phone."))],
    )
    phone2_e164 = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^\+[1-9]\d{1,14}$", message=_("Enter a valid E.164 phone."))],
        help_text=_("Second phone number for ads (optional). Shown with primary on ad contact."),
    )
    telegram = models.CharField(max_length=64, null=True, blank=True)
    city = models.ForeignKey("ads.City", on_delete=models.SET_NULL, null=True, blank=True)
    country = models.CharField(max_length=2, default="CI")
    contact_prefs = models.JSONField(
        default=list,
        help_text=_("Subset of ['sms','whatsapp','call']"),
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Profile verified by email"),
    )

    def __str__(self) -> str:  # pragma: no cover
        if hasattr(self, "user") and self.user:
            return f"Profile({self.user.username})"
        return f"Profile({self.display_name})"


def create_profile(sender, instance, created, **kwargs):  # pragma: no cover
    if created:
        Profile.objects.create(user=instance, display_name=instance.username)
        # Note: Account n'est plus créé automatiquement car le système de paiement est désactivé


models.signals.post_save.connect(create_profile, sender=CustomUser)

# Create your models here.


class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        PASSWORD_CHANGE = "password_change", _("Password change")
        LOGIN_DEVICE = "login_device", _("Login device notification")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps"
    )
    code = models.CharField(max_length=5)
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover
        return f"OTP({self.user_id},{self.purpose},{self.code})"

    @staticmethod
    def generate_code() -> str:
        return f"{random.randint(0, 99999):05d}"

    @classmethod
    def create_otp(cls, user, purpose: str, ttl_seconds: int = 600) -> "EmailOTP":
        now = timezone.now()
        code = cls.generate_code()
        otp = cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=now + timezone.timedelta(seconds=ttl_seconds),
        )
        return otp

    def is_valid(self, code: str) -> bool:
        return not self.is_used and self.code == code and timezone.now() <= self.expires_at


class Account(models.Model):
    """Compte utilisateur avec solde et crédits"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account"
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Solde en FCFA")
    )
    free_ads_remaining = models.PositiveIntegerField(
        default=0,
        help_text=_("Nombre d'annonces gratuites restantes")
    )
    ads_remaining = models.PositiveIntegerField(
        default=0,
        help_text=_("Nombre d'annonces restantes du pack acheté")
    )
    is_premium = models.BooleanField(
        default=False,
        help_text=_("Compte premium (15 annonces premium)")
    )
    premium_ads_remaining = models.PositiveIntegerField(
        default=0,
        help_text=_("Nombre d'annonces premium restantes")
    )
    free_boosters_remaining = models.PositiveIntegerField(
        default=0,
        help_text=_("Nombre de boosters gratuits restants (pack 15000 FCFA)")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Compte")
        verbose_name_plural = _("Comptes")

    def __str__(self) -> str:
        return f"Account({self.user.username}) - {self.balance} FCFA"

    def can_post_ad(self) -> bool:
        """Vérifie si l'utilisateur peut poster une annonce"""
        return (
            self.free_ads_remaining > 0 or
            self.ads_remaining > 0 or
            self.premium_ads_remaining > 0
        )

    def use_ad_credit(self) -> bool:
        """Utilise un crédit d'annonce (priorité: premium > pack > gratuit)"""
        if self.premium_ads_remaining > 0:
            self.premium_ads_remaining -= 1
            self.save()
            return True
        elif self.ads_remaining > 0:
            self.ads_remaining -= 1
            self.save()
            return True
        elif self.free_ads_remaining > 0:
            self.free_ads_remaining -= 1
            self.save()
            return True
        return False


class RechargePackage(models.Model):
    """Formules de recharge"""
    name = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Montant en FCFA")
    )
    ads_included = models.PositiveIntegerField(
        help_text=_("Nombre d'annonces incluses")
    )
    credit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Montant de crédit ajouté au compte pour booster")
    )
    free_boosters = models.PositiveIntegerField(
        default=0,
        help_text=_("Nombre de boosters gratuits (pack 15000 FCFA = 2)")
    )
    is_premium = models.BooleanField(
        default=False,
        help_text=_("Pack premium (20000 FCFA)")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["amount"]
        verbose_name = _("Formule de recharge")
        verbose_name_plural = _("Formules de recharge")

    def __str__(self) -> str:
        return f"{self.name} - {self.amount} FCFA ({self.ads_included} annonces)"


class BoostOption(models.Model):
    """Options de boost pour les annonces"""
    class BoostType(models.TextChoices):
        PREMIUM = "premium", _("Premium")
        PROLONGATION = "prolongation", _("Prolongation")
        URGENT = "urgent", _("Urgent")

    boost_type = models.CharField(max_length=20, choices=BoostType.choices)
    name = models.CharField(max_length=100)
    duration_days = models.PositiveIntegerField(
        help_text=_("Durée en jours")
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Prix en FCFA")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["boost_type", "duration_days"]
        verbose_name = _("Option de boost")
        verbose_name_plural = _("Options de boost")

    def __str__(self) -> str:
        return f"{self.get_boost_type_display()} - {self.duration_days} jours ({self.price} FCFA)"


class Transaction(models.Model):
    """Historique des transactions (recharges, boosts)"""
    class TransactionType(models.TextChoices):
        RECHARGE = "recharge", _("Recharge")
        BOOST = "boost", _("Boost")
        REFUND = "refund", _("Remboursement")

    class Status(models.TextChoices):
        PENDING = "pending", _("En attente")
        COMPLETED = "completed", _("Complétée")
        FAILED = "failed", _("Échouée")
        CANCELLED = "cancelled", _("Annulée")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    cinetpay_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    recharge_package = models.ForeignKey(
        RechargePackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    boost_option = models.ForeignKey(
        BoostOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ad = models.ForeignKey(
        "ads.Ad",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} - {self.amount} FCFA - {self.get_status_display()}"
