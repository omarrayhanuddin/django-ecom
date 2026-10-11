from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from .models import Brand, Category, Product


class ProductResource(resources.ModelResource):
    category = fields.Field(
        column_name="category",
        attribute="category",
        widget=ForeignKeyWidget(Category, field="slug"),
    )
    brand = fields.Field(
        column_name="brand",
        attribute="brand",
        widget=ForeignKeyWidget(Brand, field="name"),
    )

    class Meta:
        model = Product
        import_id_fields = ("sku",)
        fields = (
            "id", "sku", "name_bn", "name_en", "slug",
            "category", "brand",
            "base_price", "discount_price", "availability",
            "capacity", "product_type", "stock_quantity",
            "track_inventory", "is_featured", "is_trending",
            "is_best_seller", "is_top_rated",
        )
        export_order = fields
