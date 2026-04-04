from django.contrib import admin
from .models import Payment, PromoCode, PromoCodeUsage


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ("deposit_id", "user", "ad", "type", "amount", "status", "geniuspay_reference", "created_at")
    list_filter   = ("status", "type")
    search_fields = ("deposit_id__iexact", "geniuspay_reference", "user__username", "user__email")
    raw_id_fields = ("user", "ad")
    readonly_fields = ("deposit_id", "created_at", "completed_at", "gateway_response")
    ordering      = ("-created_at",)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display  = ("code", "discount_percent", "active", "expires_at", "max_uses", "uses_count", "created_at")
    list_filter   = ("active",)
    search_fields = ("code",)
    readonly_fields = ("created_at",)

    def uses_count(self, obj):
        return PromoCodeUsage.objects.filter(code=obj.code).count()
    uses_count.short_description = "Utilisations"


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display  = ("code", "user", "discount_applied", "created_at")
    list_filter   = ("code",)
    search_fields = ("code", "user__username", "user__email")
    raw_id_fields = ("user", "ad")
    readonly_fields = ("created_at",)
