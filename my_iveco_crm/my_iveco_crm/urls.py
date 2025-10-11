# my_iveco_crm/urls.py

from django.contrib import admin
from django.urls import path, include # Переконайтесь, що 'include' імпортовано
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Підключаємо маршрути з наших додатків
    path('api/', include('clients.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('inventory.urls')),
    
    # Маршрути для автентифікації залишаємо тут або виносимо в 'accounts.urls'
    path('api/', include('accounts.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)