from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task
def cleanup_stale_live_visitors():
    from .live import cleanup_stale

    return cleanup_stale()


@shared_task
def purge_old_site_visits(days=365):
    from .models import SiteVisit

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = SiteVisit.objects.filter(visited_at__lt=cutoff).delete()
    return deleted
