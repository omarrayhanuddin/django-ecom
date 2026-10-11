"""Context processor exposing active promotions to all templates."""
from django.core.cache import cache

from .services import get_active_flash_sale


def active_promotions(request):
    key = "active_flash_sale_v1"
    flash_sale = cache.get(key)
    if flash_sale is None:
        flash_sale = get_active_flash_sale()
        cache.set(key, flash_sale, 60)
    return {"active_flash_sale": flash_sale}
