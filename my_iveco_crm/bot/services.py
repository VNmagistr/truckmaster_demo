# bot/services.py

"""
Бізнес-логіка для Telegram бота
Всі операції з БД винесені сюди
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async

from django.db.models import Q, Count, Avg
from django.utils import timezone

from .models import (
    BotUser, MessageLog, ConversationState, 
    ReminderSettings, SentReminder, BotCommand
)
from clients.models import Client, Truck
from orders.models import ServiceOrder

logger = logging.getLogger(__name__)


# ========== КОРИСТУВАЧІ ==========

class UserService:
    """Сервіс для роботи з користувачами"""
    
    @staticmethod
    @sync_to_async
    def get_or_create_user(telegram_id: int, **user_data) -> tuple[BotUser, bool]:
        """Отримує або створює користувача"""
        return BotUser.objects.get_or_create(
            telegram_id=telegram_id,
            defaults=user_data
        )
    
    @staticmethod
    @sync_to_async
    def get_user_by_telegram_id(telegram_id: int) -> Optional[BotUser]:
        """Отримує користувача по Telegram ID"""
        try:
            return BotUser.objects.select_related('client').get(telegram_id=telegram_id)
        except BotUser.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def link_user_with_client(bot_user: BotUser, phone_number: str) -> tuple[bool, str]:
        """
        Прив'язує користувача бота до клієнта CRM по номеру телефону
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Шукаємо клієнта по номеру
            clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            client = Client.objects.get(phone__contains=clean_phone[-9:])  # Шукаємо по останніх 9 цифрах
            
            # Прив'язуємо
            bot_user.client = client
            bot_user.phone_number = phone_number
            bot_user.role = 'owner'  # За замовчуванням власник
            bot_user.save()
            
            return True, f"✅ Вас успішно ідентифіковано як {client.name}"
            
        except Client.DoesNotExist:
            # Зберігаємо номер, але не прив'язуємо
            bot_user.phone_number = phone_number
            bot_user.save()
            return False, "❌ Клієнта з таким номером не знайдено в базі. Зверніться до менеджера."
            
        except Client.MultipleObjectsReturned:
            return False, "⚠️ Знайдено декілька клієнтів з таким номером. Зверніться до менеджера."
            
        except Exception as e:
            logger.error(f"Error linking user with client: {e}")
            return False, "❌ Виникла помилка. Спробуйте пізніше."
    
    @staticmethod
    @sync_to_async
    def get_user_statistics(bot_user: BotUser) -> Dict[str, Any]:
        """Отримує статистику по користувачу"""
        total_messages = MessageLog.objects.filter(bot_user=bot_user).count()
        incoming = MessageLog.objects.filter(bot_user=bot_user, is_incoming=True).count()
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
    """Сервіс для роботи з автомобілями"""
    
    @staticmethod
    @sync_to_async
    def get_user_trucks(bot_user: BotUser) -> List[Truck]:
        """Отримує список автомобілів користувача"""
        if bot_user.role == 'driver':
            return list(bot_user.assigned_trucks.select_related('base_model', 'client').all())
        elif bot_user.role in ['owner', 'manager'] and bot_user.client:
            return list(Truck.objects.filter(client=bot_user.client).select_related('base_model'))
        elif bot_user.role == 'admin':
            return list(Truck.objects.all().select_related('base_model', 'client')[:50])  # Ліміт для адміна
        return []
    
    @staticmethod
    @sync_to_async
    def get_truck_by_id(truck_id: int) -> Optional[Truck]:
        """Отримує автомобіль по ID"""
        try:
            return Truck.objects.select_related('base_model', 'client').get(id=truck_id)
        except Truck.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def search_truck_by_plate(plate_query: str) -> List[Truck]:
        """
        Шукає автомобіль по номеру (повному або частковому)
        Підтримує пошук по останніх цифрах
        """
        # Видаляємо все крім букв і цифр
        clean_query = ''.join(c for c in plate_query.upper() if c.isalnum())
        
        if not clean_query:
            return []
        
        # Шукаємо по точному співпадінню або частковому
        trucks = Truck.objects.filter(
            Q(license_plate__icontains=clean_query) |
            Q(license_plate__icontains=plate_query)
        ).select_related('base_model', 'client')[:20]  # Обмежуємо 20 результатами
        
        return list(trucks)
    
    @staticmethod
    @sync_to_async
    def get_truck_info(truck: Truck) -> str:
        """Формує детальну інформацію про автомобіль"""
        info = f"🚚 *{truck.specific_model_name}*\n"
        info += f"📋 Номер: `{truck.license_plate}`\n"
        info += f"🔢 VIN: `...{truck.last_seven_vin}`\n"
        
        if truck.euro_standard:
            info += f"♻️ Євростандарт: {truck.get_euro_standard_display()}\n"
        
        if truck.client:
            info += f"👤 Власник: {truck.client.name}\n"
            if truck.client.phone:
                info += f"📞 Телефон: {truck.client.phone}\n"
        
        return info


