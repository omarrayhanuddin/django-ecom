from django.urls import path

from . import views

app_name = "promotions"

urlpatterns = [
    path("flash-sale/", views.FlashSaleListView.as_view(), name="flash_sale"),
    path("hot-deals/", views.HotDealsListView.as_view(), name="hot_deals"),
]
