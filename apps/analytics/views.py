from django.shortcuts import render

from .live import live_count
from .models import SiteVisit


def live_count_partial(request):
    return render(
        request,
        "analytics/_live_count.html",
        {"live_count": live_count()},
    )


def stats(request):
    return render(
        request,
        "analytics/stats.html",
        {"total_visits": SiteVisit.total_count(), "live_count": live_count()},
    )
