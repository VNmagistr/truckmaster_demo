import os
from celery import Celery
from celery.schedules import crontab

# Встановлюємо Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_iveco_crm.settings')

app = Celery('my_iveco_crm')

# Завантажуємо конфіг з Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматично знаходимо tasks в додатках
app.autodiscover_tasks()

# Періодичні задачі
app.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'bot.tasks.send_daily_reminders',
        'schedule': crontab(hour=9, minute=0),  # Щодня о 9:00
    },
    'ask-owners-for-mileage': {
        'task': 'bot.tasks.ask_owners_for_mileage',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Щопонеділка о 10:00
    },
    'send-appointment-reminders': {
        'task': 'appointments.tasks.send_appointment_reminders',
        'schedule': crontab(minute=0),  # every hour
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')