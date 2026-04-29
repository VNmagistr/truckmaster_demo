from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BotUserViewSet, MessageLogViewSet, ReminderSettingsViewSet,
    UnknownPlateSearchViewSet,
)

router = DefaultRouter()
router.register(r'users', BotUserViewSet)
router.register(r'messages', MessageLogViewSet)
router.register(r'reminders', ReminderSettingsViewSet)
router.register(r'unknown-plates', UnknownPlateSearchViewSet)

urlpatterns = [
    path('', include(router.urls)),
]