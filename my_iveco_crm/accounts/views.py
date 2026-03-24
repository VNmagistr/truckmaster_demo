# accounts/views.py
import io
import json
import logging
import urllib.request

import qrcode
import qrcode.image.svg

from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, MyTokenObtainPairSerializer

logger = logging.getLogger(__name__)


class AuthRateThrottle(AnonRateThrottle):
    rate = '10/minute'


class ContactRateThrottle(AnonRateThrottle):
    rate = '5/hour'


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    throttle_classes = [AuthRateThrottle]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    throttle_classes = [AuthRateThrottle]
    serializer_class = RegisterSerializer


class ContactFormView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [ContactRateThrottle]

    def post(self, request):
        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        message = request.data.get('message', '').strip()

        if not name or not phone:

            return Response({'error': "Ім'я та телефон обов'язкові"}, status=400)
        from .tasks import notify_admins_contact_form
        notify_admins_contact_form.delay(name, phone, message)
        return Response({'success': True})


class PlacesReviewsView(APIView):
    """
    Повертає рейтинг та відгуки з Google Maps.
    Результат кешується на 24 години.
    """
    permission_classes = [AllowAny]
    _CACHE_KEY = 'google_places_reviews'
    _CACHE_TTL = 60 * 60 * 24  # 24 години
    _PLACE_ID = 'ChIJW5GVz0rFOkcR1WzdVmo_Kdw'
    _MAPS_URL = 'https://maps.app.goo.gl/mw4fVkobK3tsrpQ88'

    def get(self, request):
        cached = cache.get(self._CACHE_KEY)
        if cached:
            return Response(cached)

        api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
        if not api_key:
            logger.warning('GOOGLE_PLACES_API_KEY не встановлено')
            return Response({'error': 'API key not configured'}, status=503)

        url = (
            f'https://maps.googleapis.com/maps/api/place/details/json'
            f'?place_id={self._PLACE_ID}'
            f'&fields=name,rating,user_ratings_total,reviews'
            f'&language=uk'
            f'&key={api_key}'
        )

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            logger.error(f'PlacesReviewsView: помилка запиту: {e}')
            return Response({'error': 'Failed to fetch reviews'}, status=502)

        if data.get('status') != 'OK':
            logger.error(f'PlacesReviewsView: статус {data.get("status")}')
            return Response({'error': data.get('status')}, status=502)

        result = data.get('result', {})
        payload = {
            'rating': result.get('rating'),
            'user_ratings_total': result.get('user_ratings_total'),
            'maps_url': self._MAPS_URL,
            'reviews': [
                {
                    'author_name': r.get('author_name'),
                    'rating': r.get('rating'),
                    'text': r.get('text', ''),
                    'relative_time_description': r.get('relative_time_description'),
                    'profile_photo_url': r.get('profile_photo_url'),
                }
                for r in result.get('reviews', [])
            ],
        }
        cache.set(self._CACHE_KEY, payload, self._CACHE_TTL)
        return Response(payload)


class MapsQRView(APIView):
    """
    Повертає SVG QR-код з посиланням на Google Maps.
    GET /api/accounts/qr/maps/
    """
    permission_classes = [AllowAny]
    _MAPS_URL = 'https://maps.app.goo.gl/mw4fVkobK3tsrpQ88'

    def get(self, request):
        svg_bytes = _generate_maps_qr_svg()
        return HttpResponse(svg_bytes, content_type='image/svg+xml')


def _generate_maps_qr_svg():
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
        image_factory=factory,
    )
    qr.add_data(MapsQRView._MAPS_URL)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()
