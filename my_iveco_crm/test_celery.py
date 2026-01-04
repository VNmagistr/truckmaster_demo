#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_iveco_crm.settings')
django.setup()

from bot.tasks import send_reminder_to_user_by_id
from bot.models import BotUser

user = BotUser.objects.first()
print(f'📤 Тест для: {user.get_full_name()} (ID: {user.telegram_id})')

message = '🔔 Тестове нагадування! Якщо ви це бачите - система працює! ✅'

result = send_reminder_to_user_by_id.delay(user.id, message)
print(f'✅ Task створено: {result.id}')
print('Перевірте Telegram!')
