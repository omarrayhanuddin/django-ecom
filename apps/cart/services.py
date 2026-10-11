"""Cart retrieval and mutation helpers."""
from apps.common.money import as_decimal

from .models import Cart, CartItem


def get_cart(request, create=True):
    """Return the current cart for the user or session."""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart is None and create:
            cart = Cart.objects.create(user=request.user)
        return cart

    if not request.session.session_key:
        if not create:
            return None
        request.session.create()
    key = request.session.session_key
    cart = Cart.objects.filter(session_key=key).first()
    if cart is None and create:
        cart = Cart.objects.create(session_key=key)
    return cart


def _available_stock(product, variant):
    if not product.track_inventory:
        return None  # unlimited
    if variant is not None:
        return variant.stock_quantity
    return product.stock_quantity


def add_item(cart, product, variant=None, quantity=1):
    """Add (or increment) a line. Returns ``(item, error)``."""
    quantity = max(1, int(quantity or 1))
    available = _available_stock(product, variant)
    if available is not None and available <= 0:
        return None, "পণ্যটি বর্তমানে স্টকে নেই।"

    price = variant.effective_price if variant is not None else product.get_effective_price()
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": 0, "unit_price": price},
    )
    new_qty = item.quantity + quantity
    if available is not None and new_qty > available:
        new_qty = available
    item.quantity = new_qty
    item.unit_price = price  # refresh to current price
    item.save(update_fields=["quantity", "unit_price"])
    return item, ""


def set_quantity(item, quantity):
    quantity = int(quantity)
    if quantity <= 0:
        item.delete()
        return None
    available = _available_stock(item.product, item.variant)
    if available is not None:
        quantity = min(quantity, available)
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def remove_item(item):
    item.delete()


def clear_cart(cart):
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon"])


def merge_carts(request, user=None):
    """Merge a guest session cart into the user's cart on login.

    Collision policy: keep the larger quantity (clamped), never sum duplicates.
    """
    user = user or getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    session = getattr(request, "session", None)
    session_key = session.session_key if session is not None else None
    if not session_key:
        return None
    guest_cart = Cart.objects.filter(session_key=session_key).first()
    if not guest_cart:
        return None

    user_cart, _ = Cart.objects.get_or_create(user=user)
    for g_item in guest_cart.items.select_related("product", "variant"):
        existing = user_cart.items.filter(
            product=g_item.product, variant=g_item.variant
        ).first()
        if existing:
            existing.quantity = max(existing.quantity, g_item.quantity)
            existing.save(update_fields=["quantity"])
        else:
            g_item.cart = user_cart
            g_item.save(update_fields=["cart"])
    guest_cart.delete()
    return user_cart
