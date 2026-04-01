# TruckMaster CRM — Backend

CRM-система для сервісного центру вантажних автомобілів Iveco.
Це демонстраційна версія. Frontend: [truckmaster_frontend_demo](https://github.com/VNmagistr/truckmaster_frontend_demo)

## Можливості

- Управління клієнтами та вантажівками
- Наряди-замовлення з відстеженням статусів
- Облік запчастин та складський облік
- Регламентні інтервали ТО (відлік по пробігу)
- Рахунки та інтеграція з Nova Poshta
- Особистий кабінет клієнта (окремий JWT)
- Записи на сервіс
- Telegram-бот для клієнтів
- Система модулів — вмикати/вимикати функції через адмінку
- REST API з Swagger документацією (`/api/docs/`)

## Швидкий старт

### 1. Клонування та залежності

```bash
git clone https://github.com/VNmagistr/truckmaster_demo.git
cd truckmaster_demo/my_iveco_crm
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Налаштування середовища

```bash
# Скопіюйте файл прикладу конфігурації
cp ../.env.example .env
# Відкрийте .env і встановіть SECRET_KEY (будь-який рядок 50+ символів)
```

При `DEBUG=True` автоматично використовується SQLite — PostgreSQL не потрібен.

### 3. Міграції та демо-дані

```bash
python manage.py migrate
python manage.py create_demo_data
```

### 4. Запуск

```bash
python manage.py runserver
```

Відкрийте: http://127.0.0.1:8000/admin/
Логін: `admin` / Пароль: `demo1234`

## Демо-дані

Команда `create_demo_data` створює:

| Що | Кількість |
|----|-----------|
| Адмін-користувач | 1 (`admin` / `demo1234`) |
| Клієнти | 5 |
| Вантажівки Iveco | 6 |
| Наряди-замовлення | 6 (різні статуси) |
| Групи робіт | 5 |
| Послуги | 16 |
| Інтервали ТО | налаштовані для 1 авто |

## API документація

Після запуску:
- Swagger UI: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- OpenAPI схема: http://127.0.0.1:8000/api/schema/

## Технології

- Python 3.13 / Django 5.2
- Django REST Framework + SimpleJWT
- SQLite (dev) / PostgreSQL (prod)
- Celery + Redis (для фонових задач, необов'язково)
- ReportLab (генерація PDF)
- drf-spectacular (OpenAPI документація)

## Структура модулів

Модулі вмикаються/вимикаються через `/admin/core/module/`:

| Модуль | За замовчуванням |
|--------|-----------------|
| Наряди, Клієнти, Акаунти | Завжди увімкнено |
| Склад (inventory) | Увімкнено |
| Регламенти ТО | Увімкнено |
| Кабінет клієнта | Увімкнено |
| Рахунки | Увімкнено |
| Записи на сервіс | Увімкнено |
| Telegram-бот | Вимкнено |
| ALPR (розпізнавання) | Вимкнено |
