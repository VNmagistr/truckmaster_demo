import logging
from typing import List, Optional, Dict, Any
from asgiref.sync import sync_to_async
from django.db.models import Q, Count
from django.utils import timezone

# Імпортуємо тільки те, що існує
from .models import BotUser, BotMessageLog, ReminderSettings
from clients.models import Client, Truck
from orders.models import ServiceOrder

logger = logging.getLogger(__name__)

# ========== КОРИСТУВАЧІ ==========

class UserService:
    @staticmethod
    @sync_to_async
    def get_or_create_user(telegram_id: int, **user_data) -> tuple[BotUser, bool]:
        return BotUser.objects.get_or_create(telegram_id=telegram_id, defaults=user_data)
    
    @staticmethod
    @sync_to_async
    def get_user_by_telegram_id(telegram_id: int) -> Optional[BotUser]:
        try:
            return BotUser.objects.select_related('client').get(telegram_id=telegram_id)
        except BotUser.DoesNotExist:
            return None

    @staticmethod
    @sync_to_async
    def get_user_statistics(bot_user: BotUser) -> Dict[str, Any]:
        total_messages = BotMessageLog.objects.filter(bot_user=bot_user).count()
        incoming = BotMessageLog.objects.filter(bot_user=bot_user, is_incoming=True).count()
        outgoing = total_messages - incoming
        
        return {
            'total_messages': total_messages,
            'incoming': incoming,
            'outgoing': outgoing,
            'registered': bot_user.created_at,
            'last_activity': bot_user.last_activity,
        }

# ========== АВТОМОБІЛІ ==========

class TruckService:
    @staticmethod
    @sync_to_async
    def get_user_trucks(bot_user: BotUser) -> List[Truck]:
        """Отримує список автомобілів (Тільки для власників та адмінів)"""
        # Прибрали driver та manager
        if bot_user.role == 'owner' and bot_user.client:
            return list(Truck.objects.filter(client=bot_user.client).select_related('base_model'))
        elif bot_user.role == 'admin':
            return list(Truck.objects.all().select_related('base_model', 'client')[:50])
        return []
    
    @staticmethod
    @sync_to_async
    def get_truck_by_id(truck_id: int) -> Optional[Truck]:
        try:
            return Truck.objects.select_related('base_model', 'client').get(id=truck_id)
        except Truck.DoesNotExist:
            return None

    @staticmethod
    @sync_to_async
    def search_truck_by_plate(plate_query: str) -> List[Truck]:
        clean_query = ''.join(c for c in plate_query.upper() if c.isalnum())
        if not clean_query: return []
        
        trucks = Truck.objects.filter(
            Q(license_plate__icontains=clean_query) |
            Q(license_plate__icontains=plate_query)
        ).select_related('base_model', 'client')[:20]
        return list(trucks)

# ========== ЗАМОВЛЕННЯ ==========

class OrderService:
    @staticmethod
    @sync_to_async
    def get_order_by_number(order_number: str) -> Optional[ServiceOrder]:
        try:
            return ServiceOrder.objects.select_related('client', 'truck').get(order_number=order_number)
        except ServiceOrder.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def get_active_orders(bot_user: BotUser) -> List[ServiceOrder]:
        # Тільки для власників (прибрали driver)
        if bot_user.role == 'owner' and bot_user.client:
            return list(
                ServiceOrder.objects.filter(
                    client=bot_user.client,
                    status__in=['OPEN', 'IN_PROGRESS']
                ).select_related('truck').order_by('-created_at')
            )
        return []

# ========== НАГАДУВАННЯ ==========

class ReminderService:
    @staticmethod
    @sync_to_async
    def get_user_reminders(bot_user: BotUser) -> List[ReminderSettings]:
        return list(ReminderSettings.objects.filter(bot_user=bot_user).select_related('truck'))

# ========== ЛОГИ ==========

class LogService:
    @staticmethod
    @sync_to_async
    def get_recent_logs(limit: int = 15) -> List[BotMessageLog]:
        return list(BotMessageLog.objects.select_related('bot_user').order_by('-created_at')[:limit])
    
    @staticmethod
    @sync_to_async
    def get_bot_statistics() -> Dict[str, Any]:
        total_users = BotUser.objects.count()
        active_users = BotUser.objects.filter(is_active=True).count()
        total_messages = BotMessageLog.objects.count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_messages': total_messages,
        }