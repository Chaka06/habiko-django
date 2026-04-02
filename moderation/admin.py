from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display  = ("pk", "ad", "reason", "reporter", "ip_address", "reviewed", "created_at")
    list_filter   = ("reason", "reviewed")
    search_fields = ("ad__title", "reporter__email", "details")
    list_editable = ("reviewed",)
    readonly_fields = ("ad", "reporter", "reason", "details", "ip_address", "created_at")
    ordering = ("-created_at",)
