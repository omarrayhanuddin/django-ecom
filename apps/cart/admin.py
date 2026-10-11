from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("product", "variant", "quantity", "unit_price")


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("__str__", "user", "session_key", "item_count", "created_at")
    search_fields = ("user__email", "session_key")
    inlines = [CartItemInline]

    @admin.display(description="আইটেম")
    def item_count(self, obj):
        return obj.items.count()
