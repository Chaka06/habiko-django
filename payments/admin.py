from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("deposit_id", "user", "ad", "type", "amount", "status", "correspondent", "created_at")
    list_filter = ("status", "type", "correspondent")
    search_fields = ("deposit_id", "user__username", "phone")
    raw_id_fields = ("user", "ad")
    readonly_fields = ("deposit_id", "created_at", "completed_at", "pawapay_response")
    ordering = ("-created_at",)
