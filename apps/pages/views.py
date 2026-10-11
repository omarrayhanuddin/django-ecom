from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, ListView, TemplateView

from apps.analytics.live import live_count
from apps.analytics.models import SiteVisit
from apps.catalogue.models import Brand, Category, Product
from apps.promotions.models import Banner, HotSale
from apps.promotions.services import get_active_flash_sale

from .forms import ContactForm
from .models import StaticPage, StoreLocation


class HomeView(TemplateView):
    template_name = "home/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        ctx["hero_banners"] = Banner.objects.filter(
            is_active=True, position=Banner.Position.HERO
        )
        ctx["featured_categories"] = Category.objects.filter(is_featured=True)[:8]

        flash_sale = get_active_flash_sale()
        ctx["flash_sale"] = flash_sale
        ctx["flash_entries"] = (
            flash_sale.entries.select_related("product")[:8] if flash_sale else []
        )

        ctx["hot_deals"] = HotSale.objects.filter(is_active=True).select_related("product")[:8]
        ctx["trending"] = Product.objects.filter(is_trending=True)[:12]
        ctx["top_rated"] = Product.objects.filter(is_top_rated=True)[:12]
        ctx["best_sellers"] = Product.objects.filter(is_best_seller=True)[:12]
        ctx["featured_products"] = Product.objects.filter(is_featured=True)[:12]

        # Recommended for you (spec §15.7)
        recommended = Product.objects.none()
        if user.is_authenticated and user.orders.exists():
            category_ids = (
                user.orders.values_list("items__product__category_id", flat=True)
                .exclude(items__product__category_id=None)
                .distinct()
            )
            recommended = Product.objects.filter(category_id__in=list(category_ids))[:12]
        if not recommended.exists():
            recommended = Product.objects.filter(is_best_seller=True)[:12]
        ctx["recommended"] = recommended

        ctx["total_visits"] = SiteVisit.total_count()
        ctx["live_count"] = live_count()
        return ctx


class StaticPageView(TemplateView):
    template_name = "pages/static_page.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page"] = get_object_or_404(
            StaticPage, slug=self.kwargs["slug"], is_published=True
        )
        return ctx


class BrandsView(ListView):
    template_name = "pages/brands.html"
    context_object_name = "brands"
    queryset = Brand.objects.all()


class StoresView(ListView):
    template_name = "pages/stores.html"
    context_object_name = "stores"
    queryset = StoreLocation.objects.all()


class ContactView(FormView):
    template_name = "pages/contact.html"
    form_class = ContactForm
    success_url = "/contact/"

    def form_valid(self, form):
        data = form.cleaned_data
        send_mail(
            subject=f"Contact: {data['subject']}",
            message=f"From: {data['name']} <{data['email']}>\n\n{data['message']}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )
        messages.success(self.request, "ধন্যবাদ! আমরা শীঘ্রই যোগাযোগ করব।")
        return super().form_valid(form)
