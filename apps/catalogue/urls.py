from django.urls import path

from . import views

app_name = "catalogue"

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product"),
    path("categories/<slug:slug>/", views.CategoryDetailView.as_view(), name="category"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("search/suggest/", views.SearchSuggestView.as_view(), name="search_suggest"),
]
