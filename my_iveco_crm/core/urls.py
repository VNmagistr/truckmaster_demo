# core/urls.py

from django.urls import path

from .views import ModuleListView

urlpatterns = [
    path('modules/', ModuleListView.as_view(), name='modules-list'),
]
