import logging
from django.urls import path
from django.views.generic import RedirectView
from . import views

# Set up logging
logger = logging.getLogger(__name__)

# URL configuration for the chat application.
urlpatterns = [
    path('', views.home, name='Chat'), # URL for the chat view
]

# Log the URL patterns
logger.info("URL patterns for chat application: %s", urlpatterns)