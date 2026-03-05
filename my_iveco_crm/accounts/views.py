# accounts/views.py
import asyncio
import logging
import os

from django.contrib.auth.models import User
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

        self._notify_admins(name, phone, message)
        return Response({'success': True})

    def _notify_admins(self, name, phone, message):
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return

        try:
            from bot.models import BotUser
            from telegram import Bot

            admins = list(BotUser.objects.filter(role='admin', is_active=True))
            if not admins:
                logger.warning('ContactForm: немає admin BotUser для надсилання')
                return

            text = f'📩 *Нова заявка з сайту*\n\n👤 Ім\'я: {name}\n📞 Телефон: {phone}'
            if message:
                text += f'\n💬 Повідомлення: {message}'

            bot = Bot(token=bot_token)
            for admin in admins:
                try:
                    asyncio.run(bot.send_message(
                        chat_id=admin.telegram_id,
                        text=text,
                        parse_mode='Markdown',
                    ))
                except Exception as e:
                    logger.error(f'ContactForm: помилка надсилання до {admin.telegram_id}: {e}')

        except Exception as e:
            logger.error(f'ContactForm: _notify_admins помилка: {e}')