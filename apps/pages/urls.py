from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.StaticPageView.as_view(), {"slug": "about"}, name="about"),
    path("privacy/", views.StaticPageView.as_view(), {"slug": "privacy"}, name="privacy"),
    path("terms/", views.StaticPageView.as_view(), {"slug": "terms"}, name="terms"),
    path("brands/", views.BrandsView.as_view(), name="brands"),
    path("stores/", views.StoresView.as_view(), name="stores"),
    path("contact/", views.ContactView.as_view(), name="contact"),
]
