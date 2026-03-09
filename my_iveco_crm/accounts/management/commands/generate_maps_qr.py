import os

from django.core.management.base import BaseCommand

from accounts.views import _generate_maps_qr_svg


class Command(BaseCommand):
    help = 'Generates a QR code SVG for the Google Maps location'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='qr_maps.svg',
            help='Output file path (default: qr_maps.svg)',
        )

    def handle(self, *args, **options):
        output = options['output']
        svg_bytes = _generate_maps_qr_svg()
        with open(output, 'wb') as f:
            f.write(svg_bytes)
        self.stdout.write(self.style.SUCCESS(f'QR code saved to {os.path.abspath(output)}'))
