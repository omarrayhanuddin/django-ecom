from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .services import merge_carts


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    if request is not None:
        merge_carts(request)
