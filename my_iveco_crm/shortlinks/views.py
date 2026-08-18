from django.db.models import F
from django.http import HttpResponse, HttpResponseRedirect
from django.views import View
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ShortLink
from .serializers import ShortLinkSerializer

DISABLED_PAGE = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Сторінка недоступна</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
background:#f7f7f7;color:#1a1a1a;display:flex;align-items:center;
justify-content:center;min-height:100vh;padding:24px}
.card{background:#fff;border-radius:12px;padding:48px 32px;
max-width:440px;width:100%;text-align:center;
box-shadow:0 2px 12px rgba(0,0,0,.08);border-top:4px solid #f5c518}
.icon{font-size:48px;margin-bottom:16px}
h1{font-size:20px;font-weight:600;margin-bottom:12px}
p{font-size:15px;color:#666;line-height:1.5}
</style>
</head>
<body>
<div class="card">
<div class="icon">🔒</div>
<h1>Сторінка недоступна</h1>
<p>Вибачте, дана сторінка на даний момент недоступна.
Спробуйте, будь ласка, пізніше.</p>
</div>
</body>
</html>"""


class ShortLinkRedirectView(View):
    """GET /go/<slug>/ → 302 на target_url з ShortLink."""

    def get(self, request, slug):
        try:
            link = ShortLink.objects.only('id', 'target_url', 'is_active').get(slug=slug)
        except ShortLink.DoesNotExist:
            return HttpResponse(DISABLED_PAGE, status=404, content_type='text/html')
        if not link.is_active:
            return HttpResponse(DISABLED_PAGE, status=200, content_type='text/html')
        ShortLink.objects.filter(pk=link.pk).update(hits=F('hits') + 1)
        return HttpResponseRedirect(link.target_url)


class ShortLinkListView(APIView):
    """GET /api/shortlinks/ — список QR-кодів."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ShortLink.objects.all()
        return Response(ShortLinkSerializer(qs, many=True).data)


class ShortLinkToggleView(APIView):
    """POST /api/shortlinks/<pk>/toggle/ — вмикає/вимикає QR-код."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            link = ShortLink.objects.get(pk=pk)
        except ShortLink.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=404)
        link.is_active = not link.is_active
        link.save(update_fields=['is_active', 'updated_at'])
        return Response(ShortLinkSerializer(link).data)
