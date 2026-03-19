# my_iveco_crm/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Система модулів
    path('api/', include('core.urls')),

    # Core-модулі (завжди доступні)
    path('api/', include('accounts.urls')),
    path('api/', include('users.urls')),
    path('api/', include('clients.urls')),
    path('api/', include('orders.urls')),

    # Optional-модулі (доступні якщо увімкнені в адмінці)
    path('api/inventory/', include('inventory.urls')),
    path('api/maintenance/', include('maintenance.urls')),
    path('api/cabinet/', include('cabinet.urls')),
    path('api/bot/', include('bot.urls')),
    path('api/', include('appointments.urls')),
    path('api/', include('alpr.urls')),
    path('api/', include('invoices.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)