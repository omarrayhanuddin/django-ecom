from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin

from .models import SiteSettings, StaticPage, StoreLocation, SupportInfo


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin, ModelAdmin):
    pass


@admin.register(SupportInfo)
class SupportInfoAdmin(SingletonModelAdmin, ModelAdmin):
    pass


@admin.register(StaticPage)
class StaticPageAdmin(ModelAdmin):
    list_display = ("title_bn", "title_en", "slug", "is_published")
    list_filter = ("is_published",)
    search_fields = ("title_bn", "title_en", "slug")
    prepopulated_fields = {"slug": ("title_en",)}


@admin.register(StoreLocation)
class StoreLocationAdmin(SortableAdminMixin, ModelAdmin):
    list_display = ("name", "phone", "is_head_office", "order")
    list_editable = ("is_head_office",)
    sortable_by = ()


def dashboard_callback(request, context):
    """Add a live-visitor card to the unfold dashboard."""
    from apps.analytics.live import live_count
    from apps.analytics.models import SiteVisit
    from apps.catalogue.models import Product
    from apps.orders.models import Order

    context.update(
        {
            "live_count": live_count(),
            "total_visits": SiteVisit.total_count(),
            "product_count": Product.objects.count(),
            "order_count": Order.objects.count(),
        }
    )
    return context
