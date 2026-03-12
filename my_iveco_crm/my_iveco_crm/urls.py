# my_iveco_crm/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Аутентифікація
    path('api/', include('accounts.urls')),

    # Користувачі
    path('api/', include('users.urls')),
    
    # Основні модулі
    path('api/', include('clients.urls')),
    path('api/', include('orders.urls')),
    
    # Склад та товари
    path('api/inventory/', include('inventory.urls')),
    
    # Обслуговування
    path('api/maintenance/', include('maintenance.urls')),

    # Bot API
    path('api/bot/', include('bot.urls')),

    # Client cabinet
    path('api/cabinet/', include('cabinet.urls')),

    # Appointments
    path('api/', include('appointments.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)