from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.catalogue.models import Product, ProductVariant
from apps.common.middleware import get_real_method
from apps.promotions.services import validate_coupon

from .models import CartItem
from .services import add_item, get_cart, remove_item, set_quantity

PANEL_TEMPLATE = "partials/cart_panel.html"
RESPONSE_TEMPLATE = "partials/cart_response.html"


def _count(request):
    cart = get_cart(request, create=False)
    return cart.item_count if cart else 0


class CartDetailView(TemplateView):
    template_name = "cart/cart.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cart"] = get_cart(self.request, create=False)
        return ctx


class CartPanelView(TemplateView):
    """Returns the cart panel partial (drawer body content)."""

    template_name = PANEL_TEMPLATE

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cart"] = get_cart(self.request, create=False)
        return ctx


class CartBadgeView(TemplateView):
    template_name = "partials/cart_badge.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cart_item_count"] = _count(self.request)
        return ctx


def _response(request, **extra):
    """Render the OOB-badge + panel response used by all cart mutations."""
    cart = get_cart(request, create=False)
    ctx = {"cart": cart}
    ctx.update(extra)
    return render(request, RESPONSE_TEMPLATE, ctx)


@require_POST
def add_to_cart(request):
    product = get_object_or_404(Product, pk=request.POST.get("product_id"))
    variant = None
    variant_id = request.POST.get("variant_id")
    if variant_id:
        variant = ProductVariant.objects.filter(pk=variant_id, product=product).first()
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    cart = get_cart(request)
    _item, error = add_item(cart, product, variant, quantity)
    if error:
        resp = render(request, "partials/alert.html", {"message": error, "level": "warning"})
        resp["HX-Trigger"] = "opencart"
        return resp
    # Badge-only response; the drawer body loads itself via the `opencart` event.
    resp = render(
        request, "partials/cart_badge.html", {"cart_item_count": _count(request)}
    )
    resp["HX-Trigger"] = "opencart"
    return resp


def cart_item(request, pk):
    cart = get_cart(request, create=False)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    if get_real_method(request) == "DELETE":
        remove_item(item)
    else:
        try:
            quantity = int(request.POST.get("quantity", item.quantity))
        except (TypeError, ValueError):
            quantity = item.quantity
        set_quantity(item, quantity)
    return _response(request)


@require_POST
def apply_coupon(request):
    cart = get_cart(request)
    code = request.POST.get("code", "")
    coupon, discount, error = validate_coupon(code, request.user, cart.subtotal)
    if error:
        return _response(request, coupon_error=error)
    cart.coupon = coupon
    cart.save(update_fields=["coupon"])
    return _response(request, coupon_success=f"কুপন প্রয়োগ হয়েছে, ছাড় ৳{discount}")


@require_POST
def remove_coupon(request):
    cart = get_cart(request, create=False)
    if cart:
        cart.coupon = None
        cart.save(update_fields=["coupon"])
    return _response(request)
