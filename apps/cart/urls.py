from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.CartDetailView.as_view(), name="detail"),
    path("add/", views.add_to_cart, name="add"),
    path("panel/", views.CartPanelView.as_view(), name="panel"),
    path("badge/", views.CartBadgeView.as_view(), name="badge"),
    path("item/<int:pk>/", views.cart_item, name="item"),
    path("apply-coupon/", views.apply_coupon, name="apply_coupon"),
    path("remove-coupon/", views.remove_coupon, name="remove_coupon"),
]
