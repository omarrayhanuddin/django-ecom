"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("accounts/", include("allauth.urls")),
    path("cart/", include("apps.cart.urls", namespace="cart")),
    path("checkout/", include("apps.orders.checkout_urls", namespace="checkout")),
    path("orders/", include("apps.orders.urls", namespace="orders")),
    path("promotions/", include("apps.promotions.urls", namespace="promotions")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    path("", include("apps.catalogue.urls", namespace="catalogue")),
    path("", include("apps.pages.urls", namespace="pages")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA", False):
    # Demo only: serve uploaded media through Django when not in DEBUG.
    from django.views.static import serve as media_serve

    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT})
    ]
