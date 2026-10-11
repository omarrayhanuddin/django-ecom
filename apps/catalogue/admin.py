from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline

from .models import Brand, Category, Product, ProductImage, ProductReview, ProductVariant, Tag
from .resources import ProductResource


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "order")


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("name", "sku", "price_override", "stock_quantity")


class ProductReviewInline(TabularInline):
    model = ProductReview
    extra = 0
    fields = ("user", "rating", "comment", "is_approved")
    readonly_fields = ("user",)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("display_name", "parent", "is_featured", "order", "product_count")
    list_editable = ("is_featured", "order")
    list_filter = ("is_featured", "parent")
    search_fields = ("name_bn", "name_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}

    @admin.display(description="পণ্য")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_classes = [ProductResource]
    inlines = [ProductImageInline, ProductVariantInline, ProductReviewInline]
    list_display = (
        "thumbnail", "display_name", "sku", "category", "price_display",
        "stock_display", "availability", "is_featured",
    )
    list_filter = ("availability", "category", "brand", "is_featured", "is_trending", "is_best_seller", "is_top_rated")
    search_fields = ("name_bn", "name_en", "sku")
    prepopulated_fields = {"slug": ("name_en",)}
    list_select_related = ("category", "brand")
    autocomplete_fields = ("brand",)
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("মূল তথ্য", {"fields": ("name_bn", "name_en", "slug", "sku", "category", "brand", "tags")}),
        ("বর্ণনা", {"fields": ("short_description_bn", "short_description_en", "full_description")}),
        ("মূল্য", {"fields": ("base_price", "discount_price")}),
        ("স্টক ও ধরন", {"fields": ("availability", "capacity", "product_type", "stock_quantity", "track_inventory")}),
        ("হাইলাইট", {"fields": ("is_featured", "is_trending", "is_best_seller", "is_top_rated")}),
        ("SEO", {"fields": ("meta_title", "meta_description")}),
        ("সময়", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="ছবি")
    def thumbnail(self, obj):
        img = obj.primary_image
        if img and img.image:
            return format_html('<img src="{}" height="40" alt="{}">', img.image.url, obj.sku)
        return "—"

    @admin.display(description="দাম", ordering="base_price")
    def price_display(self, obj):
        return f"৳{obj.get_effective_price():,.2f}"

    @admin.display(description="স্টক")
    def stock_display(self, obj):
        if not obj.track_inventory:
            return "আনলিমিটেড"
        return obj.stock_quantity


@admin.register(ProductReview)
class ProductReviewAdmin(ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating")
    search_fields = ("product__name_en", "user__email", "comment")
    list_editable = ("is_approved",)
    actions = ["approve_reviews"]

    @admin.action(description="নির্বাচিত রিভিউ অনুমোদন করুন")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated}টি রিভিউ অনুমোদিত হয়েছে।")