# ========== ЗАМОВЛЕННЯ ==========

class OrderService:
    """Сервіс для роботи із замовленнями"""
    
    @staticmethod
    @sync_to_async
    def get_order_by_number(order_number: str) -> Optional[ServiceOrder]:
        """Отримує замовлення по номеру"""
        try:
            return ServiceOrder.objects.select_related('client', 'truck').get(
                order_number=order_number
            )
        except ServiceOrder.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def get_truck_orders(truck: Truck, limit: int = 10) -> List[ServiceOrder]:
        """Отримує останні замовлення для автомобіля"""
        return list(
            ServiceOrder.objects.filter(truck=truck)
            .select_related('client')
            .order_by('-created_at')[:limit]
        )
    
    @staticmethod
    @sync_to_async
    def get_order_info(order: ServiceOrder) -> str:
        """Формує інформацію про замовлення"""
        info = f"📝 *Замовлення #{order.order_number}*\n"
        info += f"📅 Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        info += f"📊 Статус: {order.get_status_display()}\n"
        
        if order.truck:
            info += f"🚚 Автомобіль: {order.truck.license_plate}\n"
        
        if order.problem_description:
            desc = order.problem_description[:100] + '...' if len(order.problem_description) > 100 else order.problem_description
            info += f"📝 Опис: {desc}\n"
        
        if order.total_cost:
            info += f"💰 Вартість: {order.total_cost} грн\n"
        
        return info
    
    @staticmethod
    @sync_to_async
    def get_active_orders(bot_user: BotUser) -> List[ServiceOrder]:
        """Отримує активні замовлення користувача"""
        if bot_user.role in ['owner', 'driver'] and bot_user.client:
            return list(
                ServiceOrder.objects.filter(
                    client=bot_user.client,
                    status__in=['OPEN', 'IN_PROGRESS']
                ).select_related('truck').order_by('-created_at')
            )
        return []


# ========== НАГАДУВАННЯ ==========

class ReminderService:
    """Сервіс для роботи з нагадуваннями"""
    
    @staticmethod
    @sync_to_async
    def get_user_reminders(bot_user: BotUser) -> List[ReminderSettings]:
        """Отримує всі нагадування користувача"""
        return list(
            ReminderSettings.objects.filter(bot_user=bot_user)
            .select_related('truck')
            .order_by('truck', 'reminder_type')
        )
    
    @staticmethod
    @sync_to_async
    def get_truck_reminders(bot_user: BotUser, truck: Truck) -> List[ReminderSettings]:
        """Отримує нагадування для конкретного автомобіля"""
        return list(
            ReminderSettings.objects.filter(
                bot_user=bot_user,
                truck=truck
            ).order_by('reminder_type')
        )
    
    @staticmethod
    @sync_to_async
    def create_or_update_reminder(
        bot_user: BotUser, 
        truck: Truck, 
        reminder_type: str,
        **settings
    ) -> ReminderSettings:
        """Створює або оновлює нагадування"""
        reminder, created = ReminderSettings.objects.update_or_create(
            bot_user=bot_user,
            truck=truck,
            reminder_type=reminder_type,
            defaults=settings
        )
        return reminder
    
    @staticmethod
    @sync_to_async
    def toggle_reminder(reminder_id: int) -> tuple[bool, str]:
        """Вмикає/вимикає нагадування"""
        try:
            reminder = ReminderSettings.objects.get(id=reminder_id)
            reminder.is_enabled = not reminder.is_enabled
            reminder.save()
            
            status = "увімкнено" if reminder.is_enabled else "вимкнено"
            return True, f"✅ Нагадування {status}"
        except ReminderSettings.DoesNotExist:
            return False, "❌ Нагадування не знайдено"


