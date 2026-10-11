from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView

from .constants import AVAILABILITY_CHOICES, PRODUCT_TYPE_CHOICES
from .filters import ProductFilter
from .forms import ProductReviewForm
from .models import Category, Product


def _filter_context(request):
    return {
        "availability_choices": AVAILABILITY_CHOICES,
        "product_type_choices": PRODUCT_TYPE_CHOICES,
        "selected_availability": request.GET.getlist("availability"),
        "selected_product_types": request.GET.getlist("product_type"),
    }


class ProductListView(ListView):
    model = Product
    template_name = "catalogue/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Product.objects.select_related("category", "brand")
            .prefetch_related("images", "flash_sale_entries__flash_sale", "hot_sales")
            .filter(category__isnull=False)
        )
        self.filterset = ProductFilter(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filterset
        ctx["categories"] = Category.objects.filter(parent__isnull=True)
        ctx["is_htmx"] = getattr(self.request, "htmx", False)
        ctx.update(_filter_context(self.request))
        return ctx

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["catalogue/_product_grid.html"]
        return [self.template_name]


class CategoryDetailView(ListView):
    template_name = "catalogue/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"])
        qs = Product.objects.filter(
            Q(category=self.category) | Q(category__parent=self.category)
        ).distinct()
        self.filterset = ProductFilter(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.filterset
        ctx["category"] = self.category
        ctx["categories"] = Category.objects.filter(parent__isnull=True)
        ctx["is_htmx"] = getattr(self.request, "htmx", False)
        ctx.update(_filter_context(self.request))
        return ctx

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return ["catalogue/_product_grid.html"]
        return [self.template_name]


class ProductDetailView(DetailView):
    model = Product
    template_name = "catalogue/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.prefetch_related(
            "images", "variants", "reviews__user", "flash_sale_entries__flash_sale"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product = self.object
        ctx["review_form"] = ProductReviewForm()
        ctx["reviews"] = product.reviews.filter(is_approved=True).select_related("user")
        ctx["related"] = (
            Product.objects.filter(category=product.category)
            .exclude(pk=product.pk)[:8]
        )
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            messages.info(request, "রিভিউ দিতে অনুগ্রহ করে লগইন করুন।")
            return redirect("accounts:login")
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review, created = self.object.reviews.get_or_create(
                user=request.user, defaults=form.cleaned_data
            )
            if not created:
                messages.info(request, "আপনি ইতিমধ্যে রিভিউ দিয়েছেন।")
            else:
                messages.success(request, "রিভিউ জমা হয়েছে, অনুমোদনের পরে দেখা যাবে।")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(review_form=form))


class SearchView(ProductListView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_term"] = self.request.GET.get("q", "")
        return ctx


class SearchSuggestView(ListView):
    template_name = "catalogue/_search_suggest.html"
    context_object_name = "products"

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        if len(q) < 2:
            return Product.objects.none()
        return Product.objects.filter(
            Q(name_bn__icontains=q) | Q(name_en__icontains=q) | Q(sku__icontains=q)
        )[:6]

    def get_template_names(self):
        return ["catalogue/_search_suggest.html"]
