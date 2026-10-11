import django_filters
from django.db.models import Q

from .constants import AVAILABILITY_CHOICES, CAPACITY_CHOICES, PRODUCT_TYPE_CHOICES
from .models import Brand, Category, Product


class ProductFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="অনুসন্ধান")
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(), label="ক্যাটাগরি"
    )
    brand = django_filters.ModelMultipleChoiceFilter(
        queryset=Brand.objects.all(), label="ব্র্যান্ড"
    )
    availability = django_filters.MultipleChoiceFilter(
        choices=AVAILABILITY_CHOICES, label="স্টক"
    )
    capacity = django_filters.MultipleChoiceFilter(
        choices=CAPACITY_CHOICES, label="পরিমাণ"
    )
    product_type = django_filters.MultipleChoiceFilter(
        choices=PRODUCT_TYPE_CHOICES, label="ধরন"
    )
    min_price = django_filters.NumberFilter(field_name="base_price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="base_price", lookup_expr="lte")
    min_qty = django_filters.NumberFilter(field_name="stock_quantity", lookup_expr="gte")
    max_qty = django_filters.NumberFilter(field_name="stock_quantity", lookup_expr="lte")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock", label="শুধু স্টকে")

    ordering = django_filters.OrderingFilter(
        fields=(
            ("base_price", "price"),
            ("-created_at", "newest"),
            ("-is_best_seller", "popular"),
            ("-is_top_rated", "rating"),
        ),
        field_labels={
            "price": "দাম",
            "newest": "নতুন",
            "popular": "জনপ্রিয়",
            "rating": "রেটিং",
        },
    )

    class Meta:
        model = Product
        fields = ["q", "category", "brand", "availability", "capacity", "product_type"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name_bn__icontains=value)
            | Q(name_en__icontains=value)
            | Q(sku__icontains=value)
            | Q(short_description_bn__icontains=value)
            | Q(short_description_en__icontains=value)
        )

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(Q(track_inventory=False) | Q(stock_quantity__gt=0))
        return queryset
