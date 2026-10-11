from django.urls import re_path

from .consumers import LiveVisitorConsumer

websocket_urlpatterns = [
    re_path(r"^ws/visitors/$", LiveVisitorConsumer.as_asgi()),
]
