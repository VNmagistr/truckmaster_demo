from django.urls import path

from .views import ShortLinkRedirectView


urlpatterns = [
    path('<slug:slug>/', ShortLinkRedirectView.as_view(), name='shortlink_redirect'),
    path('<slug:slug>', ShortLinkRedirectView.as_view()),
]
