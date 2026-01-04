#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_iveco_crm.settings')
django.setup()

from bot.tasks import send_reminder_to_user_by_id
from bot.models import BotUser

user = BotUser.objects.first()
print(f'📤 Відправка тесту для: {user.get_full_name()} (Telegram ID: {user.telegram_id})')

message = '''🔔 Тестове нагадування TruckMaster

Привіт! Це тестове повідомлення системи нагадувань.

Якщо ви отримали це - система працює правильно! ✅'''

result = send_reminder_to_user_by_id.delay(user.id, message)
print(f'✅ Task ID: {result.id}')
print('🔍 Дивіться логи: tail -f /var/log/celery/worker.log')
print('📱 Перевірте Telegram!')
