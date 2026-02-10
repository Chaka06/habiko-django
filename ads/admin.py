from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import City, Feature, Ad, AdMedia, Availability, AdFeature, Report, AuditLog
from .tasks import send_moderation_notification


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "region")
    verbose_name = _("Ville")
    verbose_name_plural = _("Villes")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    verbose_name = _("Fonctionnalité")
    verbose_name_plural = _("Fonctionnalités")


class AdMediaInline(admin.TabularInline):
    model = AdMedia
    extra = 0


class AdAdminForm(forms.ModelForm):
    subcategories = forms.MultipleChoiceField(
        choices=[(choice, choice) for choice in Ad.SUBCATEGORY_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Sous-catégories",
    )

    class Meta:
        model = Ad
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Charger les sous-catégories existantes
            self.fields["subcategories"].initial = self.instance.subcategories or []

    def clean_subcategories(self):
        return self.cleaned_data.get("subcategories", [])


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    form = AdAdminForm
    list_display = (
        "title",
        "user",
        "category",
        "get_subcategories_display",
        "city",
        "status",
        "created_at",
        "expires_at",
        "moderation_actions",
    )
    list_filter = ("category", "status", "city", "created_at", "expires_at")
    search_fields = ("title", "slug", "user__username", "user__email")
    readonly_fields = ("slug", "views_count", "contacts_clicks", "created_at", "updated_at")
    inlines = [AdMediaInline]
    actions = ["approve_ads", "reject_ads", "archive_ads"]
    verbose_name = _("Annonce")
    verbose_name_plural = _("Annonces")

    fieldsets = (
        (
            "Informations générales",
            {
                "fields": (
                    "user",
                    "title",
                    "slug",
                    "description_sanitized",
                    "category",
                    "subcategories",
                )
            },
        ),
        ("Localisation", {"fields": ("city", "area")}),
        ("Statut et modération", {"fields": ("status", "is_verified", "expires_at")}),
        ("Statistiques", {"fields": ("views_count", "contacts_clicks"), "classes": ("collapse",)}),
        ("Métadonnées", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def moderation_actions(self, obj):
        if obj.status == Ad.Status.PENDING:
            return format_html(
                '<a class="button" href="{}">Approuver</a> '
                '<a class="button" href="{}">Rejeter</a>',
                reverse("admin:ads_ad_approve", args=[obj.pk]),
                reverse("admin:ads_ad_reject", args=[obj.pk]),
            )
        return "-"

    moderation_actions.short_description = "Actions"

    def approve_ads(self, request, queryset):
        with transaction.atomic():
            count = 0
            for ad in queryset.filter(status=Ad.Status.PENDING):
                ad.status = Ad.Status.APPROVED
                ad.save()
                count += 1
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
        self.message_user(request, f"{count} annonce(s) approuvée(s).")

    approve_ads.short_description = "Approuver les annonces sélectionnées"

    def reject_ads(self, request, queryset):
        with transaction.atomic():
            count = 0
            for ad in queryset.filter(status=Ad.Status.PENDING):
                ad.status = Ad.Status.REJECTED
                ad.save()
                count += 1
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
        self.message_user(request, f"{count} annonce(s) rejetée(s).")

    reject_ads.short_description = "Rejeter les annonces sélectionnées"

    def archive_ads(self, request, queryset):
        with transaction.atomic():
            count = 0
            for ad in queryset:
                ad.status = Ad.Status.ARCHIVED
                ad.save()
                count += 1
                # Log d'audit
                AuditLog.objects.create(
                    user=request.user,
                    action="archive_ad",
                    entity_type="ad",
                    entity_id=str(ad.pk),
                    metadata={"title": ad.title},
                )
        from core.context_processors import invalidate_site_metrics_cache
        invalidate_site_metrics_cache()
        self.message_user(request, f"{count} annonce(s) archivée(s).")

    archive_ads.short_description = "Archiver les annonces sélectionnées"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "city")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Statistiques pour le dashboard
        from django.db.models import Count, Q
        from .models import Report

        stats = Ad.objects.aggregate(
            pending_count=Count("id", filter=Q(status=Ad.Status.PENDING)),
            approved_count=Count("id", filter=Q(status=Ad.Status.APPROVED)),
            rejected_count=Count("id", filter=Q(status=Ad.Status.REJECTED)),
        )

        reports_count = Report.objects.filter(status="pending").count()

        extra_context.update(
            {
                "approved_count": stats["approved_count"],
                "rejected_count": stats["rejected_count"],
                "reports_count": reports_count,
            }
        )

        return super().changelist_view(request, extra_context)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("ad", "on_request")


@admin.register(AdFeature)
class AdFeatureAdmin(admin.ModelAdmin):
    list_display = ("ad", "feature")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("ad", "reason", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("ad__title", "reason")
    readonly_fields = ("ad", "reporter_fingerprint", "reason", "created_at")
    actions = ["mark_resolved", "mark_ignored"]
    verbose_name = _("Rapport")
    verbose_name_plural = _("Rapports")

    def mark_resolved(self, request, queryset):
        count = queryset.filter(status="pending").update(status="resolved")
        self.message_user(request, f"{count} rapport(s) marqué(s) comme résolu(s).")

    mark_resolved.short_description = "Marquer comme résolu"

    def mark_ignored(self, request, queryset):
        count = queryset.filter(status="pending").update(status="ignored")
        self.message_user(request, f"{count} rapport(s) marqué(s) comme ignoré(s).")

    mark_ignored.short_description = "Marquer comme ignoré"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "entity_type", "entity_id", "created_at")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("action", "entity_id", "user__username")
    readonly_fields = ("user", "action", "entity_type", "entity_id", "metadata", "created_at")
    date_hierarchy = "created_at"
    verbose_name = _("Log d'audit")
    verbose_name_plural = _("Logs d'audit")

    def has_add_permission(self, request):
        return False  # Les logs sont créés automatiquement


# Register your models here.
