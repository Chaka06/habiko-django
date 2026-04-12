from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ("deposit_id", "user", "ad", "type", "amount", "status", "geniuspay_reference", "created_at")
    list_filter   = ("status", "type")
    search_fields = ("deposit_id__iexact", "geniuspay_reference", "user__username", "user__email")
    raw_id_fields = ("user", "ad")
    readonly_fields = ("deposit_id", "created_at", "completed_at", "gateway_response")
    ordering      = ("-created_at",)
