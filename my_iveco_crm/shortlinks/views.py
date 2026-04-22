from django.db.models import F
from django.http import Http404, HttpResponseRedirect
from django.views import View

from .models import ShortLink


class ShortLinkRedirectView(View):
    """GET /go/<slug>/ → 302 на target_url з ShortLink."""

    def get(self, request, slug):
        try:
            link = ShortLink.objects.only('id', 'target_url', 'is_active').get(slug=slug)
        except ShortLink.DoesNotExist:
            raise Http404('Short link not found')
        if not link.is_active:
            raise Http404('Short link is disabled')
        ShortLink.objects.filter(pk=link.pk).update(hits=F('hits') + 1)
        return HttpResponseRedirect(link.target_url)
