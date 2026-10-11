from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView

from apps.cart.services import get_cart
from apps.orders.models import Order, PaymentInstruction

from .forms import CheckoutForm
from .services import create_order_from_cart


class CheckoutView(LoginRequiredMixin, FormView):
    """Checkout requires an authenticated user (guests are sent to login)."""

    template_name = "orders/checkout.html"
    form_class = CheckoutForm
    login_url = "/accounts/login/"

    def dispatch(self, request, *args, **kwargs):
        self.cart = get_cart(request, create=False)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cart"] = self.cart
        ctx["instructions"] = PaymentInstruction.objects.filter(is_active=True)
        return ctx

    def get(self, request, *args, **kwargs):
        if not self.cart or not self.cart.items.exists():
            messages.info(request, "আপনার কার্ট খালি।")
            return redirect("cart:detail")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.cart or not self.cart.items.exists():
            return redirect("cart:detail")
        order = create_order_from_cart(self.cart, form.cleaned_data, self.request.user)
        messages.success(
            self.request, f"অর্ডার সফলভাবে জমা হয়েছে: {order.order_number}"
        )
        return redirect("orders:confirmation", token=order.public_token)


class OrderConfirmationView(DetailView):
    model = Order
    template_name = "orders/confirmation.html"
    context_object_name = "order"
    slug_field = "public_token"
    slug_url_kwarg = "token"


class OrderListView(LoginRequiredMixin, ListView):
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 15

    def get_queryset(self):
        return self.request.user.orders.prefetch_related("items").order_by("-created_at")


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_object(self, queryset=None):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"), order_number=self.kwargs["order_number"]
        )
        is_owner = order.user_id and order.user_id == self.request.user.id
        if not (is_owner or self.request.user.is_staff):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return order


class OrderTrackView(DetailView):
    """Public, token-based tracking for guests (and anyone with the link)."""

    model = Order
    template_name = "orders/order_detail.html"
    context_object_name = "order"
    slug_field = "public_token"
    slug_url_kwarg = "token"
