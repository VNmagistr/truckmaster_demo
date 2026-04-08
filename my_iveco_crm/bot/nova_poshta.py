"""Функції для роботи з Новою Поштою в боті."""
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


@sync_to_async
def get_client_invoices_with_declarations(bot_user):
    from invoices.models import Invoice
    if not bot_user or not bot_user.client:
        return []
    return list(
        Invoice.objects.filter(
            client=bot_user.client,
            nova_poshta_declaration__isnull=False,
        ).exclude(nova_poshta_declaration='')
        .order_by('-date')[:20]
    )


@sync_to_async
def client_owns_declaration(bot_user, declaration: str) -> bool:
    from invoices.models import Invoice
    if not bot_user or not bot_user.client:
        return False
    return Invoice.objects.filter(
        client=bot_user.client,
        nova_poshta_declaration=declaration,
    ).exists()


def _np_api_track(declaration: str) -> dict:
    import requests as req
    from django.conf import settings
    api_key = getattr(settings, 'NP_API_KEY', '')
    if not api_key:
        return {'error': 'NP_API_KEY не налаштовано'}
    payload = {
        'apiKey': api_key,
        'modelName': 'TrackingDocument',
        'calledMethod': 'getStatusDocuments',
        'methodProperties': {'Documents': [{'DocumentNumber': declaration}]},
    }
    try:
        r = req.post('https://api.novaposhta.ua/v2.0/json/', json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get('success') or not data.get('data'):
            return {'error': data.get('errors', ['Помилка API'])[0]}
        return data['data'][0]
    except Exception as e:
        return {'error': str(e)}


np_api_track = sync_to_async(_np_api_track)


def format_np_status(data: dict) -> str:
    if 'error' in data:
        return f"❌ {data['error']}"
    lines = [f"📦 *{data.get('Status', '—')}*"]
    if data.get('CityRecipient'):
        lines.append(f"📍 Місто: {data['CityRecipient']}")
    if data.get('WarehouseRecipientAddress'):
        lines.append(f"🏢 Відділення: {data['WarehouseRecipientAddress']}")
    if data.get('ActualDeliveryDate'):
        lines.append(f"✅ Отримано: {data['ActualDeliveryDate']}")
    elif data.get('ScheduledDeliveryDate'):
        lines.append(f"📅 Очікується: {data['ScheduledDeliveryDate']}")
    if data.get('DateScan'):
        lines.append(f"🔍 Скановано: {data['DateScan']}")
    return '\n'.join(lines)
