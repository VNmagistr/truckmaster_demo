# core/urls.py

from django.urls import path

from .views import ModuleListView, EnumsView

urlpatterns = [
    path('modules/', ModuleListView.as_view(), name='modules-list'),
    path('enums/', EnumsView.as_view(), name='enums'),
]
