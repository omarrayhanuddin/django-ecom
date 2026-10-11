from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    Banner,
    Coupon,
    CouponRedemption,
    FlashSale,
    FlashSaleProduct,
    HotSale,
)


class FlashSaleProductInline(TabularInline):
    model = FlashSaleProduct
    extra = 1
    autocomplete_fields = ("product",)
    fields = ("product", "discount_percentage", "sale_price")


@admin.register(FlashSale)
class FlashSaleAdmin(ModelAdmin):
    list_display = ("name", "start_time", "end_time", "is_active", "is_current")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [FlashSaleProductInline]

    @admin.display(boolean=True, description="চলমান")
    def is_current(self, obj):
        return obj.is_current


@admin.register(HotSale)
class HotSaleAdmin(ModelAdmin):
    list_display = ("product", "discount_percentage", "label", "is_active")
    list_filter = ("is_active",)
    list_editable = ("discount_percentage", "label", "is_active")
    autocomplete_fields = ("product",)


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = (
        "code", "discount_type", "discount_value", "min_display",
        "used_count", "max_uses", "per_user_limit", "is_active", "valid_to",
    )
    list_filter = ("discount_type", "is_active", "is_next_purchase")
    search_fields = ("code", "user__email")
    readonly_fields = ("used_count",)
    autocomplete_fields = ("user",)
    actions = ["notify_codes"]

    @admin.display(description="ন্যূনতম")
    def min_display(self, obj):
        return f"৳{obj.minimum_order_value}"

    @admin.action(description="নির্বাচিত কুপন কোডগুলো অনুলিপি করুন")
    def notify_codes(self, request, queryset):
        codes = ", ".join(queryset.values_list("code", flat=True))
        self.message_user(request, f"কুপন কোড: {codes}")


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(ModelAdmin):
    list_display = ("coupon", "user", "order", "redeemed_at")
    search_fields = ("coupon__code", "user__email", "order__order_number")


@admin.register(Banner)
class BannerAdmin(SortableAdminMixin, ModelAdmin):
    list_display = ("__str__", "position", "order", "is_active")
    list_filter = ("position", "is_active")
    list_editable = ("is_active",)
    sortable_by = ()
