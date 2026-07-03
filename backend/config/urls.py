from django.urls import path

from apps.agent.views import chat_stream
from config.api import api

urlpatterns = [
    path("chat", chat_stream),
    path("", api.urls),
]
