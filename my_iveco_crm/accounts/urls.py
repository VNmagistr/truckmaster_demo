# accounts/urls.py
from django.urls import path
from .views import MyTokenObtainPairView, ContactFormView, PlacesReviewsView, MapsQRView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('contact/', ContactFormView.as_view(), name='contact'),
    path('places-reviews/', PlacesReviewsView.as_view(), name='places_reviews'),
    path('qr/maps/', MapsQRView.as_view(), name='maps_qr'),
]
