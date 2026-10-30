from django.contrib import admin

from .models import Listing, PaymentMethod, Service, ServiceRequest


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("icon", "name", "fee", "sort", "is_active")
    list_display_links = ("name",)
    list_editable = ("fee", "sort", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "account_name", "account_number", "sort", "is_active")
    list_editable = ("sort", "is_active")


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "service", "status", "payment_status", "created_at")
    list_filter = ("status", "payment_status", "service")
    search_fields = ("title", "user__username", "user__first_name", "payment_ref")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "service", "deal_type", "price", "is_active", "created_at")
    list_filter = ("service", "deal_type", "is_active")
    search_fields = ("title", "location", "contact_name")
