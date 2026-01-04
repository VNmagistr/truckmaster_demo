#!/usr/bin/env python3
import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

async def test_send():
    bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
    chat_id = 1348968236  # Ваш Telegram ID
    
    try:
        message = await bot.send_message(
            chat_id=chat_id,
            text="🔔 Тест! Якщо ви це бачите - бот може відправляти повідомлення!"
        )
        print(f"✅ Повідомлення відправлено! Message ID: {message.message_id}")
    except Exception as e:
        print(f"❌ Помилка: {e}")

asyncio.run(test_send())
