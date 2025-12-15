# bot/handlers/guest.py

"""
Обробники для гостей (незареєстрованих користувачів)
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..utils import log_message

logger = logging.getLogger(__name__)


# Гості мають обмежений доступ, основна логіка в common.py
# Тут можна додати додаткові обробники для гостей при необхідності

guest_handlers = []  # Список обробників для гостей