# my_iveco_crm/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
<<<<<<< HEAD
    # API endpoints
    path('api/', include('accounts.urls')),
    path('api/', include('clients.urls')),
    path('api/', include('orders.urls')),
    path('api/inventory/', include('inventory.urls')),
=======
    # Аутентифікація
    path('api/', include('accounts.urls')),
    
    # Основні модулі
    path('api/', include('clients.urls')),
    path('api/', include('orders.urls')),
    
    # Склад та товари
    path('api/inventory/', include('inventory.urls')),
    
    # Обслуговування
>>>>>>> a1f17255c6788a0df72d1230f982c97e1a0d302d
    path('api/maintenance/', include('maintenance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)