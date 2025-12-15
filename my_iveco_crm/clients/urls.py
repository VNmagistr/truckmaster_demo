from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, TruckViewSet, IvecoBaseModelViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'trucks', TruckViewSet)
router.register(r'base-models', IvecoBaseModelViewSet)

urlpatterns = router.urls