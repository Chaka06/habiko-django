"""
Services pour la gestion des comptes, recharges et boosts
"""
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Account, RechargePackage, BoostOption, Transaction
from ads.models import Ad


class AccountService:
    """Service pour gérer les comptes utilisateurs"""

    @staticmethod
    def get_or_create_account(user):
        """Récupère ou crée un compte pour l'utilisateur"""
        account, created = Account.objects.get_or_create(user=user)
        return account

    @staticmethod
    def can_post_ad(user):
        """Vérifie si l'utilisateur peut poster une annonce"""
        account = AccountService.get_or_create_account(user)
        return account.can_post_ad()

    @staticmethod
    @transaction.atomic
    def use_ad_credit(user):
        """Utilise un crédit d'annonce"""
        account = AccountService.get_or_create_account(user)
        if not account.can_post_ad():
            raise ValidationError("Vous n'avez plus de crédits d'annonces disponibles. Veuillez recharger votre compte.")
        return account.use_ad_credit()

    @staticmethod
    @transaction.atomic
    def apply_recharge(user, package_id, cinetpay_transaction_id=None):
        """Applique une recharge au compte"""
        try:
            package = RechargePackage.objects.get(id=package_id, is_active=True)
        except RechargePackage.DoesNotExist:
            raise ValidationError("Formule de recharge invalide")

        account = AccountService.get_or_create_account(user)

        # Créer la transaction
        transaction_obj = Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TransactionType.RECHARGE,
            amount=package.amount,
            status=Transaction.Status.PENDING,
            cinetpay_transaction_id=cinetpay_transaction_id,
            recharge_package=package,
            description=f"Recharge {package.name}",
        )

        # Si c'est un pack premium
        if package.is_premium:
            account.is_premium = True
            account.premium_ads_remaining += package.ads_included
        else:
            account.ads_remaining += package.ads_included

        # Ajouter le crédit pour booster
        account.balance += package.credit_amount

        # Ajouter les boosters gratuits
        account.free_boosters_remaining += package.free_boosters

        account.save()

        # Marquer la transaction comme complétée
        transaction_obj.status = Transaction.Status.COMPLETED
        transaction_obj.save()

        return transaction_obj


class BoostService:
    """Service pour gérer les boosts d'annonces"""

    @staticmethod
    @transaction.atomic
    def apply_boost(user, ad_id, boost_option_id, use_free_booster=False):
        """Applique un boost à une annonce"""
        try:
            ad = Ad.objects.get(id=ad_id, user=user)
        except Ad.DoesNotExist:
            raise ValidationError("Annonce introuvable")

        try:
            boost_option = BoostOption.objects.get(id=boost_option_id, is_active=True)
        except BoostOption.DoesNotExist:
            raise ValidationError("Option de boost invalide")

        account = AccountService.get_or_create_account(user)

        # Vérifier si on peut utiliser un booster gratuit
        if use_free_booster:
            if account.free_boosters_remaining <= 0:
                raise ValidationError("Vous n'avez plus de boosters gratuits")
            account.free_boosters_remaining -= 1
            price = Decimal('0')
        else:
            # Vérifier le solde
            if account.balance < boost_option.price:
                raise ValidationError(f"Solde insuffisant. Il vous faut {boost_option.price} FCFA, vous avez {account.balance} FCFA")
            price = boost_option.price
            account.balance -= boost_option.price

        # Appliquer le boost selon le type
        now = timezone.now()
        if boost_option.boost_type == BoostOption.BoostType.PREMIUM:
            ad.is_premium = True
            ad.premium_until = now + timezone.timedelta(days=boost_option.duration_days)
        elif boost_option.boost_type == BoostOption.BoostType.URGENT:
            ad.is_urgent = True
            ad.urgent_until = now + timezone.timedelta(days=boost_option.duration_days)
        elif boost_option.boost_type == BoostOption.BoostType.PROLONGATION:
            # Prolonger l'annonce
            if ad.extended_until and ad.extended_until > now:
                # Si déjà prolongée, ajouter à la date existante
                ad.extended_until += timezone.timedelta(days=boost_option.duration_days)
            else:
                # Sinon, prolonger depuis la date d'expiration
                if ad.expires_at:
                    ad.extended_until = ad.expires_at + timezone.timedelta(days=boost_option.duration_days)
                else:
                    ad.extended_until = now + timezone.timedelta(days=boost_option.duration_days)

        ad.save()
        account.save()

        # Créer la transaction
        transaction_obj = Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TransactionType.BOOST,
            amount=price,
            status=Transaction.Status.COMPLETED,
            boost_option=boost_option,
            ad=ad,
            description=f"Boost {boost_option.name} pour {ad.title}",
        )

        return transaction_obj

    @staticmethod
    def get_effective_expiry_date(ad):
        """Retourne la date d'expiration effective (avec prolongation)"""
        if ad.extended_until:
            return max(ad.expires_at or ad.extended_until, ad.extended_until)
        return ad.expires_at

    @staticmethod
    def is_premium_active(ad):
        """Vérifie si le boost premium est actif"""
        if not ad.is_premium:
            return False
        if ad.premium_until:
            return timezone.now() < ad.premium_until
        return True

    @staticmethod
    def is_urgent_active(ad):
        """Vérifie si le boost urgent est actif"""
        if not ad.is_urgent:
            return False
        if ad.urgent_until:
            return timezone.now() < ad.urgent_until
        return True


