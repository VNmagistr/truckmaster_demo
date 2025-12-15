# bot/states.py

"""
FSM стани для Telegram бота
Використовуємо ConversationHandler states
"""

# Загальні стани
IDLE = 'idle'
AWAITING_PHONE = 'awaiting_phone'

# Стани для адміністратора
ADMIN_SEARCH_TRUCK = 'admin_search_truck'
ADMIN_VIEW_LOGS = 'admin_view_logs'

# Стани для власника/водія
SELECTING_TRUCK = 'selecting_truck'
VIEWING_TRUCK_INFO = 'viewing_truck_info'
VIEWING_HISTORY = 'viewing_history'
AWAITING_ORDER_NUMBER = 'awaiting_order_number'

# Стани для налаштувань нагадувань
REMINDER_MENU = 'reminder_menu'
REMINDER_SELECT_TRUCK = 'reminder_select_truck'
REMINDER_SELECT_TYPE = 'reminder_select_type'
REMINDER_CONFIGURE = 'reminder_configure'

# Стани для менеджера
MANAGER_CREATE_ORDER = 'manager_create_order'
MANAGER_SEND_NOTIFICATION = 'manager_send_notification'


# Групи станів для ConversationHandler
class States:
    """Клас для зручної роботи зі станами"""
    
    # Основні стани
    IDLE = IDLE
    AWAITING_PHONE = AWAITING_PHONE
    
    # Адмін
    ADMIN_SEARCH_TRUCK = ADMIN_SEARCH_TRUCK
    ADMIN_VIEW_LOGS = ADMIN_VIEW_LOGS
    
    # Власник/Водій
    SELECTING_TRUCK = SELECTING_TRUCK
    VIEWING_TRUCK_INFO = VIEWING_TRUCK_INFO
    VIEWING_HISTORY = VIEWING_HISTORY
    AWAITING_ORDER_NUMBER = AWAITING_ORDER_NUMBER
    
    # Нагадування
    REMINDER_MENU = REMINDER_MENU
    REMINDER_SELECT_TRUCK = REMINDER_SELECT_TRUCK
    REMINDER_SELECT_TYPE = REMINDER_SELECT_TYPE
    REMINDER_CONFIGURE = REMINDER_CONFIGURE
    
    # Менеджер
    MANAGER_CREATE_ORDER = MANAGER_CREATE_ORDER
    MANAGER_SEND_NOTIFICATION = MANAGER_SEND_NOTIFICATION
    
    @classmethod
    def get_all_states(cls):
        """Повертає список всіх станів"""
        return [
            value for key, value in cls.__dict__.items()
            if not key.startswith('_') and isinstance(value, str)
        ]