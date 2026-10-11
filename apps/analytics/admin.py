from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import SiteVisit


@admin.register(SiteVisit)
class SiteVisitAdmin(ModelAdmin):
    list_display = ("session_key", "ip_address", "page_url", "visited_at")
    list_filter = ("visited_at",)
    search_fields = ("session_key", "ip_address", "user_agent")
    date_hierarchy = "visited_at"
    readonly_fields = ("session_key", "ip_address", "user_agent", "visited_at", "page_url")

    def has_add_permission(self, request):
        return False
