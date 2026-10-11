"""Expose the current cart to all templates (navbar badge, drawer)."""


def cart_summary(request):
    try:
        from .services import get_cart

        cart = get_cart(request, create=False)
    except Exception:
        cart = None
    return {
        "cart": cart,
        "cart_item_count": cart.item_count if cart else 0,
    }
