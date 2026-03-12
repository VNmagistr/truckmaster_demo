"""
WhatsApp Cloud API utility.

Env vars required:
  WHATSAPP_ACCESS_TOKEN    — permanent token from Meta App
  WHATSAPP_PHONE_NUMBER_ID — ID of the WhatsApp Business phone number

NOTE: Free-form text messages only work within 24h after the customer
      has messaged your bot first. For business-initiated notifications
      (confirmations, reminders), you must use pre-approved templates.
      See send_whatsapp_template() for template usage.
"""
import json
import logging
import os
import re
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v19.0"


def _normalize_phone(phone: str) -> str | None:
    """Convert phone to WhatsApp format: digits only, no leading +.
    E.g. '+380 67 123-45-67' -> '380671234567'
    """
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return None
    # Remove leading 0 if present (local format)
    if digits.startswith('0') and len(digits) == 10:
        digits = '38' + digits
    return digits


def _post(phone_number_id: str, token: str, payload: dict) -> dict | None:
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        logger.error(f"WhatsApp API HTTP error {e.code}: {body}")
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
    return None


def send_whatsapp_text(phone: str, text: str) -> dict | None:
    """
    Send a free-form text message.
    Works only within 24h after the customer has messaged your bot,
    OR when sending to test numbers in the Meta sandbox.
    """
    token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
    phone_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    if not token or not phone_id:
        logger.warning("WhatsApp credentials not set (WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID)")
        return None

    normalized = _normalize_phone(phone)
    if not normalized:
        logger.warning(f"Invalid phone for WhatsApp: {phone!r}")
        return None

    payload = {
        'messaging_product': 'whatsapp',
        'to': normalized,
        'type': 'text',
        'text': {'preview_url': False, 'body': text},
    }
    return _post(phone_id, token, payload)


def send_whatsapp_template(phone: str, template_name: str,
                            language_code: str = 'uk',
                            components: list | None = None) -> dict | None:
    """
    Send a pre-approved template message.
    Use this for business-initiated messages (confirmations, reminders).

    Example:
        send_whatsapp_template(
            phone='+380671234567',
            template_name='appointment_confirmation',
            components=[{
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': '15.03.2026 о 10:00'},
                    {'type': 'text', 'text': 'AA 1234 BB'},
                ],
            }]
        )
    """
    token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
    phone_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    if not token or not phone_id:
        logger.warning("WhatsApp credentials not set")
        return None

    normalized = _normalize_phone(phone)
    if not normalized:
        return None

    template: dict = {
        'name': template_name,
        'language': {'code': language_code},
    }
    if components:
        template['components'] = components

    payload = {
        'messaging_product': 'whatsapp',
        'to': normalized,
        'type': 'template',
        'template': template,
    }
    return _post(phone_id, token, payload)
