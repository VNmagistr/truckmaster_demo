from django.urls import path

from .views import ShortLinkListView, ShortLinkToggleView


urlpatterns = [
    path('', ShortLinkListView.as_view(), name='shortlink-list'),
    path('<int:pk>/toggle/', ShortLinkToggleView.as_view(), name='shortlink-toggle'),
]
