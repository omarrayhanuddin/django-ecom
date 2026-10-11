from django.views.generic import ListView

from .models import Banner, HotSale, FlashSale


class FlashSaleListView(ListView):
    template_name = "promotions/flash_sale.html"
    context_object_name = "entries"
    paginate_by = 24

    def get_queryset(self):
        sale = (
            FlashSale.objects.filter(is_active=True)
            .order_by("-start_time")
            .first()
        )
        self.sale = sale
        if not sale:
            from .models import FlashSaleProduct

            return FlashSaleProduct.objects.none()
        return sale.entries.select_related("product").order_by("-discount_percentage")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sale"] = getattr(self, "sale", None)
        return ctx


class HotDealsListView(ListView):
    template_name = "promotions/hot_deals.html"
    context_object_name = "hot_sales"
    paginate_by = 24

    def get_queryset(self):
        return HotSale.objects.filter(is_active=True).select_related("product")
