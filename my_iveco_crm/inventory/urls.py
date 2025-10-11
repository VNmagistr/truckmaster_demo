# inventory/urls.py

from rest_framework.routers import DefaultRouter
from .views import PartViewSet

router = DefaultRouter()
router.register(r'parts', PartViewSet)

urlpatterns = router.urls