# ========== ЛОГИ ТА СТАТИСТИКА ==========

class LogService:
    """Сервіс для роботи з логами"""
    
    @staticmethod
    @sync_to_async
    def get_recent_logs(limit: int = 15) -> List[MessageLog]:
        """Отримує останні логи повідомлень"""
        return list(
            MessageLog.objects.select_related('bot_user')
            .order_by('-created_at')[:limit]
        )
    
    @staticmethod
    @sync_to_async
    def get_user_logs(bot_user: BotUser, limit: int = 50) -> List[MessageLog]:
        """Отримує логи конкретного користувача"""
        return list(
            MessageLog.objects.filter(bot_user=bot_user)
            .order_by('-created_at')[:limit]
        )
    
    @staticmethod
    @sync_to_async
    def get_bot_statistics() -> Dict[str, Any]:
        """Отримує загальну статистику бота"""
        total_users = BotUser.objects.count()
        active_users = BotUser.objects.filter(is_active=True).count()
        
        users_by_role = dict(
            BotUser.objects.values('role')
            .annotate(count=Count('id'))
            .values_list('role', 'count')
        )
        
        total_messages = MessageLog.objects.count()
        today_messages = MessageLog.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        avg_response_time = MessageLog.objects.filter(
            is_processed=True,
            processing_time_ms__isnull=False
        ).aggregate(avg=Avg('processing_time_ms'))['avg'] or 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'users_by_role': users_by_role,
            'total_messages': total_messages,
            'today_messages': today_messages,
            'avg_response_time_ms': round(avg_response_time, 2),
        }
    
    @staticmethod
    @sync_to_async
    def format_logs_for_admin(logs: List[MessageLog]) -> str:
        """Форматує логи для відображення адміну"""
        if not logs:
            return "📋 Логів не знайдено"
        
        output = "📋 *Останні повідомлення:*\n\n"
        
        for log in logs:
            time_str = log.created_at.strftime('%d.%m %H:%M')
            direction = "➡️" if log.is_incoming else "⬅️"
            
            user_info = log.bot_user.get_full_name()
            if log.bot_user.username:
                user_info += f" (@{log.bot_user.username})"
            if log.bot_user.phone_number:
                user_info += f" {log.bot_user.phone_number}"
            
            message_preview = log.message_text[:50] + "..." if len(log.message_text) > 50 else log.message_text
            
            output += f"{time_str} {direction} *{user_info}*\n"
            output += f"   {message_preview}\n\n"
        
        return output


# ========== КОМАНДИ ==========

class CommandService:
    """Сервіс для роботи з командами"""
    
    @staticmethod
    @sync_to_async
    def register_command_usage(command: str):
        """Реєструє використання команди"""
        try:
            cmd, created = BotCommand.objects.get_or_create(
                command=command.lstrip('/'),
                defaults={'description': 'Auto-registered command'}
            )
            cmd.increment_usage()
        except Exception as e:
            logger.error(f"Error registering command usage: {e}")
    
    @staticmethod
    @sync_to_async
    def get_command_statistics() -> List[Dict[str, Any]]:
        """Отримує статистику використання команд"""
        commands = BotCommand.objects.filter(is_active=True).order_by('-usage_count')[:10]
        
        return [
            {
                'command': f"/{cmd.command}",
                'usage_count': cmd.usage_count,
                'last_used': cmd.last_used
            }
            for cmd in commands
        ]