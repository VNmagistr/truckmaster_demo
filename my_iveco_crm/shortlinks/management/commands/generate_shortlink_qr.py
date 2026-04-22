import io
import os

import qrcode
import qrcode.image.svg

from django.core.management.base import BaseCommand, CommandError

from shortlinks.models import ShortLink


class Command(BaseCommand):
    help = 'Generates an SVG QR code that points to /go/<slug> on the public domain.'

    def add_arguments(self, parser):
        parser.add_argument('slug', help="ShortLink slug (e.g. 'maps')")
        parser.add_argument(
            '--base-url',
            default='https://ital-truck.com.ua',
            help='Public base URL (default: https://ital-truck.com.ua)',
        )
        parser.add_argument(
            '--output',
            default=None,
            help='Output file path (default: qr_<slug>.svg)',
        )

    def handle(self, *args, **options):
        slug = options['slug']
        base_url = options['base_url'].rstrip('/')
        output = options['output'] or f'qr_{slug}.svg'

        if not ShortLink.objects.filter(slug=slug, is_active=True).exists():
            raise CommandError(
                f"Active ShortLink with slug '{slug}' not found. "
                f"Create it in admin first: /admin/shortlinks/shortlink/add/"
            )

        url = f'{base_url}/go/{slug}'

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
            image_factory=qrcode.image.svg.SvgPathImage,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf)

        with open(output, 'wb') as f:
            f.write(buf.getvalue())

        self.stdout.write(self.style.SUCCESS(
            f'QR for {url} saved to {os.path.abspath(output)}'
        ))
