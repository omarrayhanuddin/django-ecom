from celery import shared_task
from django.utils import timezone


@shared_task
def deactivate_expired_flash_sales():
    from .models import FlashSale

    count = FlashSale.objects.filter(
        is_active=True, end_time__lt=timezone.now()
    ).update(is_active=False)
    return count
