# bot/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BotUserViewSet, MessageLogViewSet, ReminderSettingsViewSet

router = DefaultRouter()
router.register(r'users', BotUserViewSet, basename='bot-user')
router.register(r'messages', MessageLogViewSet, basename='message-log')
router.register(r'reminders', ReminderSettingsViewSet, basename='reminder-settings')

urlpatterns = [
    path('', include(router.urls)),
    path('api/bot/', include('bot.urls')),
]