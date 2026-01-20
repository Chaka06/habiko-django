from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser,
    Profile,
    Account,
    RechargePackage,
    BoostOption,
    Transaction,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("HABIKO", {"fields": ("role", "phone_e164", "is_verified")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff", "is_verified")
    list_filter = ("role", "is_staff", "is_superuser", "is_active", "is_verified")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "city", "country")
    search_fields = ("user__username", "display_name")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "free_ads_remaining", "ads_remaining", "is_premium")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RechargePackage)
class RechargePackageAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "ads_included", "credit_amount", "is_premium", "is_active")
    list_filter = ("is_active", "is_premium")
    ordering = ("amount",)


@admin.register(BoostOption)
class BoostOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "boost_type", "duration_days", "price", "is_active")
    list_filter = ("boost_type", "is_active")
    ordering = ("boost_type", "duration_days")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "transaction_type", "amount", "status", "created_at")
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = ("user__username", "cinetpay_transaction_id", "description")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


# Register your models here.
