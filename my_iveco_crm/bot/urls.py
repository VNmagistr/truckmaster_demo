from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BotUserViewSet, MessageLogViewSet, ReminderSettingsViewSet

router = DefaultRouter()
router.register(r'users', BotUserViewSet)
router.register(r'messages', MessageLogViewSet)
router.register(r'reminders', ReminderSettingsViewSet)

urlpatterns = [
    path('', include(router.urls)),
]