from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("live-count/", views.live_count_partial, name="live_count"),
    path("stats/", views.stats, name="stats"),
]
