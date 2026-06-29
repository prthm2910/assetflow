"""apps/operations/incidents/admin.py — Admin registration for Incident."""

from django.contrib import admin

from apps.operations.incidents.models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("inc_id", "title", "asset", "reported_by", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("inc_id", "title", "description")
    readonly_fields = ("inc_id", "created_at", "updated_at")
