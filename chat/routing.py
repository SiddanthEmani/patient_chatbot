from django.urls import re_path
from django.conf import settings
from django.conf.urls.static import static
from . import consumers

# This is the URL configuration for the chat application.
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<patient_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]