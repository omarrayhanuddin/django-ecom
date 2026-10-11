from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("onboarding/", views.OnboardingView.as_view(), name="onboarding"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("addresses/", views.AddressListView.as_view(), name="addresses"),
    path(
        "addresses/<int:pk>/delete/",
        views.AddressDeleteView.as_view(),
        name="address_delete",
    ),
]
