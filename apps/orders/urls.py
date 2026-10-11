from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.OrderListView.as_view(), name="list"),
    path("confirm/<uuid:token>/", views.OrderConfirmationView.as_view(), name="confirmation"),
    path("track/<uuid:token>/", views.OrderTrackView.as_view(), name="track"),
    path("<str:order_number>/", views.OrderDetailView.as_view(), name="detail"),
]
