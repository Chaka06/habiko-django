from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.db import transaction
from .models import Ad, AuditLog
from .tasks import send_moderation_notification


@staff_member_required
def approve_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """Approuver une annonce depuis l'admin"""
    ad = get_object_or_404(Ad, pk=ad_id)

    if ad.status != Ad.Status.PENDING:
        messages.error(request, "Cette annonce ne peut pas être approuvée.")
        return redirect("admin:ads_ad_changelist")

    with transaction.atomic():
        ad.status = Ad.Status.APPROVED
        ad.save()

        # Log d'audit
        AuditLog.objects.create(
            user=request.user,
            action="approve_ad",
            entity_type="ad",
            entity_id=str(ad.pk),
            metadata={"title": ad.title},
        )

        # Notification email
        send_moderation_notification.delay(ad.pk, True)

    from core.context_processors import invalidate_site_metrics_cache
    invalidate_site_metrics_cache()
    messages.success(request, f"Annonce '{ad.title}' approuvée avec succès.")
    return redirect("admin:ads_ad_changelist")


@staff_member_required
def reject_ad(request: HttpRequest, ad_id: int) -> HttpResponse:
    """Rejeter une annonce depuis l'admin"""
    ad = get_object_or_404(Ad, pk=ad_id)

    if ad.status != Ad.Status.PENDING:
        messages.error(request, "Cette annonce ne peut pas être rejetée.")
        return redirect("admin:ads_ad_changelist")

    with transaction.atomic():
        ad.status = Ad.Status.REJECTED
        ad.save()

        # Log d'audit
        AuditLog.objects.create(
            user=request.user,
            action="reject_ad",
            entity_type="ad",
            entity_id=str(ad.pk),
            metadata={"title": ad.title},
        )

        # Notification email
        send_moderation_notification.delay(ad.pk, False)

    from core.context_processors import invalidate_site_metrics_cache
    invalidate_site_metrics_cache()
    messages.success(request, f"Annonce '{ad.title}' rejetée.")
    return redirect("admin:ads_ad_changelist")
